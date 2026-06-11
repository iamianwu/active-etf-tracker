from collections import defaultdict
from typing import Any

from ..config import ETF_NAMES
from ..database import get_conn, init_db, normal_stock_condition, rows_to_dicts


def is_normal_stock_code(code: str) -> bool:
    c = str(code or "").strip()
    return c.isdigit() and len(c) == 4


def latest_date_for_etf(conn, etf_code: str) -> str | None:
    row = conn.execute("SELECT MAX(data_date) AS d FROM holdings WHERE etf_code=?", (etf_code,)).fetchone()
    return row["d"] if row else None


def previous_date_for_etf(conn, etf_code: str, date: str) -> str | None:
    row = conn.execute("SELECT MAX(data_date) AS d FROM holdings WHERE etf_code=? AND data_date < ?", (etf_code, date)).fetchone()
    return row["d"] if row else None


def compute_etf_changes(conn, etf_code: str, date: str, prev_date: str | None = None) -> list[dict[str, Any]]:
    if not prev_date:
        prev_date = previous_date_for_etf(conn, etf_code, date)
    if not prev_date:
        return []

    curr = rows_to_dicts(conn.execute("SELECT * FROM holdings WHERE etf_code=? AND data_date=?", (etf_code, date)).fetchall())
    prev = rows_to_dicts(conn.execute("SELECT * FROM holdings WHERE etf_code=? AND data_date=?", (etf_code, prev_date)).fetchall())

    curr_map = {r["stock_code"]: r for r in curr}
    prev_map = {r["stock_code"]: r for r in prev}
    out = []

    for code, r in curr_map.items():
        if not is_normal_stock_code(code):
            continue

        p = prev_map.get(code)

        if not p:
            status = "新增"
            delta_shares = r["shares"] or 0
            delta_weight = r["weight"] or 0
        else:
            delta_shares = (r["shares"] or 0) - (p["shares"] or 0)
            delta_weight = (r["weight"] or 0) - (p["weight"] or 0)

            # V2：只看真正股數變動，不把「只有權重變動」當成交易。
            if delta_shares > 0:
                status = "加碼"
            elif delta_shares < 0:
                status = "減碼"
            else:
                continue

        out.append({**r, "status": status, "delta_shares": delta_shares, "delta_weight": delta_weight})

    for code, p in prev_map.items():
        if (not is_normal_stock_code(code)) or code in curr_map:
            continue
        out.append({
            **p,
            "data_date": date,
            "status": "刪除",
            "shares": 0,
            "weight": 0,
            "delta_shares": -(p["shares"] or 0),
            "delta_weight": -(p["weight"] or 0),
        })

    return sorted(out, key=lambda x: {"新增": 0, "刪除": 1, "加碼": 2, "減碼": 3}.get(x["status"], 9))


def summarize_changes(changes: list[dict[str, Any]]) -> dict[str, int]:
    keys = ["新增", "刪除", "加碼", "減碼"]
    return {k: sum(1 for x in changes if x["status"] == k) for k in keys}


def get_etf_list() -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT h.etf_code, MAX(h.data_date) AS data_date, COUNT(*) AS holding_count,
                   SUM(CASE WHEN {normal_stock_condition('h')} THEN h.weight ELSE 0 END) AS stock_weight,
                   q.etf_name, q.price, q.change_pct, q.volume, q.amount, q.aum_billion
            FROM holdings h
            LEFT JOIN etf_quotes q ON q.etf_code = h.etf_code
            WHERE h.data_date = (SELECT MAX(h2.data_date) FROM holdings h2 WHERE h2.etf_code=h.etf_code)
            GROUP BY h.etf_code, q.etf_name, q.price, q.change_pct, q.volume, q.amount, q.aum_billion
            ORDER BY h.etf_code
            """
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["etf_name"] = d.get("etf_name") or ETF_NAMES.get(d["etf_code"], d["etf_code"])
            out.append(d)
        return out


def get_etf_detail(etf_code: str) -> dict[str, Any]:
    init_db()
    with get_conn() as conn:
        d = latest_date_for_etf(conn, etf_code)
        if not d:
            return {"etf_code": etf_code, "error": "no data"}

        prev = previous_date_for_etf(conn, etf_code, d)
        holdings = rows_to_dicts(conn.execute(
            """
            SELECT h.*, sq.price, sq.change_pct,
                   CASE WHEN sq.price IS NOT NULL THEN h.shares * sq.price / 100000000.0 ELSE NULL END AS market_value_billion
            FROM holdings h
            LEFT JOIN stock_quotes sq ON sq.stock_code=h.stock_code
            WHERE h.etf_code=? AND h.data_date=?
            ORDER BY h.weight DESC
            """, (etf_code, d)
        ).fetchall())

        quote = conn.execute("SELECT * FROM etf_quotes WHERE etf_code=?", (etf_code,)).fetchone()
        changes = compute_etf_changes(conn, etf_code, d, prev) if prev else []

        return {
            "etf_code": etf_code,
            "etf_name": ETF_NAMES.get(etf_code, etf_code) if not quote else (quote["etf_name"] or ETF_NAMES.get(etf_code, etf_code)),
            "data_date": d,
            "previous_date": prev,
            "quote": dict(quote) if quote else {},
            "holdings": holdings,
            "change_summary": summarize_changes(changes),
            "changes": changes,
        }


def get_constituent_summary() -> list[dict[str, Any]]:
    init_db()
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(
            f"""
            SELECT h.stock_code, h.stock_name, h.etf_code, h.weight, h.shares,
                   sq.price, sq.change_pct
            FROM holdings h
            LEFT JOIN stock_quotes sq ON sq.stock_code=h.stock_code
            WHERE {normal_stock_condition('h')}
              AND h.data_date = (SELECT MAX(h2.data_date) FROM holdings h2 WHERE h2.etf_code=h.etf_code)
            """
        ).fetchall())

    grouped: dict[str, dict[str, Any]] = {}

    for r in rows:
        code = r["stock_code"]
        if code not in grouped:
            grouped[code] = {
                "stock_code": code,
                "stock_name": r["stock_name"],
                "etf_count": 0,
                "total_weight": 0.0,
                "total_shares": 0.0,
                "price": r.get("price"),
                "change_pct": r.get("change_pct"),
                "etfs": [],
            }

        g = grouped[code]
        g["etf_count"] += 1
        g["total_weight"] += float(r.get("weight") or 0)
        g["total_shares"] += float(r.get("shares") or 0)
        g["etfs"].append(f"{r['etf_code']}:{float(r.get('weight') or 0):.2f}")

    out = []
    for g in grouped.values():
        price = g.get("price")
        g["market_value_billion"] = (g["total_shares"] * float(price) / 100000000.0) if price else None
        g["etfs"] = ", ".join(g["etfs"])
        out.append(g)

    return sorted(out, key=lambda x: (x.get("market_value_billion") or 0, x.get("etf_count") or 0, x.get("total_weight") or 0), reverse=True)


def get_stock_detail(stock_code: str) -> dict[str, Any]:
    init_db()
    with get_conn() as conn:
        quote = conn.execute("SELECT * FROM stock_quotes WHERE stock_code=?", (stock_code,)).fetchone()

        rows = rows_to_dicts(conn.execute(
            """
            SELECT h.*, q.etf_name,
                   CASE WHEN sq.price IS NOT NULL THEN h.shares * sq.price / 100000000.0 ELSE NULL END AS market_value_billion
            FROM holdings h
            LEFT JOIN etf_quotes q ON q.etf_code=h.etf_code
            LEFT JOIN stock_quotes sq ON sq.stock_code=h.stock_code
            WHERE h.stock_code=?
              AND h.data_date = (SELECT MAX(h2.data_date) FROM holdings h2 WHERE h2.etf_code=h.etf_code)
            ORDER BY h.weight DESC
            """, (stock_code,)
        ).fetchall())

        hist = rows_to_dicts(conn.execute(
            """
            SELECT * FROM holdings WHERE stock_code=? ORDER BY data_date DESC, etf_code LIMIT 300
            """, (stock_code,)
        ).fetchall())

        try:
            price_history = rows_to_dicts(conn.execute(
                """
                SELECT trade_date, open, high, low, close, volume, change_pct, market
                FROM stock_price_history
                WHERE stock_code=?
                ORDER BY trade_date ASC
                LIMIT 160
                """, (stock_code,)
            ).fetchall())
        except Exception:
            price_history = []

        try:
            institutional = rows_to_dicts(conn.execute(
                """
                SELECT trade_date, foreign_net, investment_trust_net, dealer_net, total_net, source
                FROM institutional_flows
                WHERE stock_code=?
                ORDER BY trade_date DESC, source
                LIMIT 80
                """, (stock_code,)
            ).fetchall())
        except Exception:
            institutional = []

        name = rows[0]["stock_name"] if rows else (quote["stock_name"] if quote else stock_code)

        return {
            "stock_code": stock_code,
            "stock_name": name,
            "quote": dict(quote) if quote else {},
            "summary": {
                "etf_count": len({r["etf_code"] for r in rows}),
                "total_shares": sum((r["shares"] or 0) for r in rows),
                "total_weight": sum((r["weight"] or 0) for r in rows),
                "market_value_billion": sum((r["market_value_billion"] or 0) for r in rows),
            },
            "etfs": rows,
            "history": hist,
            "price_history": price_history,
            "institutional": institutional,
        }


def get_signals(signal_type: str | None = None) -> dict[str, Any]:
    init_db()
    with get_conn() as conn:
        changes = []
        etfs = [r["etf_code"] for r in conn.execute("SELECT DISTINCT etf_code FROM holdings").fetchall()]

        for etf in etfs:
            d = latest_date_for_etf(conn, etf)
            prev = previous_date_for_etf(conn, etf, d) if d else None
            if d and prev:
                changes.extend(compute_etf_changes(conn, etf, d, prev))

        changes = [c for c in changes if c["status"] in {"新增", "刪除", "加碼", "減碼"}]

        type_map = {"added": "新增", "removed": "刪除", "increased": "加碼", "decreased": "減碼"}
        if signal_type in type_map:
            changes = [c for c in changes if c["status"] == type_map[signal_type]]

        quote_rows = conn.execute("SELECT stock_code, price FROM stock_quotes").fetchall()
        price_map = {r["stock_code"]: (r["price"] or 0) for r in quote_rows}

        by_stock = defaultdict(lambda: {
            "stock_code": "",
            "stock_name": "",
            "price": None,
            "delta_shares": 0,
            "delta_weight": 0,
            "delta_value_billion": 0,
            "has_price": False,
            "count": 0,
            "increase_etf_count": 0,
            "decrease_etf_count": 0,
            "add_etf_count": 0,
            "remove_etf_count": 0,
            "statuses": [],
        })

        for c in changes:
            b = by_stock[c["stock_code"]]
            price = price_map.get(c["stock_code"]) or 0
            delta_shares = c.get("delta_shares") or 0
            delta_value = delta_shares * price / 100000000.0 if price else None

            b["stock_code"] = c["stock_code"]
            b["stock_name"] = c["stock_name"]
            b["price"] = price or None
            b["delta_shares"] += delta_shares
            b["delta_weight"] += c.get("delta_weight") or 0
            b["count"] += 1
            b["statuses"].append(f"{c['etf_code']} {c['status']}")

            if delta_value is not None:
                b["delta_value_billion"] += delta_value
                b["has_price"] = True

            if c["status"] == "加碼":
                b["increase_etf_count"] += 1
            elif c["status"] == "減碼":
                b["decrease_etf_count"] += 1
            elif c["status"] == "新增":
                b["add_etf_count"] += 1
            elif c["status"] == "刪除":
                b["remove_etf_count"] += 1

        aggregate = []
        for x in by_stock.values():
            if not x["has_price"]:
                x["delta_value_billion"] = None
            aggregate.append(x)

        def money_or_shares_score(x):
            if x.get("delta_value_billion") is not None:
                return abs(x.get("delta_value_billion") or 0)
            return abs(x.get("delta_shares") or 0)

        aggregate = sorted(aggregate, key=money_or_shares_score, reverse=True)

        return {
            "summary": summarize_changes(changes),
            "changes": changes,
            "aggregate": aggregate,
        }

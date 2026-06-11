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


def _mmdd(date_str: str | None) -> str:
    if not date_str:
        return ""
    s = str(date_str)
    if "-" in s:
        parts = s.split("-")
        return f"{parts[1]}/{parts[2]}"
    if "/" in s:
        parts = s.split("/")
        return f"{parts[1].zfill(2)}/{parts[2].zfill(2)}"
    return s


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


def get_signals(signal_type: str | None = None) -> dict[str, Any]:
    init_db()
    with get_conn() as conn:
        changes = []
        etfs = [r["etf_code"] for r in conn.execute("SELECT DISTINCT etf_code FROM holdings").fetchall()]
        latest_map = {}
        for etf in etfs:
            d = latest_date_for_etf(conn, etf)
            if d:
                latest_map[etf] = d

        data_date = max(latest_map.values()) if latest_map else None
        fetched_etf_count = sum(1 for d in latest_map.values() if d == data_date) if data_date else 0
        stale_etfs = [{"etf_code": k, "data_date": v} for k, v in latest_map.items() if v != data_date]

        for etf, d in latest_map.items():
            prev = previous_date_for_etf(conn, etf, d) if d else None
            if d and prev:
                changes.extend(compute_etf_changes(conn, etf, d, prev))

        changes = [c for c in changes if c["status"] in {"新增", "刪除", "加碼", "減碼"}]

        quote_rows = conn.execute("SELECT stock_code, price, change_pct FROM stock_quotes").fetchall()
        quote_map = {
            r["stock_code"]: {"price": r["price"], "change_pct": r["change_pct"]}
            for r in quote_rows
        }

        enriched = []
        for c in changes:
            q = quote_map.get(c["stock_code"], {})
            price = q.get("price") or 0
            delta_shares = c.get("delta_shares") or 0
            enriched.append({
                **c,
                "price": q.get("price"),
                "change_pct": q.get("change_pct"),
                "delta_value_billion": delta_shares * price / 100000000.0 if price else None,
            })
        changes = enriched

        type_map = {"added": "新增", "removed": "刪除", "increased": "加碼", "decreased": "減碼"}
        if signal_type in type_map:
            changes = [c for c in changes if c["status"] == type_map[signal_type]]

        by_stock = defaultdict(lambda: {
            "stock_code": "",
            "stock_name": "",
            "price": None,
            "change_pct": None,
            "current_shares": 0,
            "previous_shares": 0,
            "delta_shares": 0,
            "delta_weight": 0,
            "delta_value_billion": 0,
            "has_price": False,
            "count": 0,
            "etf_count": 0,
            "etf_codes": [],
            "buy_etf_count": 0,
            "sell_etf_count": 0,
            "increase_etf_count": 0,
            "decrease_etf_count": 0,
            "add_etf_count": 0,
            "remove_etf_count": 0,
            "statuses": [],
        })

        for c in changes:
            b = by_stock[c["stock_code"]]
            price = c.get("price") or 0
            delta_shares = c.get("delta_shares") or 0
            current_shares = c.get("shares") or 0
            previous_shares = current_shares - delta_shares
            delta_value = delta_shares * price / 100000000.0 if price else None

            b["stock_code"] = c["stock_code"]
            b["stock_name"] = c["stock_name"]
            b["price"] = price or None
            b["change_pct"] = c.get("change_pct")
            b["current_shares"] += current_shares
            b["previous_shares"] += previous_shares
            b["delta_shares"] += delta_shares
            b["delta_weight"] += c.get("delta_weight") or 0
            b["count"] += 1
            b["etf_codes"].append(c["etf_code"])
            b["statuses"].append(f"{c['etf_code']} {c['status']}")

            if delta_value is not None:
                b["delta_value_billion"] += delta_value
                b["has_price"] = True

            if c["status"] == "加碼":
                b["increase_etf_count"] += 1
                b["buy_etf_count"] += 1
            elif c["status"] == "新增":
                b["add_etf_count"] += 1
                b["buy_etf_count"] += 1
            elif c["status"] == "減碼":
                b["decrease_etf_count"] += 1
                b["sell_etf_count"] += 1
            elif c["status"] == "刪除":
                b["remove_etf_count"] += 1
                b["sell_etf_count"] += 1

        aggregate = []
        for x in by_stock.values():
            unique_etfs = list(dict.fromkeys(x.get("etf_codes") or []))
            x["etf_codes"] = unique_etfs
            x["etf_count"] = len(unique_etfs)
            if not x["has_price"]:
                x["delta_value_billion"] = None
            if x["previous_shares"]:
                x["magnitude_pct"] = x["delta_shares"] / x["previous_shares"] * 100.0
            else:
                x["magnitude_pct"] = None

            if x["delta_shares"] > 0:
                x["status"] = "新增" if x["add_etf_count"] > 0 and x["increase_etf_count"] == 0 else "加碼"
            elif x["delta_shares"] < 0:
                x["status"] = "刪除" if x["remove_etf_count"] > 0 and x["decrease_etf_count"] == 0 else "減碼"
            else:
                x["status"] = "混合"

            aggregate.append(x)

        def money_or_shares_score(x):
            if x.get("delta_value_billion") is not None:
                return abs(x.get("delta_value_billion") or 0)
            return abs(x.get("delta_shares") or 0)

        aggregate = sorted(aggregate, key=money_or_shares_score, reverse=True)

        return {
            "data_date": data_date,
            "data_date_mmdd": _mmdd(data_date),
            "fetched_etf_count": fetched_etf_count,
            "total_etf_count": len(etfs),
            "stale_etfs": stale_etfs,
            "summary": summarize_changes(changes),
            "changes": changes,
            "aggregate": aggregate,
        }

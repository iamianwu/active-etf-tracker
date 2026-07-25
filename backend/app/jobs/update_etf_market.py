import os
from pprint import pprint

from ..services.moneydj_etf_metadata import update_moneydj_etf_metadata
from ..services.pocket_etf_market import (
    ALL_ETF_CODES,
    update_pocket_etf_market,
)

def main():
    mode = os.getenv("ETF_MARKET_UPDATE_MODE", "all").strip().lower()
    if mode not in {"all", "pocket", "moneydj"}:
        raise ValueError(f"Unsupported ETF_MARKET_UPDATE_MODE: {mode}")

    pocket_result = None
    moneydj_result = None

    if mode in {"all", "pocket"}:
        batch_size = max(0, int(os.getenv("ETF_MARKET_BATCH_SIZE", "0")))
        batch_index = max(0, int(os.getenv("ETF_MARKET_BATCH_INDEX", "0")))
        codes = list(ALL_ETF_CODES)

        if batch_size:
            start = batch_index * batch_size
            codes = codes[start:start + batch_size]
            print(
                f"Pocket ETF batch={batch_index} "
                f"range={start}:{start + batch_size} "
                f"selected={len(codes)}",
                flush=True,
            )

        if not codes:
            print("Pocket ETF batch is empty; skip.", flush=True)
            pocket_result = {
                "requested": 0,
                "saved": 0,
                "errors": [],
            }
        else:
            pocket_result = update_pocket_etf_market(codes=codes)

    if mode in {"all", "moneydj"}:
        moneydj_result = update_moneydj_etf_metadata()

    result = {
        "mode": mode,
        "pocket": pocket_result,
        "moneydj": moneydj_result,
    }
    pprint(result)

    if mode in {"all", "pocket"} and pocket_result and not pocket_result.get("saved"):
        if pocket_result.get("requested"):
            raise RuntimeError("Pocket ETF market update saved zero rows")

    if mode in {"all", "moneydj"} and moneydj_result and not moneydj_result.get("saved"):
        raise RuntimeError("MoneyDJ ETF metadata update saved zero rows")

if __name__ == "__main__":
    main()

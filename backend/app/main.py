from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from .config import ADMIN_PASSWORD, CORS_ORIGINS
from .database import init_db, is_postgres
from .services.fetcher import update_one_etf, update_all_etfs, seed_demo_data
from .services.query_service import get_etf_list, get_etf_detail, get_constituent_summary, get_stock_detail, get_signals

app = FastAPI(title="Pocket ETF Tracker API", version="0.2.0-cloud")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin(x_admin_password: str | None = Header(default=None)):
    # Local development may leave ADMIN_PASSWORD empty.
    # On Render/Railway/Cloud Run, set ADMIN_PASSWORD to protect update endpoints.
    if ADMIN_PASSWORD and x_admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="invalid admin password")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"ok": True, "name": "Pocket ETF Tracker API", "db": "postgres" if is_postgres() else "sqlite"}


@app.post("/admin/seed-demo")
def seed_demo(x_admin_password: str | None = Header(default=None)):
    require_admin(x_admin_password)
    seed_demo_data()
    return {"ok": True}


@app.post("/admin/update/{etf_code}")
def update_etf(etf_code: str, dt_range: int = 1, x_admin_password: str | None = Header(default=None)):
    require_admin(x_admin_password)
    try:
        return update_one_etf(etf_code.upper(), dt_range=dt_range)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/update-all")
def update_all(dt_range: int = 1, x_admin_password: str | None = Header(default=None)):
    require_admin(x_admin_password)
    return update_all_etfs(dt_range=dt_range)


@app.get("/etfs")
def etfs():
    return get_etf_list()


@app.get("/etfs/{etf_code}")
def etf_detail(etf_code: str):
    d = get_etf_detail(etf_code.upper())
    if d.get("error"):
        raise HTTPException(status_code=404, detail=d["error"])
    return d


@app.get("/holdings")
def holdings():
    return get_constituent_summary()


@app.get("/stocks/{stock_code}")
def stock_detail(stock_code: str):
    return get_stock_detail(stock_code)


@app.get("/signals")
def signals(type: str | None = None):
    return get_signals(type)

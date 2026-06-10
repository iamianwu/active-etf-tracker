import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "etf_tracker.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if x.strip()]
API_URL = "https://www.pocket.tw/api/cm/MobileService/ashx/GetDtnoData.ashx"

ETF_CODES = [
    "00980A", "00982A", "00981A", "00983A", "00984A", "00985A", "00986A",
    "00989A", "00988A", "00991A", "00990A", "00987A", "00992A", "00994A",
    "00995A", "00993A", "00996A", "00400A", "00401A", "00997A", "00999A",
    "00403A",
]

ETF_NAMES = {
    "00980A": "主動野村臺灣優選",
    "00981A": "主動統一台股增長",
    "00982A": "主動群益台灣強棒",
    "00983A": "主動中信ARK創新",
    "00984A": "主動安聯台灣高息",
    "00985A": "主動野村台灣50",
    "00986A": "主動元大臺灣價值",
    "00987A": "主動凱基台灣精選",
    "00988A": "主動統一全球創新",
    "00989A": "主動復華未來50",
    "00990A": "主動永豐臺灣ESG",
    "00991A": "主動富邦未來車",
    "00992A": "主動國泰台灣領袖",
    "00993A": "主動台新台灣成長",
    "00994A": "主動第一金台股優",
    "00995A": "主動兆豐台灣科技",
    "00996A": "主動群益科技高息",
    "00997A": "主動中信台灣成長",
    "00999A": "主動台新全球AI",
    "00400A": "主動野村全球優選",
    "00401A": "主動統一美國增長",
    "00403A": "主動統一升級50",
}

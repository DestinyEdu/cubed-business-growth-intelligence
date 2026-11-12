"""Project configuration for the Cubed Business Growth Intelligence Lab (PoC).
All data in this project is synthetic. No real client information is used."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "cubed_lab.db"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

RANDOM_SEED = 42          # makes the synthetic data reproducible
NUM_CLIENTS = 500         # approximate number of fictional SME clients
DATA_IS_SYNTHETIC = True  # must remain True for the PoC

"""Run one local cycle. With no publishing credentials, output stays in data/tapes/."""
import logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
from nbn import main, store  # noqa: E402

con = store.connect()
result = main.cycle(con)
print("cycle result:", result)
print("db:", store.status_summary(con))

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Tests use their own database file so they never wipe the demo's decision log.
os.environ.setdefault("FRAUDLENS_DB_URL", f"sqlite:///{(Path(__file__).parent / 'test.db').as_posix()}")

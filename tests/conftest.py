"""Shared test setup: isolate the DB to a temp sqlite before the app imports."""
import os
import tempfile

# Point the app at a throwaway DB *before* undertale_vera_app is imported anywhere
# (the engine is built at import time). pytest loads conftest first.
_tmp = tempfile.NamedTemporaryFile(prefix="utv_test_", suffix=".db", delete=False)
_tmp.close()
os.environ["UNDERTALE_VERA_DB"] = f"sqlite:///{_tmp.name}"

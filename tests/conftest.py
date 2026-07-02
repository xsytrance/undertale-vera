"""Shared test setup: isolate the DB to a temp sqlite before the app imports."""
import os
import tempfile

# Point the app at a throwaway DB *before* undertale_vera_app is imported anywhere
# (the engine is built at import time). pytest loads conftest first.
_tmp = tempfile.NamedTemporaryFile(prefix="utv_test_", suffix=".db", delete=False)
_tmp.close()
os.environ["UNDERTALE_VERA_DB"] = f"sqlite:///{_tmp.name}"

# Isolate supplied-portrait writes to a throwaway dir (the resolver reads this env
# at import) so tests never touch the real static/assets/portraits folder.
os.environ["UNDERTALE_VERA_PORTRAIT_DIR"] = tempfile.mkdtemp(prefix="utv_portraits_")
os.environ["UNDERTALE_VERA_EMBLEM_DIR"] = tempfile.mkdtemp(prefix="utv_emblems_")

# Isolate the power ladder: the suite must never read the developer's real
# ember_power.json (a live Spark/BYOK choice would flip every chat test's
# backend). power_config reads this env at import.
os.environ["UNDERTALE_VERA_POWER_CONFIG"] = os.path.join(
    tempfile.mkdtemp(prefix="utv_power_"), "ember_power.json")

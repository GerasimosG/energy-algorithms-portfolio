import os
import shutil

# Tests must never depend on a developer's local repo-root .env (CI has none).
# Skip the config .env auto-loader for the whole session so the ENTSO-E token
# never leaks into the test environment and the token-guard tests are
# deterministic on any machine (including a Pi where a real .env exists).
os.environ.setdefault("ENERGY_ALGORITHMS_SKIP_DOTENV", "1")

_cbc_path = shutil.which("cbc")
if _cbc_path and not os.access("cbc", os.X_OK):
    try:
        os.symlink(_cbc_path, "cbc")
    except OSError:
        pass

import os
import shutil

_cbc_path = shutil.which("cbc")
if _cbc_path and not os.access("cbc", os.X_OK):
 try:
 os.symlink(_cbc_path, "cbc")
 except OSError:
 pass

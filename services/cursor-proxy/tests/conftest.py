from __future__ import annotations

import sys
from pathlib import Path

root = str(Path(__file__).resolve().parents[1])
if root in sys.path:
    sys.path.remove(root)
sys.path.insert(0, root)
for name in list(sys.modules):
    if name == "app" or name.startswith("app."):
        del sys.modules[name]

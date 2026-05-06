import sys
sys.path.insert(0, '.')
from main import app
routes = [r.path for r in app.routes]
print(f"Backend OK: {len(routes)} routes")
for r in sorted(routes):
    print(f"  {r}")

# Dev API server — watches ONLY src/ so the Next.js .next/ build churn
# can't trigger an endless uvicorn reload loop (which previously made new
# routes 404 because the server never finished reloading).
#
# Usage:  ./run_api.ps1
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src

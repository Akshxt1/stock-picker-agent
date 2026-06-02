# run_test.py
import json
from src.agents.crew import run_stock_picker

result = run_stock_picker(
    market="INDIA",
    sector="Technology",
    size="Large",
)

print("\n" + "="*60)
print("MASTER ANALYST OUTPUT")
print("="*60)
print(json.dumps(result, indent=2))
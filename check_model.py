import joblib
import os

for model_path in ['models/triage_assets_mingled.pkl', 'triage_assets_mingled.pkl']:
    print(f"\nTesting: {model_path}")
    if os.path.exists(model_path):
        try:
            assets = joblib.load(model_path)
            print(f"  Status: OK")
            print(f"  Keys: {list(assets.keys())}")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print(f"  Status: File not found")

"""
Test Hugging Face Model Loading
This script tests if models can be downloaded and loaded from HF Hub
"""

import os
os.environ['USE_HUGGINGFACE'] = 'true'

print("=" * 70)
print("🧪 TESTING HUGGING FACE MODEL INTEGRATION")
print("=" * 70)
print("\n🔧 Configuration:")
print(f"   USE_HUGGINGFACE: {os.getenv('USE_HUGGINGFACE')}")
print(f"   Repository: Manoj-palanisamy/smarttriage-models")
print("\n" + "=" * 70)

try:
    print("\n1️⃣ Testing imports...")
    from huggingface_hub import hf_hub_download
    from transformers import pipeline
    import joblib
    print("   ✅ All imports successful!")
    
    print("\n2️⃣ Downloading XGBoost model from Hugging Face...")
    local_model_path = hf_hub_download(
        repo_id="Manoj-palanisamy/smarttriage-models",
        filename="triage_assets_mingled.pkl",
        cache_dir="./hf_cache"
    )
    print(f"   ✅ Downloaded to: {local_model_path}")
    
    print("\n3️⃣ Loading XGBoost assets...")
    assets = joblib.load(local_model_path)
    print(f"   ✅ Loaded assets with keys: {list(assets.keys())}")
    
    print("\n4️⃣ Loading BERT model from Hugging Face...")
    exp_brain = pipeline(
        "text-classification",
        model="Manoj-palanisamy/smarttriage-models",
        tokenizer="Manoj-palanisamy/smarttriage-models"
    )
    print("   ✅ BERT model loaded successfully!")
    
    print("\n5️⃣ Testing BERT model inference...")
    test_result = exp_brain("Patient has severe chest pain and difficulty breathing")
    print(f"   ✅ Inference works! Result: {test_result}")
    
    print("\n" + "=" * 70)
    print("🎉 SUCCESS! ALL TESTS PASSED!")
    print("=" * 70)
    print("\n✨ Your models are working perfectly from Hugging Face!")
    print("\n📝 Next steps:")
    print("   1. Your app is ready to run with HF models")
    print("   2. Run: python app.py (with USE_HUGGINGFACE=true)")
    print("   3. Push code to GitHub (no large model files!)")
    print("\n💡 Cache location: ./hf_cache/")
    print("   (Models download once, then use cache)")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\n🔧 Troubleshooting:")
    print("   1. Check internet connection")
    print("   2. Verify models uploaded: https://huggingface.co/Manoj-palanisamy/smarttriage-models")
    print("   3. Try running upload_to_hf.py again if files are missing")
    import traceback
    traceback.print_exc()

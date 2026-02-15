"""
Upload SmartTriage Models to Hugging Face Hub
This script uploads your local model files to Hugging Face repository
"""

from huggingface_hub import HfApi, login
import os
import sys

# Configuration
REPO_ID = "Manoj-palanisamy/smarttriage-models"
LOCAL_MODEL_DIR = "models"

def check_files_exist():
    """Check if required model files exist locally"""
    files_to_upload = {
        "XGBoost Model": "models/triage_assets_mingled.pkl",
        "BERT Config": "models/experimental_brain/config.json",
        "BERT Model": "models/experimental_brain/model.safetensors",
        "Tokenizer Config": "models/experimental_brain/tokenizer_config.json",
        "Tokenizer": "models/experimental_brain/tokenizer.json"
    }
    
    print("\n🔍 Checking for local model files...")
    all_exist = True
    
    for name, path in files_to_upload.items():
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)  # Convert to MB
            print(f"  ✅ {name}: {path} ({size:.2f} MB)")
        else:
            print(f"  ❌ {name}: {path} NOT FOUND")
            all_exist = False
    
    return all_exist, files_to_upload

def upload_models():
    """Upload models to Hugging Face Hub"""
    print("\n" + "="*60)
    print("🤗 HUGGING FACE MODEL UPLOAD TOOL")
    print("="*60)
    print(f"📦 Repository: {REPO_ID}")
    print(f"📂 Local folder: {LOCAL_MODEL_DIR}/")
    print("="*60 + "\n")
    
    # Check if files exist
    all_exist, files_to_upload = check_files_exist()
    
    if not all_exist:
        print("\n❌ ERROR: Some required files are missing!")
        print("Please ensure all model files are in the 'models/' folder.")
        sys.exit(1)
    
    print("\n✅ All required files found!")
    
    # Login check
    print("\n🔑 Checking Hugging Face authentication...")
    try:
        api = HfApi()
        # Try to get user info to check if logged in
        user_info = api.whoami()
        print(f"✅ Logged in as: {user_info['name']}")
    except Exception as e:
        print("\n❌ Not logged in to Hugging Face!")
        print("\nPlease run the following command first:")
        print("  huggingface-cli login")
        print("\nOr login in Python:")
        print("  >>> from huggingface_hub import login")
        print("  >>> login()")
        print("\nGet your token from: https://huggingface.co/settings/tokens")
        sys.exit(1)
    
    # Confirm upload
    print("\n" + "="*60)
    print("⚠️  READY TO UPLOAD")
    print("="*60)
    print(f"This will upload {len(files_to_upload)} files to:")
    print(f"https://huggingface.co/{REPO_ID}")
    print("\nFiles to upload:")
    for name, path in files_to_upload.items():
        print(f"  • {name}")
    
    response = input("\nProceed with upload? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("\n❌ Upload cancelled.")
        sys.exit(0)
    
    # Upload files
    print("\n📤 Starting upload...\n")
    
    try:
        # Upload XGBoost pickle file
        print("1️⃣ Uploading XGBoost model (triage_assets_mingled.pkl)...")
        api.upload_file(
            path_or_fileobj="models/triage_assets_mingled.pkl",
            path_in_repo="triage_assets_mingled.pkl",
            repo_id=REPO_ID,
            repo_type="model",
        )
        print("   ✅ Uploaded successfully!\n")
        
        # Upload BERT model files
        print("2️⃣ Uploading BERT model files...")
        bert_files = {
            "config.json": "models/experimental_brain/config.json",
            "model.safetensors": "models/experimental_brain/model.safetensors",
            "tokenizer_config.json": "models/experimental_brain/tokenizer_config.json",
            "tokenizer.json": "models/experimental_brain/tokenizer.json"
        }
        
        for filename, local_path in bert_files.items():
            if os.path.exists(local_path):
                print(f"   Uploading {filename}...")
                api.upload_file(
                    path_or_fileobj=local_path,
                    path_in_repo=filename,
                    repo_id=REPO_ID,
                    repo_type="model",
                )
                print(f"   ✅ {filename} uploaded!")
            else:
                print(f"   ⚠️ {filename} not found, skipping...")
        
        print("\n" + "="*60)
        print("🎉 SUCCESS! All models uploaded!")
        print("="*60)
        print(f"\n🔗 View your models at:")
        print(f"   https://huggingface.co/{REPO_ID}")
        print(f"\n📝 Next steps:")
        print(f"   1. Set environment variable: USE_HUGGINGFACE=true")
        print(f"   2. Run your app: python app.py")
        print(f"   3. Models will be downloaded and cached automatically")
        print("\n✨ Your app is now ready for deployment without large files!")
        
    except Exception as e:
        print(f"\n❌ ERROR during upload: {e}")
        print("\nTroubleshooting:")
        print("  • Check your internet connection")
        print("  • Verify repository exists: https://huggingface.co/{REPO_ID}")
        print("  • Make sure repository is public")
        print("  • Try logging in again: huggingface-cli login")
        sys.exit(1)

if __name__ == "__main__":
    try:
        upload_models()
    except KeyboardInterrupt:
        print("\n\n❌ Upload cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

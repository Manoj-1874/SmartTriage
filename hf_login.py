"""
Simple Hugging Face Login Script
Paste your token when prompted
"""

from huggingface_hub import login

print("=" * 60)
print("🤗 HUGGING FACE LOGIN")
print("=" * 60)
print("\nYou will be prompted to enter your Hugging Face token.")
print("\n📋 Instructions:")
print("1. Copy your token from: https://huggingface.co/settings/tokens")
print("2. Paste it below (nothing will display while typing - this is normal)")
print("3. Press Enter")
print("\n" + "=" * 60)

try:
    # This will prompt for token input
    login()
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS! You are now logged in!")
    print("=" * 60)
    print("\n📝 Next step: Run the upload script")
    print("   python upload_to_hf.py")
    
except Exception as e:
    print(f"\n❌ Login failed: {e}")
    print("\nTroubleshooting:")
    print("- Make sure you copied the full token")
    print("- Token should start with 'hf_'")
    print("- Get a new token from: https://huggingface.co/settings/tokens")

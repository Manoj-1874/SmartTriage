"""
Hugging Face Token Verification & Login
This script helps you test and verify your token before uploading
"""

from huggingface_hub import login, HfApi
import sys

print("=" * 70)
print("🔑 HUGGING FACE TOKEN VERIFICATION")
print("=" * 70)
print("\n📋 Before you start, make sure you have:")
print("   1. Created a token at: https://huggingface.co/settings/tokens")
print("   2. Token has 'Write' permission (not just Read)")
print("   3. Token is active (not expired or deleted)")
print("\n💡 Your token should look like: hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890")
print("=" * 70)

# Get token from user
print("\n🔐 Please paste your Hugging Face token below:")
print("(Press Ctrl+C to cancel)\n")

try:
    token = input("Token: ").strip()
    
    # Validate token format
    if not token:
        print("\n❌ ERROR: No token entered!")
        sys.exit(1)
    
    if not token.startswith('hf_'):
        print("\n⚠️  WARNING: Token doesn't start with 'hf_'")
        print("Are you sure this is a valid Hugging Face token?")
        response = input("Continue anyway? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("❌ Cancelled.")
            sys.exit(0)
    
    if len(token) < 10:
        print("\n❌ ERROR: Token seems too short!")
        print("Valid tokens are usually 30-40+ characters long.")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("🔍 TESTING TOKEN...")
    print("=" * 70)
    
    # Test 1: Try to authenticate
    print("\n1️⃣ Testing authentication...")
    try:
        login(token=token, add_to_git_credential=False)
        print("   ✅ Authentication successful!")
    except Exception as e:
        print(f"   ❌ Authentication failed: {e}")
        print("\n🔧 Fix:")
        print("   - Go to: https://huggingface.co/settings/tokens")
        print("   - Delete the old token")
        print("   - Create a NEW token with 'Write' permission")
        print("   - Copy the NEW token and try again")
        sys.exit(1)
    
    # Test 2: Try to get user info
    print("\n2️⃣ Verifying token permissions...")
    try:
        api = HfApi(token=token)
        user_info = api.whoami()
        print(f"   ✅ Logged in as: {user_info['name']}")
        print(f"   📧 Email: {user_info.get('email', 'N/A')}")
        
        # Check if token has write access
        if 'write' in str(user_info.get('auth', {}).get('accessToken', {}).get('role', '')).lower():
            print("   ✅ Token has WRITE access")
        else:
            print("   ⚠️  Token may not have write access")
            print("      You might not be able to upload files")
    except Exception as e:
        print(f"   ⚠️  Could not verify permissions: {e}")
    
    # Test 3: Check repository access
    print("\n3️⃣ Checking repository access...")
    try:
        repo_id = "Manoj-palanisamy/smarttriage-models"
        api.repo_info(repo_id=repo_id, repo_type="model")
        print(f"   ✅ Can access repository: {repo_id}")
    except Exception as e:
        print(f"   ⚠️  Repository check: {e}")
        print(f"      Make sure {repo_id} exists and is accessible")
    
    # Save token
    print("\n4️⃣ Saving token for future use...")
    try:
        login(token=token, add_to_git_credential=True)
        print("   ✅ Token saved successfully!")
    except Exception as e:
        print(f"   ⚠️  Could not save token: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 SUCCESS! YOUR TOKEN IS VALID AND READY!")
    print("=" * 70)
    print("\n📝 Next steps:")
    print("   1. Run: python upload_to_hf.py")
    print("   2. Your models will be uploaded automatically")
    print("   3. Wait for the upload to complete (5-10 minutes)")
    print("\n💡 Your token is now saved. You won't need to enter it again!")
    
except KeyboardInterrupt:
    print("\n\n❌ Cancelled by user.")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    print("\n🔧 Troubleshooting:")
    print("   1. Go to: https://huggingface.co/settings/tokens")
    print("   2. Click 'New token'")
    print("   3. Name: SmartTriage-Upload")
    print("   4. Role: WRITE (important!)")
    print("   5. Copy the token")
    print("   6. Run this script again")
    sys.exit(1)

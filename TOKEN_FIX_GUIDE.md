# 🚨 TOKEN ERROR - QUICK FIX GUIDE

## ❌ Problem: "Invalid user token"

This means your token is either:
- ❌ Not copied correctly (missing characters)
- ❌ Doesn't have WRITE permission
- ❌ Was deleted or expired
- ❌ Has extra spaces/characters

---

## ✅ SOLUTION: Create a NEW Token

### **Step 1: Go to Token Settings**
🔗 https://huggingface.co/settings/tokens

### **Step 2: Create New Token**
1. Click the **"New token"** button
2. Fill in the form:
   - **Name:** `SmartTriage-Upload`
   - **Type:** Select **"Write"** ⚠️ (NOT "Read" - very important!)
3. Click **"Generate token"**

### **Step 3: Copy Token Carefully**
- A new page will show your token
- It looks like: `hf_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890`
- Click the **"Copy"** button (don't select manually)
- ⚠️ **Important:** This is your ONLY chance to see it!

### **Step 4: Test Your Token**
```bash
python verify_token.py
```

When prompted:
1. **Right-click** in the PowerShell window to paste
2. Or press **Ctrl + V**
3. Press **Enter**

---

## 🎯 What to Look For

### ❌ **BAD Token (Read Only):**
```
Token settings:
Type: Read
```

### ✅ **GOOD Token (Write Access):**
```
Token settings:
Type: Write
```

---

## 📋 Quick Checklist

Before running `verify_token.py`, make sure:

- [ ] Token is BRAND NEW (just created)
- [ ] Token has **WRITE** permission (not just Read)
- [ ] You copied the ENTIRE token (no spaces at start/end)
- [ ] Token starts with `hf_`
- [ ] Token is at least 30 characters long

---

## 🔧 Alternative: Manual Token Entry

If copy-paste isn't working, try this:

1. Open: `verify_token.py` in Notepad
2. Find the line: `token = input("Token: ").strip()`
3. Replace with: `token = "hf_PASTE_YOUR_TOKEN_HERE"`
4. Save the file
5. Run: `python verify_token.py`

---

## 🚀 Once Token Works

After successful verification, run:
```bash
python upload_to_hf.py
```

This will upload all your model files!

---

## 💡 Pro Tip

If you keep having issues, try:
1. Delete ALL old tokens from: https://huggingface.co/settings/tokens
2. Create ONE new token with Write access
3. Copy it immediately after creation
4. Paste into `verify_token.py`

---

**Run this now:**
```bash
python verify_token.py
```

# 🚀 Quick Start: Upload Models to Hugging Face

## ✅ Checklist

### Step 1: Install Required Package
```bash
pip install huggingface_hub
```

### Step 2: Login to Hugging Face
```bash
huggingface-cli login
```
**Get your token from:** https://huggingface.co/settings/tokens

### Step 3: Upload Your Models
```bash
python upload_to_hf.py
```

This will upload:
- ✅ `triage_assets_mingled.pkl` (XGBoost model)
- ✅ `config.json` (BERT config)
- ✅ `model.safetensors` (BERT weights)
- ✅ `tokenizer_config.json` (Tokenizer settings)
- ✅ `tokenizer.json` (Tokenizer vocabulary)

### Step 4: Test with Hugging Face Models
```bash
# Windows PowerShell
$env:USE_HUGGINGFACE = "true"
python app.py

# Windows CMD
set USE_HUGGINGFACE=true
python app.py
```

### Step 5: Verify Upload
Visit: https://huggingface.co/Manoj-palanisamy/smarttriage-models

You should see all 5 files uploaded!

---

## 🎯 Current Status

Repository: **Manoj-palanisamy/smarttriage-models** ✅
- Created: Yes ✅
- Public: Yes ✅
- Files uploaded: ⬜ (Do this now!)

---

## 💡 Pro Tips

1. **For Development:** Use local models (faster)
   - Just run `python app.py` without environment variable

2. **For Production/GitHub:** Use Hugging Face models
   - Set `USE_HUGGINGFACE=true`
   - No large files in your GitHub repo!

3. **First Load Takes Time:** Models download and cache
   - Subsequent runs are instant (uses cache)

4. **Cache Location:** `./hf_cache/` folder
   - Safe to delete if you want fresh downloads

---

## 📦 What Gets Uploaded

| File | Size | Purpose |
|------|------|---------|
| triage_assets_mingled.pkl | ~50-100MB | XGBoost + encoders + scaler |
| model.safetensors | ~100-400MB | BERT model weights |
| config.json | ~1KB | BERT configuration |
| tokenizer_config.json | ~1KB | Tokenizer settings |
| tokenizer.json | ~500KB-2MB | Tokenizer vocabulary |

---

## 🔥 Ready to Upload?

Run this now:
```bash
python upload_to_hf.py
```

The script will:
1. ✅ Check if all files exist locally
2. ✅ Verify you're logged in to Hugging Face
3. ✅ Show you what will be uploaded
4. ✅ Ask for confirmation
5. ✅ Upload all files with progress
6. ✅ Provide next steps

**Estimated time:** 2-10 minutes (depending on internet speed)

---

## ❓ Need Help?

See detailed guide: `HUGGINGFACE_SETUP.md`

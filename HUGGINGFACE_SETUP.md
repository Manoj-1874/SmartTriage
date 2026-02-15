# 🤗 Hugging Face Model Setup Guide

## Overview
Your SmartTriage Dashboard now supports loading models from Hugging Face Hub, allowing you to host large model files (>100MB) externally and avoid GitHub's file size limits.

**Your Repository:** https://huggingface.co/Manoj-palanisamy/smarttriage-models

---

## 📋 Prerequisites

1. **Hugging Face Account** ✅ (Already created: Manoj-palanisamy)
2. **Repository Created** ✅ (smarttriage-models)
3. **Local Models** (in `models/` folder)

---

## 🚀 Step-by-Step Setup

### **Step 1: Install Hugging Face CLI**

```bash
pip install huggingface_hub
```

### **Step 2: Login to Hugging Face**

```bash
# Login via CLI
huggingface-cli login
```

When prompted, enter your Hugging Face access token:
- Go to: https://huggingface.co/settings/tokens
- Click "New token"
- Name it: "SmartTriage Upload"
- Select "Write" access
- Copy the token and paste it in the terminal

### **Step 3: Prepare Your Model Files**

Your local model files that need to be uploaded:

```
models/
├── experimental_brain/           # BERT model folder
│   ├── config.json
│   ├── model.safetensors
│   ├── tokenizer_config.json
│   └── tokenizer.json
└── triage_assets_mingled.pkl     # XGBoost + encoders (pickle file)
```

### **Step 4: Upload Models to Hugging Face**

#### **Option A: Using Python Script (Recommended)**

Create `upload_to_hf.py`:

```python
from huggingface_hub import HfApi
import os

api = HfApi()

# Your repository ID
repo_id = "Manoj-palanisamy/smarttriage-models"

print("📤 Uploading models to Hugging Face...")

# Upload the pickle file (XGBoost models)
print("1️⃣ Uploading triage_assets_mingled.pkl...")
api.upload_file(
    path_or_fileobj="models/triage_assets_mingled.pkl",
    path_in_repo="triage_assets_mingled.pkl",
    repo_id=repo_id,
    repo_type="model",
)
print("✅ Pickle file uploaded!")

# Upload BERT model files
print("2️⃣ Uploading BERT model files...")
bert_files = [
    "models/experimental_brain/config.json",
    "models/experimental_brain/model.safetensors",
    "models/experimental_brain/tokenizer_config.json",
    "models/experimental_brain/tokenizer.json"
]

for file_path in bert_files:
    if os.path.exists(file_path):
        filename = os.path.basename(file_path)
        print(f"   Uploading {filename}...")
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=filename,
            repo_id=repo_id,
            repo_type="model",
        )
        print(f"   ✅ {filename} uploaded!")
    else:
        print(f"   ⚠️ {file_path} not found, skipping...")

print("\n🎉 All models uploaded successfully!")
print(f"🔗 View your models at: https://huggingface.co/{repo_id}")
```

Run it:
```bash
python upload_to_hf.py
```

#### **Option B: Using Web Interface**

1. Go to: https://huggingface.co/Manoj-palanisamy/smarttriage-models
2. Click "Files and versions" tab
3. Click "Add file" → "Upload files"
4. Drag and drop:
   - `triage_assets_mingled.pkl`
   - `config.json`
   - `model.safetensors`
   - `tokenizer_config.json`
   - `tokenizer.json`
5. Click "Commit changes to main"

#### **Option C: Using Git LFS (For Large Files)**

```bash
# Install Git LFS
git lfs install

# Clone your HF repository
git clone https://huggingface.co/Manoj-palanisamy/smarttriage-models
cd smarttriage-models

# Copy your model files
cp ../SmartTriage_Dashboard/models/triage_assets_mingled.pkl .
cp ../SmartTriage_Dashboard/models/experimental_brain/* .

# Track large files with Git LFS
git lfs track "*.pkl"
git lfs track "*.safetensors"

# Add and commit
git add .
git commit -m "Add SmartTriage AI models"
git push
```

---

## 🔧 Configure Your App

### **Method 1: Use Environment Variable (Recommended for Production)**

```bash
# Windows PowerShell
$env:USE_HUGGINGFACE = "true"
python app.py

# Windows CMD
set USE_HUGGINGFACE=true
python app.py

# Linux/Mac
export USE_HUGGINGFACE=true
python app.py
```

### **Method 2: Modify Code Directly (For Testing)**

In `app.py`, change line 31:

```python
# Change from:
USE_HUGGINGFACE = os.getenv('USE_HUGGINGFACE', 'false').lower() == 'true'

# To:
USE_HUGGINGFACE = True  # Always use Hugging Face
```

---

## 📦 Final File Structure on Hugging Face

Your repository should look like this:

```
Manoj-palanisamy/smarttriage-models/
├── README.md (auto-generated)
├── triage_assets_mingled.pkl       # XGBoost model + encoders
├── config.json                     # BERT config
├── model.safetensors               # BERT weights
├── tokenizer_config.json           # Tokenizer settings
└── tokenizer.json                  # Tokenizer vocabulary
```

---

## ✅ Testing Your Setup

### **1. Test with Hugging Face Models**

```bash
# Set environment variable
$env:USE_HUGGINGFACE = "true"

# Run the app
python app.py
```

You should see:
```
🏥 Loading SmartTriage Dual-Brain Engine...
📥 Downloading models from Hugging Face Hub...
✅ Models loaded from Hugging Face Hub successfully!
✅ System 1 (XGBoost) & System 2 (Shadow Brain) Online.
```

### **2. Test with Local Models (Fallback)**

```bash
# Don't set the environment variable (or set to false)
python app.py
```

You should see:
```
🏥 Loading SmartTriage Dual-Brain Engine...
📂 Loading models from local storage...
✅ Models loaded from local storage successfully!
✅ System 1 (XGBoost) & System 2 (Shadow Brain) Online.
```

---

## 🎯 Deployment Strategies

### **During Development:**
- Use **local models** for faster iteration
- No internet required
- Instant loading

### **For Production/GitHub:**
- Use **Hugging Face models**
- No large files in repository
- Models cached after first download

### **For Presentation:**
- Upload models to HF **before** demo
- Set `USE_HUGGINGFACE=true`
- Models download once and cache locally

---

## 🔄 Model Updates

When you update your models:

```bash
# Re-upload using Python script
python upload_to_hf.py

# Or manually delete old files and upload new ones via web interface
```

The app will automatically download the latest version.

---

## 📊 Model Cards (Optional but Recommended)

Create a `README.md` in your HF repository describing your models:

```markdown
---
language: en
license: mit
tags:
- medical
- triage
- classification
- healthcare
---

# SmartTriage AI Models

This repository contains the dual-brain AI system for SmartTriage Dashboard:

## Models Included

1. **XGBoost Risk Classifier** (`triage_assets_mingled.pkl`)
   - Predicts patient risk levels (HIGH/MEDIUM/LOW)
   - Trained on vital signs and medical history
   - Includes encoders and feature scalers

2. **BERT Symptom Analyzer** (transformer model)
   - Semantic analysis of patient symptoms
   - Emergency detection system
   - Fine-tuned for medical text classification

## Usage

```python
from transformers import pipeline
from huggingface_hub import hf_hub_download
import joblib

# Load XGBoost models
model_path = hf_hub_download(
    repo_id="Manoj-palanisamy/smarttriage-models",
    filename="triage_assets_mingled.pkl"
)
assets = joblib.load(model_path)

# Load BERT model
classifier = pipeline(
    "text-classification",
    model="Manoj-palanisamy/smarttriage-models"
)
```

## License

MIT License - See LICENSE file for details
```

---

## 🚨 Troubleshooting

### **Issue: "Repository not found"**
- Make sure repository is **public**
- Check the repo ID: `Manoj-palanisamy/smarttriage-models`

### **Issue: "File not found on Hugging Face"**
- Verify files are uploaded: https://huggingface.co/Manoj-palanisamy/smarttriage-models/tree/main
- Check file names match exactly

### **Issue: "Authentication failed"**
- Run `huggingface-cli login` again
- Use a token with **write** access

### **Issue: Models download slowly**
- First download takes time (models are large)
- Subsequent runs use cached models
- Cache location: `./hf_cache/` folder

### **Issue: "Module not found: huggingface_hub"**
```bash
pip install huggingface_hub
```

---

## 🎉 Next Steps

1. ✅ Update app.py with your HF repo ID (DONE)
2. ⬜ Install `huggingface_hub`: `pip install huggingface_hub`
3. ⬜ Login to HF: `huggingface-cli login`
4. ⬜ Upload models using one of the methods above
5. ⬜ Test with `USE_HUGGINGFACE=true`
6. ⬜ Push to GitHub (no large files!)
7. ⬜ Present your project! 🚀

---

## 📚 Additional Resources

- Hugging Face Hub Documentation: https://huggingface.co/docs/hub/index
- Model Upload Guide: https://huggingface.co/docs/hub/models-uploading
- Git LFS Guide: https://git-lfs.github.com/

---

**Your models will be publicly accessible for your presentation demo!** 🎓

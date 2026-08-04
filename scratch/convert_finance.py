from PIL import Image
import os

source_path = r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\financial_projections_dashboard_1778674236980.png'
dest_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\financial_assumptions.jpg'

try:
    with Image.open(source_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(dest_path, "JPEG", quality=85, optimize=True)
        
    size_kb = os.path.getsize(dest_path) / 1024
    print(f"Successfully converted. Size: {size_kb:.2f} KB")
except Exception as e:
    print(f"Error: {e}")

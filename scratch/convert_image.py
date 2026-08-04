from PIL import Image
import os

source_path = r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\rural_indian_persona_muthu_1778663967969.png'
dest_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\muthu_persona.jpg'

try:
    with Image.open(source_path) as img:
        # Convert to RGB if needed (PNGs can be RGBA)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Save as JPG with quality adjustment to keep it under 1MB
        # 85 is usually a good balance of quality and size
        img.save(dest_path, "JPEG", quality=85, optimize=True)
        
    size_kb = os.path.getsize(dest_path) / 1024
    print(f"Successfully converted to JPG. Size: {size_kb:.2f} KB")
    print(f"Saved to: {dest_path}")
except Exception as e:
    print(f"Error: {e}")

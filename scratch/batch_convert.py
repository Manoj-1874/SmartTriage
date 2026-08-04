from PIL import Image
import os

images = {
    'pitch_team.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\verification_team_tech_1778669212243.png',
    'pitch_industry.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\verification_industry_tech_1778669239074.png',
    'pitch_problem.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\verification_problem_scam_1778669264828.png',
    'pitch_customers.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\verification_customers_safe_1778669294220.png',
    'pitch_opening.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\verification_abstract_opening_1778669317571.png'
}

output_dir = r'e:\Nilal_thiruvila\SmartTriage_Dashboard'

for filename, source in images.items():
    dest = os.path.join(output_dir, filename)
    try:
        with Image.open(source) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(dest, "JPEG", quality=85, optimize=True)
        size_kb = os.path.getsize(dest) / 1024
        print(f"Converted {filename}: {size_kb:.2f} KB")
    except Exception as e:
        print(f"Error converting {filename}: {e}")

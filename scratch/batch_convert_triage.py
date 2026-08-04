from PIL import Image
import os

images = {
    'triage_team.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\smart_triage_team_1778674778757.png',
    'triage_industry.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\smart_triage_phc_industry_1778674803152.png',
    'triage_problem.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\smart_triage_problem_rural_1778674830405.png',
    'triage_customers.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\smart_triage_customers_vhn_1778674864660.png',
    'triage_opening.jpg': r'C:\Users\HP\.gemini\antigravity\brain\86fda951-9389-4a2f-a0c3-ffa90c3d00af\smart_triage_opening_abstract_1778674887749.png'
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

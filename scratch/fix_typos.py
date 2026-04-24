import os

file_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\utils\integrated_dual_brain_risk.py'

if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Fix typos
    content = content.replace('Fusingg', 'Fusing')
    content = content.replace('Esccalating', 'Escalating')
    content = content.replace('semanticc', 'semantic')
    
    # Add a unique marker to prove it's updated
    content = content.replace('[DUAL-BRAIN-SYSTEM-3]', '[DUAL-BRAIN-v2.2-STABLE]')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully fixed typos and updated version marker.")
else:
    print(f"File not found: {file_path}")

import os

file_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\utils\integrated_dual_brain_risk.py'

if os.path.exists(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Try multiple encodings
    for encoding in ['utf-8', 'utf-16', 'cp1252']:
        try:
            content = data.decode(encoding)
            new_content = content.replace('Fussing', 'Fusing')
            new_content = new_content.replace('detecteed', 'detected')
            
            if content != new_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Successfully fixed typos using {encoding} encoding.")
                break
        except:
            continue
    else:
        print("Could not find typos or determine encoding.")
else:
    print(f"File not found: {file_path}")

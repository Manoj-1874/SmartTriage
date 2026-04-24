import os

file_path = r'e:\Nilal_thiruvila\SmartTriage_Dashboard\utils\integrated_dual_brain_risk.py'

if os.path.exists(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
    
    # Binary replacement to avoid encoding issues
    replacements = [
        (b'Fussing', b'Fusing'),
        (b'detecteed', b'detected')
    ]
    
    new_data = data
    for old, new in replacements:
        if old in new_data:
            new_data = new_data.replace(old, new)
            print(f"Fixed typo: {old.decode()} -> {new.decode()}")
    
    if new_data != data:
        with open(file_path, 'wb') as f:
            f.write(new_data)
        print("Successfully updated file with binary replacements.")
    else:
        print("No typos found in binary data.")
else:
    print(f"File not found: {file_path}")

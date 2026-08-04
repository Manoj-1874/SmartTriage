with open('templates/doctor_dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'body' in line.lower() or 'navbar' in line.lower() or 'header' in line.lower() or 'logout' in line.lower():
            print(f"{i+1}: {line.strip()}")

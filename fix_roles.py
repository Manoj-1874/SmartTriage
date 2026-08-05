import re

with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix phc_nurse strict role checks
c = re.sub(r"if current_user\.role != 'phc_nurse':", r"if current_user.role not in ['phc_nurse', 'doctor']:", c)

# Fix pharmacist strict role checks if any
c = re.sub(r"if current_user\.role != 'pharmacist':", r"if current_user.role not in ['pharmacist', 'doctor']:", c)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)

print('Replacement successful.')

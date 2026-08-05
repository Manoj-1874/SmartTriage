with open('templates/sidebar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace user variables with current_user
content = content.replace('user.role', 'current_user.role')
content = content.replace('user.fullname', 'current_user.fullname')
content = content.replace('{% if user %}', '{% if current_user.is_authenticated %}')

with open('templates/sidebar.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated sidebar.html to use current_user")

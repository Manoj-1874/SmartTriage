with open('templates/doctor_dashboard.html', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('<nav class="s-nav">')
end = text.find('</nav>', start)
print(text[start:end+6])

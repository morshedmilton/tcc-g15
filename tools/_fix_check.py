import io

p = 'tools/check_env.py'
s = io.open(p, encoding='utf-8', newline='').read()

old = '["Custom", "Balanced", "Performance", "Quiet", "G_Mode"]'
new = '["Auto", "Balanced", "G_Mode", "Custom"]'

if old in s:
    s = s.replace(old, new)
    io.open(p, 'w', encoding='utf-8', newline='').write(s)
    print('done')
else:
    print('NOT FOUND')
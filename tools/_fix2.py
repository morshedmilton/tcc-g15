import io

p = 'src/GUI/AppGUI.py'
lines = io.open(p, encoding='utf-8', newline='').read().split('\r\n')

old = lines[168:172]  # 4 lines
new = [
    '        # Set main window props',
    '        # Fixed size to hold two thermal panels (380*2 + margins) + 5 mode buttons + failsafe row.',
    '        # adjustSize() fails because the layout\'s sizeHint is too optimistic (it can squeeze).',
    '        self.setFixedSize(900, 330)',
]

print('match:', lines[168:172] == old)
lines[168:172] = new
io.open(p, 'w', encoding='utf-8', newline='').write('\r\n'.join(lines))
print('done')
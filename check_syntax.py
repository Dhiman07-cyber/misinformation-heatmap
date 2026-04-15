import ast
with open('backend/main_clean.py', encoding='utf-8') as f:
    src = f.read()
ast.parse(src)
print('Syntax OK')

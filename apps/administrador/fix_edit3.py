import re

with open('apps/administrador/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove duplicate return statement
content = content.replace(
    '''    return render(request, "administrador/tema_semanal.html", {"usuario": admin, "modo": "generar"})

return render(request, "administrador/tema_semanal.html", {"usuario": admin, "modo": "generar"})''',
    '''    return render(request, "administrador/tema_semanal.html", {"usuario": admin, "modo": "generar"})'''
)

# Fix historial block indentation - the return is inside if not outside
old_historial = '''        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "modo": "historial",
            "temas": temas
        })

    if modo == "editar":'''

new_historial = '''        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "modo": "historial",
            "temas": temas
        })

    if modo == "editar":'''

content = content.replace(old_historial, new_historial)

with open('apps/administrador/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed")
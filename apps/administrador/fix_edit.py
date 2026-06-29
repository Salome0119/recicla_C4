import re

with open('apps/administrador/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove misplaced preview_data line
content = re.sub(r".*preview_data.*", '', content)

# Add edit handler before the final return statement
old_return = 'return render(request, "administrador/tema_semanal.html", {"usuario": admin, "modo": "generar"})'
new_handler = '''    if modo == "editar":
        titulo_ed = request.GET.get("titulo", "")
        vista_ed = request.GET.get("vista", "")
        preview = request.session.get("preview_data", {})
        preguntas_json = json.dumps(preview.get("preguntas", []))
        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "preview": preview,
            "preview_preguntas_json": preguntas_json,
            "tema_titulo": titulo_ed,
            "vista_destino": vista_ed,
            "modo": "editar"
        })

''' + old_return

content = content.replace(old_return, new_handler)

with open('apps/administrador/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed")
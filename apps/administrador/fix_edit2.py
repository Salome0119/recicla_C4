import re

with open('apps/administrador/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the indentation issue - the edit block was added inside historial block incorrectly
old_block = '''        "temas": temas
        })



        if modo == "editar":
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
        })'''

new_block = '''        "temas": temas
        })

    if modo == "editar":
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

    return render(request, "administrador/tema_semanal.html", {"usuario": admin, "modo": "generar"})'''

content = content.replace(old_block, new_block)

with open('apps/administrador/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed")
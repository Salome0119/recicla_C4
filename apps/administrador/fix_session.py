import re

with open('apps/administrador/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add session save before vista_previa return
old_vista_previa = '''        if result is None:
            result = fallback_content

        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "preview": result,'''

new_vista_previa = '''        if result is None:
            result = fallback_content

        request.session["preview_data"] = {"contenido": result.get("contenido", ""), "preguntas": result.get("preguntas", [])}

        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "preview": result,'''

content = content.replace(old_vista_previa, new_vista_previa)

with open('apps/administrador/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed")
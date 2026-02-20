import os
from io import BytesIO
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa

def link_callback(uri, rel):
    """
    Convierte rutas HTML (STATIC, MEDIA) a rutas absolutas en el sistema de archivos
    para que xhtml2pdf pueda acceder a ellas.
    """
    # Archivos de media
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    # Archivos estáticos
    elif uri.startswith(settings.STATIC_URL):
        # Primero busca en STATIC_ROOT
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        if not os.path.isfile(path) and settings.STATICFILES_DIRS:
            # Si no existe en STATIC_ROOT, busca en STATICFILES_DIRS[0]
            path = os.path.join(settings.STATICFILES_DIRS[0], uri.replace(settings.STATIC_URL, ""))
    else:
        return uri

    if not os.path.isfile(path):
        raise Exception(f"No se encontró el archivo {path}")
    return path

def render_to_pdf(template_src, context_dict={}):
    """
    Renderiza una plantilla HTML a PDF usando xhtml2pdf.
    """
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()

    pdf = pisa.pisaDocument(
        BytesIO(html.encode("UTF-8")),   # Codificación segura
        result,
        link_callback=link_callback      # Resolver rutas estáticas y media
    )

    if not pdf.err:
        return result.getvalue()  # Devuelve los bytes del PDF
    return None

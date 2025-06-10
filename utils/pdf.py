from django.template.loader import render_to_string
from weasyprint import HTML
from io import BytesIO

def render_to_pdf(template_src, context_dict={}):
    html_string = render_to_string(template_src, context_dict)
    html = HTML(string=html_string, base_url=None)  # base_url 설정 가능
    result = BytesIO()
    html.write_pdf(target=result)
    return result.getvalue()


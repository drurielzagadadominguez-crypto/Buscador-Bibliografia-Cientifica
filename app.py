# -*- coding: utf-8 -*-
import os
import re
import requests
import urllib3
from io import BytesIO
from flask import Flask, request, send_file, render_template_string
import openpyxl
from openpyxl.styles import Font, PatternFill
from bs4 import BeautifulSoup
import PyPDF2

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuración del DOI del Dr. Zagada
DOI_TEXT = "10.5281/zenodo.19323977"
DOI_URL = "https://doi.org/10.5281/zenodo.19323978"

TRANSLATIONS = {
    'es': {
        'title': 'Buscador de Bibliografía Científica',
        'lang_btn': 'English Version',
        'lang_url': '/?lang=en',
        'hero_title': '🔬 Extractor Científico Avanzado',
        'hero_sub': 'Búsqueda IA + Scraping de PDFs y Webs',
        'tut_title': '🔑 ¿Cómo obtener tu API Key gratuita?',
        'tut_p': 'Necesitas una clave gratuita de Groq:',
        'tut_li1': 'Regístrate en <a href="https://console.groq.com/" target="_blank">console.groq.com</a>.',
        'tut_li2': 'Ve a <b>"API Keys"</b> y crea una.',
        'lbl_api': 'Tu API Key de Groq:',
        'ph_api': 'gsk_.......................................',
        'lbl_tema': 'Tema de investigación:',
        'ph_tema': 'Ej: Inteligencia Artificial en Medicina',
        'lbl_idioma': 'Idioma de los artículos:',
        'opt_es': 'Español',
        'opt_en': 'Inglés',
        'lbl_limite': 'Cantidad de artículos:',
        'btn_submit': 'Generar y Descargar Excel 📊',
        'loading_title': 'Extrayendo información...',
        'loading_text': 'Leyendo webs y PDFs. No cierres esta página.',
        'cred_title': '👨‍🔬 Créditos y Citación',
        'cred_author': 'Elaborado por el <b>Dr. Utiel Zagada Dominguez</b>.',
        'cred_cite': 'Si esta herramienta le fue de utilidad, favor de citarlo como proveedor tecnológico.',
        'cred_doi': f'<b>DOI:</b> <a href="{DOI_URL}" target="_blank">{DOI_TEXT}</a>'
    },
    'en': {
        'title': 'Scientific Bibliography Search Engine',
        'lang_btn': 'Versión en Español',
        'lang_url': '/?lang=es',
        'hero_title': '🔬 Advanced Scientific Extractor',
        'hero_sub': 'AI Search + PDF & Web Scraping',
        'tut_title': '🔑 How to get your free API Key?',
        'tut_p': 'You need a free Groq key:',
        'tut_li1': 'Sign up at <a href="https://console.groq.com/" target="_blank">console.groq.com</a>.',
        'tut_li2': 'Go to <b>"API Keys"</b> and create one.',
        'lbl_api': 'Your Groq API Key:',
        'ph_api': 'gsk_.......................................',
        'lbl_tema': 'Research topic:',
        'ph_tema': 'Ex: Artificial Intelligence in Medicine',
        'lbl_idioma': 'Language of articles:',
        'opt_es': 'Spanish',
        'opt_en': 'English',
        'lbl_limite': 'Amount of articles:',
        'btn_submit': 'Generate and Download Excel 📊',
        'loading_title': 'Extracting information...',
        'loading_text': 'Reading webs and PDFs. Do not close this page.',
        'cred_title': '👨‍🔬 Credits & Citation',
        'cred_author': 'Developed by <b>Dr. Utiel Zagada Dominguez</b>.',
        'cred_cite': 'If you found this tool useful, please cite him as the technological provider.',
        'cred_doi': f'<b>DOI:</b> <a href="{DOI_URL}" target="_blank">{DOI_TEXT}</a>'
    }
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t.title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f7f6; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .card { border-radius: 15px; box-shadow: 0 10px 20px rgba(0,0,0,0.1); border: none; overflow: hidden; }
        #loading { display: none; }
        .hero { background: linear-gradient(135deg, #0d6efd 0%, #0dcaf0 100%); color: white; padding: 25px; text-align: center; position: relative;}
        .lang-switch { position: absolute; top: 15px; right: 20px; }
        .tutorial-box { background-color: #e9f7fe; border-left: 5px solid #0dcaf0; padding: 15px; border-radius: 5px; font-size: 0.9rem; }
        .credits-box { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px; font-size: 0.85rem; color: #495057; }
    </style>
</head>
<body>
<div class="container mt-4 mb-5">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="hero">
                    <a href="{{ t.lang_url }}" class="btn btn-sm btn-light fw-bold lang-switch">{{ t.lang_btn }}</a>
                    <h2 class="mb-0 mt-3">{{ t.hero_title }}</h2>
                    <p class="mt-2 mb-0">{{ t.hero_sub }}</p>
                </div>
                <div class="card-body p-4">
                    <div class="tutorial-box mb-4">
                        <h6 class="fw-bold text-primary">{{ t.tut_title }}</h6>
                        <ol class="mb-0">
                            <li>{{ t.tut_li1 | safe }}</li>
                            <li>{{ t.tut_li2 | safe }}</li>
                        </ol>
                    </div>

                    <form id="searchForm" action="/procesar" method="POST" onsubmit="showLoading()">
                        <input type="hidden" name="ui_lang" value="{{ lang }}">
                        <div class="mb-3">
                            <label class="form-label fw-bold">{{ t.lbl_api }}</label>
                            <input type="password" class="form-control" name="api_key" required placeholder="{{ t.ph_api }}">
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">{{ t.lbl_tema }}</label>
                            <input type="text" class="form-control" name="tema" required placeholder="{{ t.ph_tema }}">
                        </div>
                        <div class="row mb-4">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">{{ t.lbl_idioma }}</label>
                                <select class="form-select" name="idioma">
                                    <option value="es" {% if lang == 'es' %}selected{% endif %}>{{ t.opt_es }}</option>
                                    <option value="en" {% if lang == 'en' %}selected{% endif %}>{{ t.opt_en }}</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">{{ t.lbl_limite }}</label>
                                <input type="number" class="form-control" name="limite" value="10" min="1" max="40">
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary w-100 py-2 fs-5 fw-bold">{{ t.btn_submit }}</button>
                    </form>

                    <div id="loading" class="text-center mt-5">
                        <div class="spinner-border text-primary" style="width: 3rem; height: 3rem;"></div>
                        <h4 class="mt-3">{{ t.loading_title }}</h4>
                        <p>{{ t.loading_text | safe }}</p>
                    </div>

                    <div class="credits-box mt-4">
                        <h6 class="fw-bold mb-1 text-dark">{{ t.cred_title }}</h6>
                        <p class="mb-1">{{ t.cred_author | safe }}</p>
                        <p class="mb-2 text-muted"><i>{{ t.cred_cite }}</i></p>
                        <div class="p-2 bg-white border rounded text-center">
                            {{ t.cred_doi | safe }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
<script>
    function showLoading() {
        document.getElementById('searchForm').style.display = 'none';
        document.getElementById('loading').style.display = 'block';
    }
</script>
</body>
</html>
"""

API_URL = "https://api.groq.com/openai/v1/chat/completions"

def llamar_ia(prompt, user_api_key):
    payload = {"model": "llama3-70b-8192", "messages":[{"role": "user", "content": prompt}], "temperature": 0.2}
    headers = {"Authorization": f"Bearer {user_api_key}", "Content-Type": "application/json"}
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return r.json()['choices'][0]['message']['content']
    except: return ""

def buscar_referencias(tema, user_api_key, limite):
    query = tema.replace(' ', '+')
    url = f"https://api.crossref.org/works?query={query}&rows={limite}&filter=type:journal-article"
    referencias = []
    try:
        res = requests.get(url, timeout=20).json()
        items = res.get("message", {}).get("items", [])
        for i in items:
            referencias.append({
                "autores": ", ".join([f"{a.get('family','')}" for a in i.get("author",[])]) or "Anon",
                "titulo": i.get("title",[tema])[0], 
                "revista": i.get("container-title",["Journal"])[0], 
                "doi": f"https://doi.org/{i.get('DOI','')}"
            })
    except: pass
    return referencias

app = Flask(__name__)

@app.route('/')
def index():
    lang = request.args.get('lang', 'es')
    return render_template_string(HTML_TEMPLATE, lang=lang, t=TRANSLATIONS.get(lang, TRANSLATIONS['es']))

@app.route('/procesar', methods=['POST'])
def procesar():
    api_key = request.form.get('api_key')
    tema = request.form.get('tema')
    limite = int(request.form.get('limite', 10))
    ui_lang = request.form.get('ui_lang', 'es')
    
    refs = buscar_referencias(tema, api_key, limite)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Autores", "Título", "Revista", "DOI Link"])
    for r in refs:
        ws.append([r['autores'], r['titulo'], r['revista'], r['doi']])
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, download_name=f"Bibliografia_{tema[:15]}.xlsx", as_attachment=True)

if __name__ == '__main__':
    app.run()

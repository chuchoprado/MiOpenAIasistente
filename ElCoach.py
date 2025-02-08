from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Inicializa Flask
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ✅ Carga credenciales de Google Sheets desde variables de entorno
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD_ElCoach")

if not CREDENTIALS_JSON:
    raise ValueError("❌ ERROR: Falta la credencial de Google Sheets en las variables de entorno.")

credentials_dict = json.loads(CREDENTIALS_JSON)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

# Conectar a Google Sheets
def get_sheet():
    try:
        client = gspread.authorize(credentials)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        logging.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
        return None

# ✅ Endpoint mejorado con búsqueda flexible
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    category = request.args.get("category")
    tag = request.args.get("tag")

    logging.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con la hoja de cálculo"}), 500

    try:
        # ✅ Normaliza datos para hacer la búsqueda sin importar mayúsculas o #
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().lstrip("#").strip() if tag else None

        rows = sheet.get_all_records()
        logging.info(f"✅ Total de filas obtenidas: {len(rows)}")

        # ✅ Filtrado: reconoce múltiples etiquetas en una misma celda
        filtered_resources = [
            row for row in rows
            if (not normalized_category or normalized_category in row.get("Category", "").strip().lower()) and
               (not normalized_tag or any(normalized_tag in t.strip().lower().lstrip("#") for t in row.get("Tag", "").split()))
        ]

        logging.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: Fallo al obtener datos: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Server error"}), 500

# ✅ Health Check
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "OK", "timestamp": datetime.now().isoformat()})

# ✅ Iniciar el servidor en Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

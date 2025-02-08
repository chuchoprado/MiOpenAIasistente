from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ✅ Configurar Flask
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ Cargar credenciales de Google Sheets desde variables de entorno
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = "BBDD ElCoach"  # Nombre de tu Google Sheet
SPREADSHEET_ID = "1ooixOlYScf6Wi0_7mT0UBEc9bESC7gnDfnyo0LLEcCE"  # ID de la hoja

if not GOOGLE_SHEETS_CREDENTIALS:
    raise ValueError("❌ ERROR: No se encontraron las credenciales de Google Sheets.")

credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)

# ✅ Conectar con Google Sheets
def get_sheet():
    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1  # Abre la primera hoja
        return sheet
    except Exception as e:
        logger.error(f"❌ ERROR al conectar con Google Sheets: {e}", exc_info=True)
        return None

# ✅ Endpoint para obtener datos desde la API
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    Obtiene datos desde Google Sheets y permite filtrar por:
    - Categoría (Ejemplo: Suplementos)
    - Tag (Ejemplo: #dormir, sin importar si tiene el # o no)
    """
    category = request.args.get("category", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower().lstrip("#")

    logger.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con Google Sheets"}), 500

    try:
        rows = sheet.get_all_records()  # ✅ Obtener todos los datos de la hoja
        logger.info(f"✅ Total de registros obtenidos: {len(rows)}")

        # ✅ Normalizar y filtrar los datos
        filtered_resources = [
            row for row in rows
            if (not category or category in row.get("Category", "").strip().lower()) and
               (not tag or any(tag == t.strip().lower().lstrip("#") for t in row.get("Tag", "").strip().split()))
        ]

        logger.info(f"✅ Recursos filtrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logger.error(f"❌ ERROR al obtener datos: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR en el servidor"}), 500

# ✅ Endpoint de salud (para verificar que el server está activo)
@app.route("/health")
def health_check():
    return jsonify({
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "spreadsheet": SPREADSHEET_NAME
    })

# ✅ Ejecutar Flask en Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

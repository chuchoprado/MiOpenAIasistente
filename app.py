from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Configurar logging para depuración
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Inicializar Flask
app = Flask(__name__)

# ✅ Cargar credenciales de Google Sheets
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD_ElCoach")

if not GOOGLE_SHEETS_CREDENTIALS:
    logger.error("❌ ERROR: No se encontraron credenciales en las variables de entorno.")
    raise ValueError("No se encontraron credenciales de Google Sheets.")

credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

# ✅ Conectar con Google Sheets
def get_sheet():
    try:
        client = gspread.authorize(credentials)
        sheet = client.open(SPREADSHEET_NAME).sheet1  # Hoja principal
        logger.info("✅ Conexión a Google Sheets exitosa.")
        return sheet
    except Exception as e:
        logger.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
        return None

@app.route("/")
def root():
    return jsonify({"status": "API activa", "message": "Bienvenido a la API de Google Sheets"}), 200

@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "spreadsheet_name": SPREADSHEET_NAME
    }), 200

@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """ Obtiene y filtra datos de Google Sheets """
    category = request.args.get("category", "").strip().lower()
    tag = request.args.get("tag", "").strip().lower().lstrip("#")

    logger.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con Google Sheets"}), 500

    try:
        # ✅ Obtener todos los registros
        rows = sheet.get_all_records()
        logger.info(f"✅ Se obtuvieron {len(rows)} filas de la hoja.")

        # ✅ Filtrar por categoría y etiquetas
        filtered_data = [
            row for row in rows
            if (not category or category in row.get("Category", "").strip().lower()) and
               (not tag or any(tag in t.strip().lower().lstrip("#") for t in row.get("Tag", "").split()))
        ]

        logger.info(f"✅ Recursos encontrados: {len(filtered_data)}")

        if not filtered_data:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_data}), 200

    except Exception as e:
        logger.error(f"❌ ERROR: Ocurrió un fallo al obtener los datos: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Fallo en el servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

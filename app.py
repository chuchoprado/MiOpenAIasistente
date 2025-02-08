from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Inicializa Flask
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ✅ Cargar credenciales desde variables de entorno
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD_ElCoach")

if not CREDENTIALS_JSON:
    raise ValueError("❌ ERROR: No se encontraron credenciales en las variables de entorno.")

credentials_dict = json.loads(CREDENTIALS_JSON)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(credentials)
sheet = client.open(SPREADSHEET_NAME).sheet1

# ✅ Endpoint raíz (para verificar si el servicio está activo)
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "✅ Servicio activo", "message": "Bienvenido a la API de ElCoach"}), 200

# ✅ Endpoint para obtener datos desde Google Sheets con filtros
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    Permite buscar recursos en Google Sheets por categoría y etiqueta.
    Si el usuario solo proporciona `tag`, devuelve todos los recursos con esa etiqueta sin importar la categoría.
    Si el usuario solo proporciona `category`, devuelve todos los recursos de esa categoría sin importar la etiqueta.
    Si se usan ambos, se filtran por ambas condiciones.
    """
    category = request.args.get("category")
    tag = request.args.get("tag")

    logging.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    if not sheet:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con Google Sheets"}), 500

    try:
        # ✅ Normalizar inputs
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().strip().lstrip("#") if tag else None

        # ✅ Obtener datos de la hoja de cálculo
        rows = sheet.get_all_records()

        # ✅ Filtrar datos
        filtered_resources = [
            row for row in rows
            if (
                (not normalized_category or row.get("Category", "").strip().lower() == normalized_category) and
                (not normalized_tag or any(t.lower().lstrip("#") == normalized_tag for t in row.get("Tag", "").split()))
            )
        ]

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Error interno del servidor"}), 500

# ✅ Ejecutar en Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials

# 🔥 Configuración del servidor Flask
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ✅ Cargar credenciales de Google Sheets desde variable de entorno
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if CREDENTIALS_JSON:
    credentials_dict = json.loads(CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
else:
    raise ValueError("❌ ERROR: No se encontraron credenciales de Google Sheets.")

# ✅ Conexión con Google Sheets
def get_sheet():
    try:
        client = gspread.authorize(credentials)
        sheet = client.open("BBDD_ElCoach").sheet1  # Asegúrate de que el nombre coincide con la hoja en Google Sheets
        return sheet
    except Exception as e:
        logging.error(f"❌ ERROR al conectar con Google Sheets: {e}")
        return None

# ✅ Endpoint para obtener datos de Google Sheets
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    spreadsheet_id = request.args.get("spreadsheet_id")
    category = request.args.get("category")
    tag = request.args.get("tag")

    logging.debug(f"🔍 Parámetros recibidos - Spreadsheet ID: {spreadsheet_id}, Categoría: {category}, Tag: {tag}")

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con Google Sheets"}), 500

    try:
        rows = sheet.get_all_records()
        logging.info(f"✅ Total de filas obtenidas: {len(rows)}")

        # 🔍 Normalizar entrada (eliminar espacios y convertir a minúsculas)
        category = category.lower().strip() if category else None
        tag = tag.lower().lstrip("#").strip() if tag else None

        # 🔍 Filtrado flexible
        filtered_resources = [
            row for row in rows
            if (
                (not category or category in row.get("Category", "").strip().lower()) and
                (not tag or any(t.lower().lstrip("#") == tag for t in row.get("Tag", "").strip().split()))
            )
        ]

        logging.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: {e}")
        return jsonify({"error": "❌ ERROR: Problema en el servidor"}), 500

# ✅ Iniciar servidor
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

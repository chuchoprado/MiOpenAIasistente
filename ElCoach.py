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

if not CREDENTIALS_JSON:
    logging.error("❌ ERROR: No se encontraron credenciales de Google Sheets en variables de entorno.")
    raise ValueError("No se encontraron credenciales de Google Sheets.")

try:
    credentials_dict = json.loads(CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    client = gspread.authorize(credentials)
    sheet = client.open("BBDD_ElCoach").sheet1
except Exception as e:
    logging.error(f"❌ ERROR al conectar con Google Sheets: {e}")

# ✅ Endpoint para obtener datos de Google Sheets
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    category = request.args.get("category")
    tag = request.args.get("tag")

    logging.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

    try:
        rows = sheet.get_all_records()
        logging.info(f"✅ Total de filas obtenidas: {len(rows)}")

        category = category.lower().strip() if category else None
        tag = tag.lower().lstrip("#").strip() if tag else None

        filtered_resources = [
            row for row in rows
            if (
                (not category or category in row.get("Category", "").strip().lower()) and
                (not tag or any(t.lower().lstrip("#") == tag for t in row.get("Tag", "").strip().split()))
            )
        ]

        logging.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: {e}")
        return jsonify({"error": "❌ ERROR en el servidor"}), 500

# ✅ Iniciar servidor en Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

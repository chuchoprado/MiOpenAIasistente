from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials

# ✅ Inicializa Flask
app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ✅ Carga credenciales de Google Sheets desde variables de entorno
CREDENTIALS_JSON = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

if CREDENTIALS_JSON:
    credentials_dict = json.loads(CREDENTIALS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
else:
    raise ValueError("❌ ERROR: No se encontraron credenciales de Google Sheets en las variables de entorno.")

# ✅ Función para conectar a Google Sheets
def get_sheet():
    try:
        client = gspread.authorize(credentials)
        sheet = client.open("BBDD ElCoach").sheet1  # ✅ Se actualizó el nombre correcto de la hoja
        return sheet
    except Exception as e:
        logging.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
        return None

# ✅ Endpoint mejorado con búsqueda flexible
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    """
    Permite buscar recursos en Google Sheets usando categoría, tag, o ambos.
    La búsqueda es insensible a mayúsculas/minúsculas y al prefijo "#".
    """
    spreadsheet_id = request.args.get("spreadsheet_id")
    category = request.args.get("category")
    tag = request.args.get("tag")

    logging.debug(f"🔍 Parámetros recibidos - Spreadsheet ID: {spreadsheet_id}, Categoría: {category}, Tag: {tag}")

    if not spreadsheet_id:
        return jsonify({"error": "❌ ERROR: Falta el parámetro 'spreadsheet_id'"}), 400

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con la hoja de cálculo"}), 500

    try:
        # ✅ Normalización: eliminar espacios, convertir a minúsculas y eliminar #
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().strip().lstrip("#") if tag else None

        # ✅ Obtiene todos los registros de la hoja
        rows = sheet.get_all_records()
        logging.info(f"✅ Total de filas obtenidas: {len(rows)}")

        # ✅ Filtrado flexible según los parámetros
        filtered_resources = [
            row for row in rows
            if (
                (not normalized_category or row.get("Category", "").strip().lower() == normalized_category) and
                (not normalized_tag or normalized_tag in row.get("Tag", "").strip().lower().replace("#", ""))
            )
        ]

        logging.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: Fallo al obtener datos de la hoja: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Ocurrió un error en el servidor"}), 500

# ✅ Ajuste para el puerto de Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Usa el puerto de Render si está disponible
    app.run(host="0.0.0.0", port=port)

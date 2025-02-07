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
    raise ValueError("❌ ERROR: Missing Google Sheets credentials in environment variables.")

# ✅ Función para conectar a Google Sheets
def get_sheet():
    try:
        client = gspread.authorize(credentials)
        sheet = client.open("BBDD ElCoach").sheet1  # ✅ Verifica que este sea el nombre correcto
        return sheet
    except Exception as e:
        logging.error(f"❌ ERROR: No se pudo conectar con Google Sheets: {e}", exc_info=True)
        return None

# ✅ Endpoint con búsqueda flexible en etiquetas múltiples
@app.route("/api/sheets", methods=["GET"])
def fetch_sheet_data():
    spreadsheet_id = request.args.get("spreadsheet_id")
    category = request.args.get("category")
    tag = request.args.get("tag")

    logging.debug(f"🔍 Parámetros recibidos - Spreadsheet ID: {spreadsheet_id}, Categoría: {category}, Tag: {tag}")

    if not spreadsheet_id:
        return jsonify({"error": "❌ ERROR: Missing required parameters"}), 400

    sheet = get_sheet()
    if sheet is None:
        return jsonify({"error": "❌ ERROR: No se pudo conectar con la hoja de cálculo"}), 500

    try:
        # ✅ Obtiene todos los registros de la hoja
        rows = sheet.get_all_records()
        logging.info(f"✅ Total de filas obtenidas: {len(rows)}")

        # ✅ Obtener todas las categorías y etiquetas disponibles
        all_categories = set()
        all_tags = set()

        for row in rows:
            category_in_db = row.get("Category", "").strip().lower()
            tags_in_db = set(tag.strip().lower().lstrip("#") for tag in row.get("Tag", "").strip().split())

            all_categories.add(category_in_db)
            all_tags.update(tags_in_db)

        logging.info(f"📊 Categorías disponibles en la hoja: {all_categories}")
        logging.info(f"🏷️ Etiquetas disponibles en la hoja: {all_tags}")

        # ✅ Normalización de entrada
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().strip().lstrip("#") if tag else None

        # ✅ Filtrado flexible de datos
        filtered_resources = []
        for row in rows:
            row_category = row.get("Category", "").strip().lower()
            row_tags = set(tag.strip().lower().lstrip("#") for tag in row.get("Tag", "").strip().split())

            # Filtrar por categoría (si aplica)
            category_match = not normalized_category or normalized_category in row_category

            # Filtrar por etiqueta (si aplica) - Detecta si está en la lista de etiquetas
            tag_match = not normalized_tag or normalized_tag in row_tags

            if category_match and tag_match:
                filtered_resources.append(row)

        logging.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            logging.warning(f"⚠️ No se encontraron recursos para categoría '{category}' y tag '{tag}'.")
            return jsonify({"message": "⚠️ No se encontraron recursos que coincidan.", "data": []}), 200

        return jsonify({"data": filtered_resources}), 200

    except Exception as e:
        logging.error(f"❌ ERROR: Fallo al obtener datos: {e}", exc_info=True)
        return jsonify({"error": "❌ ERROR: Server error"}), 500

# ✅ Iniciar el servidor en Render
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

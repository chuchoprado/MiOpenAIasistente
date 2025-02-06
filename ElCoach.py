import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
import os
from unidecode import unidecode  # Normaliza acentos

# Inicializar Flask
app = Flask(__name__)

# Ruta al archivo de credenciales en Render
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

@app.route("/")
def home():
    """Endpoint raíz para comprobar que el servidor Flask está activo."""
    return "✅ El servidor está activo y funcionando correctamente."

def fetch_data(spreadsheet_id, category=None, tag=None):
    """Obtiene datos de Google Sheets según la categoría y etiqueta."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Abrir la hoja de cálculo por ID
        sheet = client.open_by_key(spreadsheet_id).sheet1
        records = sheet.get_all_records()

        # Normalizar entrada y comparación
        category = unidecode(category.lower().strip()) if category else None
        tag = unidecode(tag.lower().strip()) if tag else None

        # Asegurar que la etiqueta tenga #
        if tag and not tag.startswith("#"):
            tag = f"#{tag}"

        filtered_data = []
        for row in records:
            # Normalizar los valores en la hoja
            row_category = unidecode(str(row.get("Category", "")).lower().strip())
            row_tags = unidecode(str(row.get("Tag", "")).lower().strip())

            # Separar etiquetas en lista para comparar
            tag_list = [t.strip() for t in row_tags.split()]

            # Verificar coincidencias
            category_match = category is None or row_category == category
            tag_match = tag is None or tag in tag_list

            if category_match and tag_match:
                # Limpia claves eliminando espacios extra
                clean_row = {key.strip(): value for key, value in row.items()}
                filtered_data.append(clean_row)

        # OpenAI requiere una estructura clara, se devuelve en "results"
        return jsonify({"results": filtered_data}) if filtered_data else jsonify({"message": "No se encontraron resultados"})

    except Exception as e:
        return jsonify({"error": f"Error al recuperar datos: {str(e)}"})

@app.route("/fetch_data", methods=["POST"])
def fetch_data_endpoint():
    """Recibe la solicitud de OpenAI y devuelve los datos filtrados de Google Sheets."""
    data = request.json
    spreadsheet_id = data.get("spreadsheet_id")
    category = data.get("category")  # Convertimos de inglés a español
    tag = data.get("tag")  # Convertimos de inglés a español

    if not spreadsheet_id:
        return jsonify({"error": "spreadsheet_id es requerido"}), 400

    results = fetch_data(spreadsheet_id, category, tag)
    return results

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


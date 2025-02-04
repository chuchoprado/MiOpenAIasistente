import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

CREDENTIALS_FILE = "/etc/secrets/credentials.json"  # Archivo secreto en Render

def fetch_data(spreadsheet_id, category=None, tag=None):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(spreadsheet_id).sheet1
        records = sheet.get_all_records()

        filtered_data = [
            {"nombre": row["Nombre"], "enlace": row["Enlace"]}
            for row in records
            if (category is None or row["Categoría"].lower() == category.lower())
            and (tag is None or tag.lower() in row["Etiqueta"].lower())
        ]

        return {"resultados": filtered_data}

    except Exception as e:
        return {"error": f"Error al recuperar datos: {str(e)}"}
def home():
    """Ruta base para verificar si el servicio está activo."""
    return "✅ El servicio está funcionando correctamente."

@app.route("/fetch_data", methods=["POST"])
def fetch_data_endpoint():
    """Recibe la solicitud de OpenAI y devuelve los datos filtrados de Google Sheets."""
    data = request.json
    spreadsheet_id = data.get("spreadsheet_id")
    category = data.get("category")
    tag = data.get("tag")

    if not spreadsheet_id:
        return jsonify({"error": "spreadsheet_id es requerido"}), 400

    results = fetch_data(spreadsheet_id, category, tag)
    return jsonify(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials

# Inicializar la aplicación Flask
app = Flask(__name__)

# Ubicación del archivo de credenciales en Render (debe estar en los secretos)
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

def fetch_data(spreadsheet_id, category=None, tag=None):
    """Obtiene datos de Google Sheets según la categoría y etiqueta."""
    try:
        # Configurar acceso a Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Abrir la hoja de cálculo
        sheet = client.open_by_key(spreadsheet_id).sheet1
        records = sheet.get_all_records()

        # Filtrar datos por categoría y etiqueta
        filtered_data = [
            {
                "nombre": row.get("Nombre", "Desconocido"),
                "tipo": row.get("Categoría", "Desconocido"),
                "etiqueta": row.get("Etiqueta", "Desconocido"),
                "enlace": row.get("Enlace", "#")
            }
            for row in records
            if (category is None or row.get("Categoría", "").lower() == category.lower()) 
            and (tag is None or tag.lower() in row.get("Etiqueta", "").lower())
        ]

        # Si no hay resultados, devolver un mensaje indicando que no hay datos
        if not filtered_data:
            return {"mensaje": "No se encontraron recursos para la categoría y etiqueta especificadas."}

        return {"resultados": filtered_data}

    except Exception as e:
        return {"error": f"Error al recuperar datos: {str(e)}"}

@app.route("/")
def home():
    """Ruta de prueba para confirmar que el servicio está activo."""
    return jsonify({"message": "ElCoach API está funcionando correctamente"}), 200

@app.route("/fetch_data", methods=["POST"])
def fetch_data_endpoint():
    """Recibe la solicitud de OpenAI y devuelve los datos filtrados de Google Sheets."""
    try:
        data = request.json
        spreadsheet_id = data.get("spreadsheet_id")
        category = data.get("category")
        tag = data.get("tag")

        # Validación: Verificar que se ha proporcionado el ID de la hoja de cálculo
        if not spreadsheet_id:
            return jsonify({"error": "spreadsheet_id es requerido"}), 400

        # Obtener los datos
        results = fetch_data(spreadsheet_id, category, tag)
        return jsonify(results)

    except Exception as e:
        return jsonify({"error": f"Error en la solicitud: {str(e)}"}), 500

if __name__ == "__main__":
    # Ejecutar la aplicación en el puerto 8080
    app.run(host="0.0.0.0", port=8080)

from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional, Dict, List

# ✅ Inicializa Flask
app = Flask(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ✅ Variables de entorno
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD_ElCoach")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1ooixOlYScf6Wi0_7mT0UBEc9bESC7gnDfnyo0LLEcCE")
PORT = int(os.getenv("PORT", 10000))

class SheetManager:
    def __init__(self):
        self.credentials = self._setup_google_credentials()
        self.client = None
        self.sheet = None

    def _setup_google_credentials(self):
        """Cargar credenciales de Google Sheets"""
        if not GOOGLE_SHEETS_CREDENTIALS:
            raise ValueError("❌ ERROR: Falta la variable de entorno GOOGLE_SHEETS_CREDENTIALS.")

        credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

    def connect(self) -> Optional[gspread.Worksheet]:
        """Conectar con Google Sheets"""
        if not self.client:
            self.client = gspread.authorize(self.credentials)
        if not self.sheet:
            self.sheet = self.client.open(SPREADSHEET_NAME).sheet1
        return self.sheet

    def get_data(self) -> List[Dict]:
        """Obtener todos los datos de la hoja"""
        sheet = self.connect()
        return sheet.get_all_records()

    @staticmethod
    def filter_resources(rows: List[Dict], category: Optional[str] = None, tag: Optional[str] = None) -> List[Dict]:
        """Filtrar los datos según la categoría y etiquetas"""
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().strip().lstrip("#") if tag else None

        filtered_data = [
            row for row in rows
            if (
                (not normalized_category or normalized_category in row.get("Category", "").strip().lower()) and
                (not normalized_tag or any(
                    normalized_tag in t.strip().lower().lstrip("#")
                    for t in row.get("Tag", "").split()
                ))
            )
        ]
        return filtered_data

sheet_manager = SheetManager()

@app.route("/")
def root():
    """Ruta de documentación de la API"""
    return jsonify({
        "status": "active",
        "version": "1.0",
        "endpoints": {
            "/": "Documentación",
            "/api/sheets": "Obtiene datos filtrados de Google Sheets. Parámetros: category, tag",
            "/health": "Verifica si la API está funcionando"
        }
    })

@app.route("/health")
def health_check():
    """Revisión del estado de salud de la API"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "spreadsheet_name": SPREADSHEET_NAME
    })

@app.route("/api/sheets")
def fetch_sheet_data():
    """API que recupera y filtra datos de Google Sheets"""
    try:
        category = request.args.get("category")
        tag = request.args.get("tag")

        logger.debug(f"🔍 Parámetros recibidos - Categoría: {category}, Tag: {tag}")

        rows = sheet_manager.get_data()
        logger.info(f"✅ Total de registros obtenidos: {len(rows)}")

        filtered_resources = sheet_manager.filter_resources(rows, category, tag)
        logger.info(f"✅ Recursos encontrados: {len(filtered_resources)}")

        if not filtered_resources:
            return jsonify({
                "message": "⚠️ No se encontraron coincidencias",
                "data": [],
                "filters_applied": {"category": category, "tag": tag}
            }), 200

        return jsonify({"data": filtered_resources, "total_results": len(filtered_resources)}), 200

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return jsonify({"error": f"❌ ERROR: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

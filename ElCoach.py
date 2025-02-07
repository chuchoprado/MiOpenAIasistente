from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from oauth2client.service_account import ServiceAccountCredentials
from functools import wraps
from typing import Optional, Dict, List, Set

# Initialize Flask
app = Flask(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables configuration
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD ElCoach")
# Usar el ID de environment variable o el valor por defecto si no existe
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1ooixOlYScf6Wi0_7mT0UBEc9bESC7gnDfnyo0LLEcCE")
PORT = int(os.getenv("PORT", 10000))

def setup_google_credentials():
    """Initialize and validate Google Sheets credentials"""
    if not GOOGLE_SHEETS_CREDENTIALS:
        raise ValueError("❌ ERROR: Missing Google Sheets credentials in environment variables.")
    
    credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

def error_handler(func):
    """Decorator to handle exceptions and provide consistent error responses"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
            return jsonify({"error": f"❌ ERROR: {str(e)}"}), 500
    return wrapper

class SheetManager:
    def __init__(self):
        self.credentials = setup_google_credentials()
        self.client = None
        self.sheet = None

    def connect(self) -> Optional[gspread.Worksheet]:
        """Establish connection to Google Sheets"""
        if not self.client:
            self.client = gspread.authorize(self.credentials)
        if not self.sheet:
            self.sheet = self.client.open(SPREADSHEET_NAME).sheet1
        return self.sheet

    def get_data(self) -> List[Dict]:
        """Retrieve and process sheet data"""
        sheet = self.connect()
        return sheet.get_all_records()

    @staticmethod
    def extract_metadata(rows: List[Dict]) -> tuple[Set[str], Set[str]]:
        """Extract all categories and tags from the data"""
        categories = {row.get("Category", "").strip().lower() for row in rows}
        tags = {
            tag.strip().lower().lstrip("#")
            for row in rows
            for tag in row.get("Tag", "").strip().split()
        }
        return categories, tags

    @staticmethod
    def filter_resources(
        rows: List[Dict],
        category: Optional[str] = None,
        tag: Optional[str] = None
    ) -> List[Dict]:
        """Filter resources based on category and tag"""
        normalized_category = category.lower().strip() if category else None
        normalized_tag = tag.lower().strip().lstrip("#") if tag else None

        return [
            row for row in rows
            if (not normalized_category or normalized_category in row.get("Category", "").strip().lower()) and
            (not normalized_tag or normalized_tag in {t.strip().lower().lstrip("#") for t in row.get("Tag", "").strip().split()})
        ]

sheet_manager = SheetManager()

@app.route("/api/sheets", methods=["GET"])
@error_handler
def fetch_sheet_data():
    """API endpoint to fetch and filter sheet data"""
    # Validate required parameters
    spreadsheet_id = request.args.get("spreadsheet_id")
    if not spreadsheet_id:
        return jsonify({"error": "❌ ERROR: Missing spreadsheet_id parameter"}), 400

    # Get filter parameters
    category = request.args.get("category")
    tag = request.args.get("tag")
    
    logger.debug(f"🔍 Request parameters - Spreadsheet ID: {spreadsheet_id}, Category: {category}, Tag: {tag}")

    # Fetch and process data
    rows = sheet_manager.get_data()
    logger.info(f"✅ Retrieved {len(rows)} rows from sheet")

    # Extract metadata
    categories, tags = sheet_manager.extract_metadata(rows)
    logger.info(f"📊 Available categories: {categories}")
    logger.info(f"🏷️ Available tags: {tags}")

    # Filter resources
    filtered_resources = sheet_manager.filter_resources(rows, category, tag)
    logger.info(f"✅ Found {len(filtered_resources)} matching resources")

    if not filtered_resources:
        return jsonify({
            "message": "⚠️ No matching resources found",
            "data": []
        }), 200

    return jsonify({"data": filtered_resources}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

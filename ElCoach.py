from flask import Flask, request, jsonify
import gspread
import json
import os
import logging
from datetime import datetime  # Añadida esta importación
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
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "BBDD_ElCoach")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1ooixOlYScf6Wi0_7mT0UBEc9bESC7gnDfnyo0LLEcCE")
PORT = int(os.getenv("PORT", 10000))

class SheetManager:
    def __init__(self):
        self.credentials = self._setup_google_credentials()
        self.client = None
        self.sheet = None

    def _setup_google_credentials(self):
        """Initialize and validate Google Sheets credentials"""
        if not GOOGLE_SHEETS_CREDENTIALS:
            raise ValueError("❌ ERROR: Missing Google Sheets credentials in environment variables.")
        
        credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

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

@app.route("/")
def root():
    """Root endpoint with API information"""
    return jsonify({
        "status": "active",
        "version": "1.0",
        "endpoints": {
            "/": "This documentation",
            "/api/sheets": "Get filtered sheet data. Parameters: category, tag",
            "/health": "Health check endpoint"
        },
        "example_usage": {
            "get_all_data": "/api/sheets",
            "filter_by_category": "/api/sheets?category=ejemplo",
            "filter_by_tag": "/api/sheets?tag=muestra",
            "filter_by_both": "/api/sheets?category=ejemplo&tag=muestra"
        }
    })

@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Google Sheets API",
        "spreadsheet_name": SPREADSHEET_NAME
    })

@app.route("/api/sheets")
def fetch_sheet_data():
    """API endpoint to fetch and filter sheet data"""
    try:
        # Get filter parameters
        category = request.args.get("category")
        tag = request.args.get("tag")
        
        logger.debug(f"🔍 Request parameters - Category: {category}, Tag: {tag}")

        # Fetch and process data
        rows = sheet_manager.get_data()
        logger.info(f"✅ Retrieved {len(rows)} rows from sheet")

        # Filter resources
        filtered_resources = sheet_manager.filter_resources(rows, category, tag)
        logger.info(f"✅ Found {len(filtered_resources)} matching resources")

        if not filtered_resources:
            return jsonify({
                "message": "⚠️ No matching resources found",
                "data": [],
                "filters_applied": {
                    "category": category,
                    "tag": tag
                }
            }), 200

        return jsonify({
            "data": filtered_resources,
            "total_results": len(filtered_resources),
            "filters_applied": {
                "category": category,
                "tag": tag
            }
        }), 200

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return jsonify({
            "error": f"❌ ERROR: {str(e)}",
            "type": type(e).__name__
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Route not found",
        "available_endpoints": {
            "/": "API information",
            "/api/sheets": "Get sheet data",
            "/health": "Health check"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "error": "Internal server error",
        "message": str(error)
    }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

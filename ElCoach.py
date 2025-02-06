import gspread
from flask import Flask, request, jsonify
from oauth2client.service_account import ServiceAccountCredentials
import os
from unidecode import unidecode  # Normalize accents

# Initialize Flask
app = Flask(__name__)

# Path to credentials file in Render
CREDENTIALS_FILE = "/etc/secrets/credentials.json"

@app.route("/")
def home():
    """Root endpoint to check if Flask server is running."""
    return "✅ Server is up and running correctly."

def fetch_data(spreadsheet_id, category=None, tag=None):
    """Fetches data from Google Sheets based on category and tag."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(credentials)

        # Open the spreadsheet by ID
        sheet = client.open_by_key(spreadsheet_id).sheet1
        records = sheet.get_all_records()

        # Normalize input and comparison
        category = unidecode(category.lower().strip()) if category else None
        tag = unidecode(tag.lower().strip()) if tag else None

        # Ensure tag has #
        if tag and not tag.startswith("#"):
            tag = f"#{tag}"

        filtered_data = []
        for row in records:
            # Normalize spreadsheet values
            row_category = unidecode(str(row.get("Category", "")).lower().strip())
            row_tags = unidecode(str(row.get("Tag", "")).lower().strip())

            # Split tags into a list
            tag_list = [t.strip() for t in row_tags.split()]

            # Check for matches
            category_match = category is None or row_category == category
            tag_match = tag is None or tag in tag_list

            if category_match and tag_match:
                # Clean row keys by stripping extra spaces
                clean_row = {key.strip(): value for key, value in row.items()}
                filtered_data.append(clean_row)

        return filtered_data if filtered_data else [{"message": "No results found"}]

    except Exception as e:
        return {"error": f"Error fetching data: {str(e)}"}

@app.route("/fetch_data", methods=["POST"])
def fetch_data_endpoint():
    """Receives request from OpenAI and returns filtered data from Google Sheets."""
    data = request.json
    spreadsheet_id = data.get("spreadsheet_id")
    category = data.get("category")
    tag = data.get("tag")

    if not spreadsheet_id:
        return jsonify({"error": "spreadsheet_id is required"}), 400

    results = fetch_data(spreadsheet_id, category, tag)
    return jsonify(results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

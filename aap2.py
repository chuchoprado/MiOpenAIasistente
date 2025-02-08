@app.route("/api/openai_sheets", methods=["GET"])
def fetch_openai_sheets():
    """
    Middleware especial para adaptar la respuesta de la API a OpenAI Function Calling.
    """
    try:
        # Parámetros desde OpenAI
        category = request.args.get("category")
        tag = request.args.get("tag")

        logger.debug(f"🔍 OpenAI request - Category: {category}, Tag: {tag}")

        # Hacer la solicitud normal a la API de Google Sheets
        response = requests.get(
            f"https://miopenaiasistente.onrender.com/api/sheets?category={category}&tag={tag}"
        )

        if response.status_code != 200:
            return jsonify({"success": False, "message": "Error al obtener datos"}), 500

        data = response.json()

        # Transformar la respuesta a un formato que OpenAI pueda leer mejor
        products = [
            {
                "title": item.get("Title", ""),
                "description": item.get("Description", ""),
                "link": item.get("Link      ", "").strip()  # Se limpia el espacio en la clave
            }
            for item in data.get("data", [])
        ]

        return jsonify({"success": True, "products": products})

    except Exception as e:
        logger.error(f"❌ ERROR: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "Error interno"}), 500

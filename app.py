from flask import Flask, render_template, request, jsonify
import asyncio
import os
from moviebox_api import Session, Search
from moviebox_api.models import SearchResultsItem

app = Flask(__name__)

# Reuse one session for the app
session = Session()
last_search_results = {}  # cache to hold last search results


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing search query"}), 400

    try:
        asyncio.set_event_loop(asyncio.new_event_loop())
        search = Search(session, query)
        data = search.get_content_sync()

        items = []
        for item_data in data.get("items", []):
            # store raw dict in cache (converted later)
            last_search_results[item_data.get("subjectId")] = item_data

            items.append({
                "subjectId": item_data.get("subjectId"),
                "title": item_data.get("title"),
                "genre": item_data.get("genre"),
                "releaseDate": item_data.get("releaseDate"),
                "cover": item_data.get("cover", {}).get("url", "")
            })

        return jsonify({"items": items})

    except Exception as e:
        print("❌ Error in /search:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/download/<subject_id>")
def download(subject_id):
    try:
        item_data = last_search_results.get(subject_id)
        if not item_data:
            return jsonify({"error": "Item not found in recent search results"}), 404

        # ✅ convert dict back to a model instance
        item_model = SearchResultsItem(**item_data)

        os.makedirs("downloads", exist_ok=True)

        # Create Search and get details
        asyncio.set_event_loop(asyncio.new_event_loop())
        search = Search(session, item_model.title)
        details = search.get_item_details(item_model)

        async def perform_download():
            await details.download(save_path="downloads")

        asyncio.run(perform_download())

        return jsonify({
            "status": "success",
            "message": f"{item_model.title} downloaded successfully!"
        })

    except Exception as e:
        print("❌ Download error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)

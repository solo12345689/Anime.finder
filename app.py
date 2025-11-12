from flask import Flask, render_template, request, jsonify
import asyncio
import os
from moviebox_api import Session, Search, MovieAuto
from moviebox_api.models import SearchResultsItem

app = Flask(__name__)

# Reuse one session for the app
session = Session()
last_search_results = {}  # cache to hold last search results

def run_async(coro):
    """Helper function to run async code in Flask routes"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing search query"}), 400

    try:
        search_instance = Search(session, query)
        data = search_instance.get_content_sync()

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

        # Get the title from cached data
        title = item_data.get("title")
        if not title:
            return jsonify({"error": "Item title not found"}), 404

        os.makedirs("downloads", exist_ok=True)

        # Use MovieAuto for simple downloading as shown in the documentation
        async def perform_download():
            auto = MovieAuto(download_dir="downloads")
            # This will download the movie with subtitles
            movie_file, subtitle_file = await auto.run(title)
            return {
                "movie_path": str(movie_file.saved_to) if movie_file else None,
                "subtitle_path": str(subtitle_file.saved_to) if subtitle_file else None
            }

        result = run_async(perform_download())

        return jsonify({
            "status": "success",
            "message": f"{title} downloaded successfully!",
            "paths": result
        })

    except Exception as e:
        print("❌ Download error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, render_template, request, jsonify
import asyncio
import os
import threading
import concurrent.futures
import json
import time
import tempfile
from moviebox_api import Session, Search
from moviebox_api.models import SearchResultsItem

app = Flask(__name__)

# Global variables with lazy initialization
_session = None
_executor = None

# In-memory cache (since file-based caching is having issues)
search_cache = {}

def get_api_session():
    global _session
    if _session is None:
        _session = Session()
    return _session

def get_executor():
    global _executor
    if _executor is None:
        _executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    return _executor

def run_in_event_loop(coro):
    """Run a coroutine in a dedicated asyncio event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def run_async(coro):
    """Run a coroutine using a thread pool to avoid event loop conflicts"""
    executor = get_executor()
    if asyncio.iscoroutine(coro):
        future = executor.submit(run_in_event_loop, coro)
        return future.result()
    else:
        return coro

# Determine appropriate download directory
def get_download_dir():
    # Try to use /tmp directory (available in most platforms)
    if os.path.exists('/tmp'):
        return '/tmp/downloads'
    # Try to use user's home directory
    elif os.path.expanduser('~') != '~':
        return os.path.join(os.path.expanduser('~'), 'downloads')
    # Fallback to current directory
    else:
        return os.path.join(os.getcwd(), 'downloads')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing search query"}), 400

    try:
        print(f"Searching for: {query}")
        # Create Search object
        api_session = get_api_session()
        search_obj = Search(api_session, query)
        
        # Run the async search function
        data = run_async(search_obj.get_content())
        
        print(f"Search returned {len(data.get('items', []))} items")

        items = []
        
        for item_data in data.get("items", []):
            # Store raw dict in cache with subjectId as key
            subject_id = item_data.get("subjectId")
            if subject_id:
                # Convert to string for consistent lookup
                subject_id_str = str(subject_id)
                search_cache[subject_id_str] = item_data
                print(f"Stored item in memory cache: {subject_id_str} -> {item_data.get('title')}")

                items.append({
                    "subjectId": subject_id_str,
                    "title": item_data.get("title"),
                    "genre": item_data.get("genre"),
                    "releaseDate": item_data.get("releaseDate"),
                    "cover": item_data.get("cover", {}).get("url", ""),
                    "type": item_data.get("type", "")  # Add type to distinguish movies from series
                })

        print(f"Memory cache now contains: {list(search_cache.keys())}")
        return jsonify({"items": items})

    except Exception as e:
        print("❌ Error in /search:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/download/<subject_id>")
def download(subject_id):
    try:
        # Make sure subject_id is a string for consistent lookup
        subject_id = str(subject_id)
        print(f"Looking for subject_id: {subject_id}")
        print(f"Available in cache: {list(search_cache.keys())}")
        
        item_data = search_cache.get(subject_id)
        if not item_data:
            error_msg = f"Item not found in recent search results. Looking for: {subject_id}"
            print(error_msg)
            # Debug: Show what we actually have in cache
            if search_cache:
                print(f"Cache contains these IDs: {list(search_cache.keys())}")
            else:
                print("Cache is completely empty")
            return jsonify({"error": error_msg}), 404

        # Convert dict back to a model instance
        item_model = SearchResultsItem(**item_data)
        
        # Get appropriate download directory
        download_dir = get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        
        # Create Search and get details
        api_session = get_api_session()
        search_obj = Search(api_session, item_model.title)
        
        # Get item details
        details = run_async(search_obj.get_item_details(item_model))
        
        # Try to get content using the get_content method
        content_result = details.get_content()
        content = run_async(content_result)
        
        # Check what we got back
        print(f"Content type: {type(content)}")
        if isinstance(content, dict):
            print(f"Content keys: {list(content.keys())}")
        else:
            print(f"Content type is not dict: {type(content)}")
        
        # If content is a dictionary with file/streaming information
        if isinstance(content, dict):
            # Check for common keys that might contain download/streaming info
            stream_url = None
            
            # Common keys for streaming URLs
            for key in ['stream_url', 'download_url', 'url', 'link', 'video_url', 'file', 'sources']:
                if key in content:
                    stream_url = content[key]
                    break
                    
            # Handle nested structures
            if not stream_url and 'data' in content:
                data = content['data']
                if isinstance(data, dict):
                    for key in ['stream_url', 'download_url', 'url', 'link', 'video_url', 'file', 'sources']:
                        if key in data:
                            stream_url = data[key]
                            break
            
            # If we found a streaming URL
            if stream_url:
                return jsonify({
                    "status": "success",
                    "message": "Content retrieved successfully!",
                    "stream_url": stream_url,
                    "title": item_model.title
                })
            else:
                # Return the full content for inspection
                return jsonify({
                    "status": "info",
                    "message": "Content retrieved successfully - review details below",
                    "content": content,
                    "title": item_model.title
                })
        else:
            # If content is not a dict, return it as is
            return jsonify({
                "status": "info",
                "message": f"Content retrieved (type: {type(content)})",
                "content": str(content)[:1000],  # Limit string length
                "title": item_model.title
            })

    except Exception as e:
        print("❌ Download error:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
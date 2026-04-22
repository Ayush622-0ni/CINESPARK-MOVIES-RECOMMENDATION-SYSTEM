import os
import requests
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_omdb_movie(title):
    if not OMDB_API_KEY:
        return None
    # Use requests to fetch data from OMDB API
    url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if data.get("Response") == "True":
            return {
                "title": data.get("Title", ""),
                "poster": data.get("Poster", "") if data.get("Poster") != "N/A" else "",
                "overview": data.get("Plot", "No overview available."),
                "rating": data.get("imdbRating", "N/A"),
                "year": data.get("Year", "")[:4],
                "genre": data.get("Genre", "")
            }
        return None
    except Exception as e:
        print(f"OMDB Error: {e}")
        return None

def get_youtube_trailer(title):
    if not YOUTUBE_API_KEY:
        return None
    
    query = f"{title} official trailer"
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&key={YOUTUBE_API_KEY}&maxResults=1"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["id"]["videoId"]
        return None
    except Exception as e:
        print(f"YouTube Error: {e}")
        return None

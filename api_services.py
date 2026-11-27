import os
import re
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()

OMDB_API_KEY = os.getenv("OMDB_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def fetch_wikipedia_movie(title):
    """
    Fetches real-time movie details, high-res poster, synopsis, and metadata 
    from Wikipedia Open Media API (No API key needed / 100% Free & Unlimited).
    Works for latest Bollywood, Hollywood, and global movies (e.g. Dhurandhar, Stree 2, Fighter).
    """
    clean_title = re.sub(r'[^\w\s-]', '', title).strip()
    headers = {"User-Agent": "CineSparkMovieApp/2.0 (https://cinespark.app; support@cinespark.app)"}
    
    queries = [f"{clean_title} film", clean_title, f"{clean_title} movie"]
    for q in queries:
        try:
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&utf8=&format=json&origin=*"
            s_res = requests.get(search_url, headers=headers, timeout=5).json()
            search_items = s_res.get("query", {}).get("search", [])
            
            if search_items:
                page_title = search_items[0]["title"]
                sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_title)}"
                sum_res = requests.get(sum_url, headers=headers, timeout=5).json()
                
                extract = sum_res.get("extract", "")
                if not extract or len(extract) < 30:
                    continue
                
                poster = ""
                if sum_res.get("thumbnail") and sum_res["thumbnail"].get("source"):
                    poster = sum_res["thumbnail"]["source"]
                    # Request 600px high-resolution version
                    poster = re.sub(r'/\d+px-', '/600px-', poster)
                
                year_match = re.search(r'\b(19\d\d|20\d\d)\b', extract)
                year = year_match.group(1) if year_match else "2025"
                
                # Detect genres from description
                genre_keywords = {
                    "Action": ["action", "spy", "fight", "agent", "chase"],
                    "Thriller": ["thriller", "suspense", "mystery", "terror"],
                    "Sci-Fi": ["science fiction", "sci-fi", "space", "alien", "future"],
                    "Comedy": ["comedy", "humor", "funny", "satire"],
                    "Drama": ["drama", "emotional", "biographical"],
                    "Romance": ["romantic", "romance", "love story"],
                    "Horror": ["horror", "supernatural", "ghost", "haunted"],
                    "Crime": ["crime", "police", "gangster", "mafia", "detective"],
                    "Adventure": ["adventure", "quest", "journey"]
                }
                detected = []
                extract_lower = extract.lower()
                for g, kws in genre_keywords.items():
                    if any(kw in extract_lower for kw in kws):
                        detected.append(g)
                if not detected:
                    detected = ["Action", "Drama"]

                return {
                    "title": sum_res.get("title", title),
                    "poster": poster,
                    "backdrop": poster,
                    "overview": extract[:280] + ("..." if len(extract) > 280 else ""),
                    "full_overview": extract,
                    "rating": 8.0,
                    "vote_count": 1500,
                    "year": year,
                    "genres": detected
                }
        except Exception as e:
            print(f"Wikipedia search error for '{q}': {e}")
            continue

    return None

def get_omdb_movie(title):
    """Fetches movie metadata using OMDb API if key is present, otherwise falls back to Wikipedia."""
    if OMDB_API_KEY:
        url = f"http://www.omdbapi.com/?t={urllib.parse.quote(str(title))}&apikey={OMDB_API_KEY}"
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            if data.get("Response") == "True":
                genres = [g.strip() for g in data.get("Genre", "").split(",") if g.strip()]
                return {
                    "title": data.get("Title", title),
                    "poster": data.get("Poster", "") if data.get("Poster") != "N/A" else "",
                    "backdrop": data.get("Poster", "") if data.get("Poster") != "N/A" else "",
                    "overview": data.get("Plot", "No overview available."),
                    "full_overview": data.get("Plot", "No overview available."),
                    "rating": float(data.get("imdbRating", 0) if data.get("imdbRating") != "N/A" else 8.0),
                    "vote_count": 1000,
                    "year": data.get("Year", "")[:4],
                    "genres": genres if genres else ["Action", "Drama"]
                }
        except Exception as e:
            print(f"OMDB Error: {e}")

    # Fallback to Wikipedia Live Search (bina API key ke har movie ka data nikalega)
    return fetch_wikipedia_movie(title)

def scrape_youtube_trailer(title):
    """Scrapes YouTube search to get official trailer videoId without needing an API key."""
    query = urllib.parse.quote(f"{title} official trailer")
    url = f"https://www.youtube.com/results?search_query={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', res.text)
            if video_ids:
                return video_ids[0]
            watch_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', res.text)
            if watch_ids:
                return watch_ids[0]
    except Exception as e:
        print(f"YouTube Scraper Error: {e}")
    return None

def get_youtube_trailer(title):
    """Fetches YouTube Trailer videoId with API and scraper fallback."""
    if YOUTUBE_API_KEY:
        query = f"{title} official trailer"
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&key={YOUTUBE_API_KEY}&maxResults=1"
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                return data["items"][0]["id"]["videoId"]
        except Exception as e:
            print(f"YouTube API Error: {e}")
    
    # 100% Free Scraper Fallback
    return scrape_youtube_trailer(title)

import pandas as pd
import ast

# Load dataset
movies = pd.read_csv("movies_metadata.csv", low_memory=False)

# Clean data
movies = movies.dropna(subset=["title"])
movies["popularity"] = pd.to_numeric(movies["popularity"], errors="coerce")
movies["vote_average"] = pd.to_numeric(movies["vote_average"], errors="coerce")
movies["vote_count"] = pd.to_numeric(movies["vote_count"], errors="coerce")

# Filter out movies without actual poster paths to ensure highest visual quality
# This ensures "posters of all movies are visible" seamlessly without placeholders
movies = movies.dropna(subset=["poster_path"])
movies = movies[movies["poster_path"] != ""]

def convert_genres(obj):
    try:
        return [i['name'] for i in ast.literal_eval(obj)]
    except:
        return []

movies["genres"] = movies["genres"].apply(convert_genres)

BASE_URL = "https://image.tmdb.org/t/p/w500"
ORIGINAL_BASE = "https://image.tmdb.org/t/p/original"

def get_poster(path):
    if not str(path).startswith('/'):
        path = '/' + str(path)
    return BASE_URL + path

def get_original_poster(path):
    if not str(path).startswith('/'):
        path = '/' + str(path)
    return ORIGINAL_BASE + path

# Helper to format movie
def format_movie(row):
    return {
        "title": str(row.get("title", "")),
        "poster": get_poster(row.get("poster_path")),
        "backdrop": get_original_poster(row.get("poster_path")),
        "overview": str(row.get("overview", "No overview available."))[:250] + "...",
        "rating": round(float(row.get("vote_average", 0) if pd.notna(row.get("vote_average")) else 0), 1),
        "year": str(row.get("release_date", ""))[:4]
    }

# =========================
# GET FEATURED/TRENDING
# =========================
def get_trending_movies(limit=25):
    trending = movies.sort_values(by="popularity", ascending=False).head(limit)
    return [format_movie(row) for _, row in trending.iterrows()]

def get_top_rated_movies(limit=25):
    top_rated = movies[movies['vote_count'] > 2000].sort_values(by="vote_average", ascending=False).head(limit)
    return [format_movie(row) for _, row in top_rated.iterrows()]

def get_action_movies(limit=25):
    action = movies[movies['genres'].apply(lambda x: 'Action' in x)].sort_values(by="popularity", ascending=False).head(limit)
    return [format_movie(row) for _, row in action.iterrows()]

def get_massive_gallery(limit=60):
    # For the energetic UI wall of posters
    gallery = movies.sort_values(by="popularity", ascending=False).iloc[25:25+limit]
    return [format_movie(row) for _, row in gallery.iterrows()]

# =========================
# SEARCH BY MOVIE NAME
# =========================
def recommend_by_movie(movie_name):
    movie_name = movie_name.lower().strip()

    matched = movies[movies["title"].str.lower().str.contains(movie_name, na=False)]
    if matched.empty:
        return []

    selected_movie = matched.iloc[0]
    selected_genres = selected_movie["genres"]

    recommendations = []
    
    for _, row in movies.iterrows():
        if row["title"].lower() != selected_movie["title"].lower():
            if any(g in row["genres"] for g in selected_genres):
                recommendations.append(format_movie(row))
                if len(recommendations) >= 30:
                    break

    return recommendations

# =========================
# SEARCH BY GENRE
# =========================
def recommend_by_genre(genre):
    recommendations = []

    for _, row in movies.iterrows():
        if genre in row["genres"]:
            recommendations.append(format_movie(row))
            if len(recommendations) >= 40:
                break

    return recommendations
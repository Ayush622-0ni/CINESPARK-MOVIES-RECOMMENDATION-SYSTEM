import os
import ast
import re
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib
import api_services

print("[ML ENGINE] Loading dataset and building vector space...")

# 1. Load Dataset
movies = pd.read_csv("movies_metadata.csv", low_memory=False)

# 2. Clean & Preprocess
movies = movies.dropna(subset=["title", "poster_path"])
movies = movies[movies["poster_path"].astype(str).str.startswith("/")]
movies["title"] = movies["title"].astype(str)
movies["overview"] = movies["overview"].fillna("").astype(str)
movies["tagline"] = movies["tagline"].fillna("").astype(str)
movies["vote_average"] = pd.to_numeric(movies["vote_average"], errors="coerce").fillna(0)
movies["vote_count"] = pd.to_numeric(movies["vote_count"], errors="coerce").fillna(0)
movies["popularity"] = pd.to_numeric(movies["popularity"], errors="coerce").fillna(0)

def parse_genres(obj):
    try:
        return [i["name"] for i in ast.literal_eval(obj)]
    except Exception:
        return []

movies["genre_list"] = movies["genres"].apply(parse_genres)
movies["genre_str"] = movies["genre_list"].apply(lambda g: " ".join(g))

# 3. Calculate IMDb Official Weighted Rating (Bayesian Formula)
# WR = (v / (v + m)) * R + (m / (v + m)) * C
C = movies["vote_average"].mean()
m = 200  # Minimum 200 votes threshold
def calculate_weighted_rating(row):
    v = row["vote_count"]
    R = row["vote_average"]
    if v + m == 0:
        return 0
    return (v / (v + m) * R) + (m / (v + m) * C)

movies["weighted_rating"] = movies.apply(calculate_weighted_rating, axis=1)

# 4. Build Content-Based "Soup" & TF-IDF Vector Matrix
movies["content_soup"] = (
    movies["title"] + " " +
    movies["genre_str"] + " " +
    movies["genre_str"] + " " +  # Extra weight to genres
    movies["tagline"] + " " +
    movies["overview"]
)

tfidf = TfidfVectorizer(stop_words="english", max_features=12000, ngram_range=(1, 2))
tfidf_matrix = tfidf.fit_transform(movies["content_soup"])

# Pre-calculate index mapping for fast lookups
title_to_idx = {title.lower().strip(): idx for idx, title in enumerate(movies["title"])}
all_titles_lower = list(title_to_idx.keys())

BASE_URL = "https://image.tmdb.org/t/p/w500"
ORIGINAL_BASE = "https://image.tmdb.org/t/p/original"

def get_poster(path):
    if not path or pd.isna(path):
        return ""
    path_str = str(path).strip()
    if path_str.startswith("http://") or path_str.startswith("https://"):
        return path_str
    if not path_str.startswith("/"):
        path_str = "/" + path_str
    return BASE_URL + path_str

def get_original_poster(path):
    if not path or pd.isna(path):
        return ""
    path_str = str(path).strip()
    if path_str.startswith("http://") or path_str.startswith("https://"):
        return path_str
    if not path_str.startswith("/"):
        path_str = "/" + path_str
    return ORIGINAL_BASE + path_str

def format_movie(row, match_percentage=None):
    release_str = str(row.get("release_date", ""))
    year = release_str[:4] if len(release_str) >= 4 else "N/A"
    
    genres_val = row.get("genre_list", [])
    if isinstance(genres_val, str):
        genres_val = [g.strip() for g in genres_val.split(",") if g.strip()]

    item = {
        "title": str(row.get("title", "")),
        "poster": get_poster(row.get("poster_path")),
        "backdrop": get_original_poster(row.get("poster_path")),
        "overview": str(row.get("overview", "No overview available."))[:280] + ("..." if len(str(row.get("overview", ""))) > 280 else ""),
        "full_overview": str(row.get("overview", "No overview available.")),
        "rating": round(float(row.get("vote_average", 0) if pd.notna(row.get("vote_average")) else 0), 1),
        "vote_count": int(row.get("vote_count", 0)),
        "year": year,
        "genres": genres_val
    }
    if match_percentage is not None:
        item["match_percentage"] = int(match_percentage)
    return item

print(f"[ML ENGINE] Initialized successfully with {len(movies)} movies in TF-IDF vector space.")

# =========================================================================
# ML ENGINE FUNCTIONS
# =========================================================================

def find_best_movie_index(movie_name):
    """Finds exact or closest matching movie index using fuzzy search."""
    clean_name = movie_name.lower().strip()
    if clean_name in title_to_idx:
        return title_to_idx[clean_name]
    
    # Substring search
    sub_matches = movies[movies["title"].str.lower().str.contains(clean_name, na=False, regex=False)]
    if not sub_matches.empty:
        best_match = sub_matches.sort_values(by="popularity", ascending=False).iloc[0]
        return movies.index.get_loc(best_match.name)
    
    # Fuzzy matching
    close_matches = difflib.get_close_matches(clean_name, all_titles_lower, n=1, cutoff=0.55)
    if close_matches:
        return title_to_idx[close_matches[0]]
    
    return None

def recommend_by_movie(movie_name, top_n=24):
    """
    True Content-Based ML Recommendation using TF-IDF + Cosine Similarity.
    Supports movies from local dataset AND any new external movie (e.g. Dhurandhar, Stree 2) 
    via live metadata resolution and on-the-fly vectorization!
    """
    idx = find_best_movie_index(movie_name)
    
    # Case A: Movie exists in dataset
    if idx is not None:
        movie_vector = tfidf_matrix[idx]
        cosine_sims = cosine_similarity(movie_vector, tfidf_matrix).flatten()
        cosine_sims[idx] = -1.0

        candidate_indices = np.argpartition(cosine_sims, -100)[-100:]
        candidate_indices = candidate_indices[np.argsort(cosine_sims[candidate_indices])[::-1]]

        max_sim = cosine_sims[candidate_indices[0]] if len(candidate_indices) > 0 and cosine_sims[candidate_indices[0]] > 0 else 1.0
        
        hybrid_candidates = []
        for c_idx in candidate_indices:
            sim = cosine_sims[c_idx]
            if sim <= 0.04:
                continue
            row = movies.iloc[c_idx]
            sim_norm = sim / max_sim
            rating_norm = min(max(row["weighted_rating"] / 10.0, 0.0), 1.0)
            hybrid_score = (0.75 * sim_norm) + (0.25 * rating_norm)
            match_pct = int(min(99, max(75, round(70 + (sim_norm * 29)))))
            hybrid_candidates.append((hybrid_score, match_pct, row))

        hybrid_candidates.sort(key=lambda x: x[0], reverse=True)

        recommendations = []
        for _, match_pct, row in hybrid_candidates[:top_n]:
            recommendations.append(format_movie(row, match_percentage=match_pct))

        return recommendations

    # Case B: Movie not in dataset (e.g. Dhurandhar, latest releases)
    # Fetch live metadata and vectorize on the fly!
    external_data = api_services.get_omdb_movie(movie_name)
    if external_data:
        # Build vector on the fly from external movie synopsis and genres
        genre_text = " ".join(external_data.get("genres", []))
        ext_soup = f"{external_data['title']} {genre_text} {genre_text} {external_data.get('full_overview', '')}"
        
        try:
            ext_vector = tfidf.transform([ext_soup])
            cosine_sims = cosine_similarity(ext_vector, tfidf_matrix).flatten()
            
            top_indices = np.argpartition(cosine_sims, -80)[-80:]
            top_indices = top_indices[np.argsort(cosine_sims[top_indices])[::-1]]
            
            max_sim = cosine_sims[top_indices[0]] if len(top_indices) > 0 and cosine_sims[top_indices[0]] > 0 else 1.0
            
            recs = []
            for c_idx in top_indices:
                sim = cosine_sims[c_idx]
                if sim <= 0.03:
                    continue
                row = movies.iloc[c_idx]
                sim_norm = sim / max_sim if max_sim > 0 else 0.5
                match_pct = int(min(98, max(75, round(70 + (sim_norm * 28)))))
                recs.append(format_movie(row, match_percentage=match_pct))
                if len(recs) >= top_n:
                    break
            
            # Put the searched movie at position #0
            external_data["match_percentage"] = 100
            return [external_data] + recs
        except Exception as e:
            print("On-the-fly vectorization error:", e)
            return [external_data]

    return []

def recommend_by_genre(genre, top_n=30):
    """Filters by genre and ranks using IMDb Weighted Rating with poster quality check."""
    matched = movies[movies["genre_list"].apply(lambda g_list: any(genre.lower() == g.lower() for g in g_list))]
    if matched.empty:
        return []
    top_picks = matched[matched["vote_count"] >= 50].sort_values(by="weighted_rating", ascending=False).head(top_n)
    if len(top_picks) < 10:
        top_picks = matched.sort_values(by="popularity", ascending=False).head(top_n)
    return [format_movie(row) for _, row in top_picks.iterrows()]

def recommend_by_mood(mood_key, top_n=24):
    """AI Mood-Based Movie Curation."""
    mood_key = mood_key.lower().strip()
    
    mood_genre_map = {
        "mind_bending": (["Science Fiction", "Mystery", "Thriller"], ["dream", "time", "memory", "simulation", "reality", "mind"]),
        "adrenaline": (["Action", "Adventure", "Crime"], ["chase", "mission", "fight", "race", "hero", "explosive"]),
        "feel_good": (["Comedy", "Animation", "Family"], ["friendship", "fun", "love", "humor", "happy", "adventure"]),
        "romance": (["Romance", "Drama"], ["love", "relationship", "heart", "couple", "passion"]),
        "spooky": (["Horror", "Thriller", "Mystery"], ["haunted", "ghost", "dark", "fear", "demon", "killer"]),
        "dark_crime": (["Crime", "Drama", "Mystery"], ["detective", "mafia", "gangster", "murder", "investigation"])
    }

    if mood_key not in mood_genre_map:
        return get_trending_movies(top_n)

    genres, keywords = mood_genre_map[mood_key]
    
    filtered = movies[movies["genre_list"].apply(lambda g_list: any(g in genres for g in g_list))]
    filtered = filtered[filtered["vote_count"] >= 30]
    
    def score_mood(row):
        score = row["weighted_rating"]
        content = (row["overview"] + " " + row["tagline"]).lower()
        keyword_hits = sum(1 for kw in keywords if kw in content)
        return score + (keyword_hits * 0.8) + (row["popularity"] * 0.01)

    scored = filtered.copy()
    scored["mood_score"] = scored.apply(score_mood, axis=1)
    top_mood_movies = scored.sort_values(by="mood_score", ascending=False).head(top_n)
    
    return [format_movie(row) for _, row in top_mood_movies.iterrows()]

def get_user_personalized_recommendations(liked_titles, top_n=24):
    """Builds user taste profile and returns personalized picks."""
    if not liked_titles:
        return get_top_rated_movies(top_n)

    valid_indices = []
    for title in liked_titles:
        idx = find_best_movie_index(title)
        if idx is not None:
            valid_indices.append(idx)

    if not valid_indices:
        return get_top_rated_movies(top_n)

    user_vector = tfidf_matrix[valid_indices].mean(axis=0)
    user_vector = np.asarray(user_vector)

    scores = cosine_similarity(user_vector, tfidf_matrix).flatten()

    for idx in valid_indices:
        scores[idx] = -1.0

    top_indices = np.argpartition(scores, -60)[-60:]
    top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

    results = []
    for idx in top_indices:
        if scores[idx] <= 0.03:
            continue
        row = movies.iloc[idx]
        match_pct = int(min(99, max(80, round(75 + (scores[idx] * 40)))))
        results.append(format_movie(row, match_percentage=match_pct))
        if len(results) >= top_n:
            break

    return results

def search_movies_live(query, limit=8):
    """Instant Autocomplete Search returning top matching movies with details."""
    query = query.lower().strip()
    if not query or len(query) < 2:
        return []

    prefix_matches = movies[movies["title"].str.lower().str.startswith(query, na=False)]
    contains_matches = movies[movies["title"].str.lower().str.contains(query, na=False, regex=False)]
    
    combined = pd.concat([prefix_matches, contains_matches]).drop_duplicates(subset=["title"])
    combined = combined.sort_values(by=["popularity", "weighted_rating"], ascending=[False, False]).head(limit)

    results = [format_movie(row) for _, row in combined.iterrows()]

    # If few or no local matches found, query live resolver so latest movies (Dhurandhar, etc.) appear in autocomplete
    if len(results) < 2:
        live_m = api_services.get_omdb_movie(query)
        if live_m and not any(r["title"].lower() == live_m["title"].lower() for r in results):
            results.insert(0, live_m)

    return results

def get_trending_movies(limit=25):
    """Trending movies filtered for high visual quality."""
    trending = movies[movies["vote_count"] >= 50].sort_values(by="popularity", ascending=False).head(limit)
    return [format_movie(row) for _, row in trending.iterrows()]

def get_top_rated_movies(limit=25):
    """Top rated classics ranked by IMDb Bayesian Weighted Rating."""
    top_rated = movies[movies["vote_count"] >= 300].sort_values(by="weighted_rating", ascending=False).head(limit)
    return [format_movie(row) for _, row in top_rated.iterrows()]

def get_action_movies(limit=25):
    """Action blockbusters filtered for high quality."""
    action = movies[movies["genre_list"].apply(lambda x: "Action" in x) & (movies["vote_count"] >= 80)].sort_values(by="weighted_rating", ascending=False).head(limit)
    return [format_movie(row) for _, row in action.iterrows()]

def get_massive_gallery(limit=60):
    """Massive movie wall with verified popularity."""
    gallery = movies[movies["vote_count"] >= 20].sort_values(by="popularity", ascending=False).iloc[25:25+limit]
    return [format_movie(row) for _, row in gallery.iterrows()]
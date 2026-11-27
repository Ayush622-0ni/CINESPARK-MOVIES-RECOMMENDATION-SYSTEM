import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

# Smart Database Configuration: MySQL (if XAMPP is running) or SQLite (Permanent local database)
mysql_available = False
custom_db_url = os.environ.get('DATABASE_URL')

if custom_db_url:
    if custom_db_url.startswith('postgres://'):
        custom_db_url = custom_db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif custom_db_url.startswith('postgresql://'):
        custom_db_url = custom_db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    db_url = custom_db_url
else:
    try:
        conn = pymysql.connect(host='localhost', user='root', password='', connect_timeout=2)
        conn.cursor().execute('CREATE DATABASE IF NOT EXISTS cinespark')
        conn.close()
        mysql_available = True
    except Exception:
        mysql_available = False

    if mysql_available:
        db_url = 'mysql+pymysql://root:@localhost/cinespark'
        print("[INFO] Connected to XAMPP MySQL database: cinespark")
    else:
        basedir = os.path.abspath(os.path.dirname(__file__))
        sqlite_path = os.path.join(basedir, 'cinespark.db')
        db_url = f'sqlite:///{sqlite_path}'
        print(f"[INFO] Running in SQLite Mode (No XAMPP required). Database: {sqlite_path}")

from recommender import (
    recommend_by_movie,
    recommend_by_genre,
    recommend_by_mood,
    get_user_personalized_recommendations,
    search_movies_live,
    get_trending_movies,
    get_top_rated_movies,
    get_action_movies,
    get_massive_gallery
)
import api_services

app = Flask(__name__, template_folder='templates', static_folder='statics')
app.config['SECRET_KEY'] = 'cinespark_super_secret_key_matrix'
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# =========================================================================
# DATABASE MODELS
# =========================================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    watchlist = db.relationship('Watchlist', backref='user', lazy=True, cascade="all, delete-orphan")
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade="all, delete-orphan")

class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    poster = db.Column(db.String(500), nullable=True)
    backdrop = db.Column(db.String(500), nullable=True)
    overview = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    year = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    poster = db.Column(db.String(500), nullable=True)
    backdrop = db.Column(db.String(500), nullable=True)
    overview = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Float, nullable=True)
    year = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    try:
        db.create_all()
        print("[INFO] Database tables initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Database table initialization FAILED: {e}")
        print("[ERROR] Registration/Login will not work until the database is connected.")

# =========================================================================
# AUTHENTICATION ROUTES
# =========================================================================

@app.route("/", methods=["GET"])
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('discover'))
    return render_template("landing.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('discover'))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for('register'))

        try:
            user = User.query.filter_by(email=email).first()
            uname_check = User.query.filter_by(username=username).first()
        except Exception as e:
            print(f"[ERROR] Database query failed during registration: {e}")
            flash("Registration failed due to a server error. Please try again later.", "error")
            return redirect(url_for('register'))

        if user or uname_check:
            flash("User already exists with this username or email.", "error")
            return redirect(url_for('register'))

        try:
            new_user = User(
                username=username,
                email=email,
                password=generate_password_hash(password, method='pbkdf2:sha256')
            )
            db.session.add(new_user)
            db.session.commit()
            
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Registration failed: {e}")
            flash("Registration failed due to a server error. Please try again later.", "error")
            return redirect(url_for('register'))
    
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('discover'))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        try:
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("discover"))
            else:
                flash("Invalid email or password. Access Denied.", "error")
        except Exception as e:
            print(f"[ERROR] Login failed: {e}")
            flash("Login failed due to a server error. Please try again later.", "error")

    return render_template("auth.html", mode="login")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))

# =========================================================================
# CORE APPLICATION & RECOMMENDATION ROUTES
# =========================================================================

@app.route("/discover", methods=["GET", "POST"])
@login_required
def discover():
    recommendations = []
    movie_name = ""
    genre = ""
    mood = request.args.get("mood", "")
    is_search = False

    trending = get_trending_movies()
    top_rated = get_top_rated_movies()
    action_movies = get_action_movies()
    gallery_movies = get_massive_gallery()
    featured_movie = trending[0] if len(trending) > 0 else None

    # Personalized "Recommended For You" based on User's favorites/watchlist
    user_fav_titles = [f.title for f in Favorite.query.filter_by(user_id=current_user.id).all()]
    user_watch_titles = [w.title for w in Watchlist.query.filter_by(user_id=current_user.id).all()]
    combined_user_taste = list(set(user_fav_titles + user_watch_titles))
    
    personalized_movies = get_user_personalized_recommendations(combined_user_taste, top_n=20)

    # If Mood filter is clicked via URL query param
    if mood:
        is_search = True
        recommendations = recommend_by_mood(mood, top_n=30)

    # Search form submission
    if request.method == "POST":
        movie_name = request.form.get("movie", "").strip()
        genre = request.form.get("genre", "").strip()

        if movie_name or genre:
            is_search = True
            
        if movie_name and not genre:
            recommendations = recommend_by_movie(movie_name, top_n=30)
        elif genre and not movie_name:
            recommendations = recommend_by_genre(genre, top_n=36)
        elif movie_name and genre:
            movie_recs = recommend_by_movie(movie_name, top_n=25)
            genre_recs = recommend_by_genre(genre, top_n=25)
            
            combined = movie_recs + genre_recs
            unique_movies = []
            seen = set()
            for m in combined:
                if m["title"] not in seen:
                    unique_movies.append(m)
                    seen.add(m["title"])
            recommendations = unique_movies

        # If movie not in local dataset, fallback query OMDb API if available
        if movie_name and not recommendations:
            omdb_data = api_services.get_omdb_movie(movie_name)
            if omdb_data:
                recommendations.insert(0, omdb_data)

    return render_template(
        "index.html",
        featured=featured_movie,
        trending=trending,
        top_rated=top_rated,
        action_movies=action_movies,
        gallery_movies=gallery_movies,
        personalized=personalized_movies,
        has_taste_profile=len(combined_user_taste) > 0,
        recommendations=recommendations,
        movie_name=movie_name,
        genre=genre,
        mood=mood,
        is_search=is_search
    )

# =========================================================================
# WATCHLIST & FAVORITES PAGE
# =========================================================================

@app.route("/watchlist", methods=["GET"])
@login_required
def watchlist_page():
    watchlists = Watchlist.query.filter_by(user_id=current_user.id).order_by(Watchlist.created_at.desc()).all()
    favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    return render_template("watchlist.html", watchlists=watchlists, favorites=favorites)

# =========================================================================
# AJAX & API ENDPOINTS
# =========================================================================

@app.route("/api/trailer/<path:movie_title>", methods=["GET"])
@login_required
def get_trailer(movie_title):
    video_id = api_services.get_youtube_trailer(movie_title)
    return jsonify({"videoId": video_id})

@app.route("/api/search-live", methods=["GET"])
@login_required
def live_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    results = search_movies_live(q, limit=8)
    return jsonify(results)

@app.route("/api/user/saved-items", methods=["GET"])
@login_required
def get_saved_items():
    w_titles = [w.title for w in Watchlist.query.filter_by(user_id=current_user.id).all()]
    f_titles = [f.title for f in Favorite.query.filter_by(user_id=current_user.id).all()]
    return jsonify({
        "watchlist": w_titles,
        "favorites": f_titles
    })

@app.route("/api/watchlist/toggle", methods=["POST"])
@login_required
def toggle_watchlist():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    try:
        item = Watchlist.query.filter_by(user_id=current_user.id, title=title).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"status": "removed", "title": title})
        else:
            new_item = Watchlist(
                user_id=current_user.id,
                title=title,
                poster=data.get("poster"),
                backdrop=data.get("backdrop"),
                overview=data.get("overview"),
                rating=float(data.get("rating", 0) or 0),
                year=str(data.get("year", ""))
            )
            db.session.add(new_item)
            db.session.commit()
            return jsonify({"status": "added", "title": title})
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Watchlist toggle failed: {e}")
        return jsonify({"error": "Server error. Please try again."}), 500

@app.route("/api/favorite/toggle", methods=["POST"])
@login_required
def toggle_favorite():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "Title is required"}), 400

    try:
        item = Favorite.query.filter_by(user_id=current_user.id, title=title).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({"status": "removed", "title": title})
        else:
            new_item = Favorite(
                user_id=current_user.id,
                title=title,
                poster=data.get("poster"),
                backdrop=data.get("backdrop"),
                overview=data.get("overview"),
                rating=float(data.get("rating", 0) or 0),
                year=str(data.get("year", ""))
            )
            db.session.add(new_item)
            db.session.commit()
            return jsonify({"status": "added", "title": title})
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR] Favorite toggle failed: {e}")
        return jsonify({"error": "Server error. Please try again."}), 500

if __name__ == "__main__":
    app.run(debug=True)
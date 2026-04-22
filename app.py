import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql

# Auto-create the database if it doesn't exist
try:
    conn = pymysql.connect(host='localhost', user='root', password='')
    conn.cursor().execute('CREATE DATABASE IF NOT EXISTS cinespark')
    conn.close()
except Exception as e:
    print(f"XAMPP MySQL check failed (ensure XAMPP MySQL is active): {e}")

from recommender import (
    recommend_by_movie,
    recommend_by_genre,
    get_trending_movies,
    get_top_rated_movies,
    get_action_movies,
    get_massive_gallery
)
import api_services

app = Flask(__name__, template_folder='templates', static_folder='statics')
app.config['SECRET_KEY'] = 'cinespark_super_secret_key_matrix'
db_url = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:@localhost/cinespark')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print(f"Failed to initialize database tables. Ensure XAMPP is running: {e}")

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
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        uname_check = User.query.filter_by(username=username).first()

        if user or uname_check:
            flash("User already exists. Please log in.", "error")
            return redirect(url_for('register'))

        new_user = User(username=username, email=email, password=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! Initiating login sequences...", "success")
        return redirect(url_for("login"))
    
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('discover'))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("discover"))
        else:
            flash("Invalid credentials. Access Denied.", "error")

    return render_template("auth.html", mode="login")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))
@app.route("/api/trailer/<path:movie_title>", methods=["GET"])
@login_required
def get_trailer(movie_title):
    video_id = api_services.get_youtube_trailer(movie_title)
    return {"videoId": video_id}

@app.route("/discover", methods=["GET", "POST"])
@login_required
def discover():
    recommendations = []
    movie_name = ""
    genre = ""
    is_search = False

    trending = get_trending_movies()
    top_rated = get_top_rated_movies()
    action_movies = get_action_movies()
    gallery_movies = get_massive_gallery()
    featured_movie = trending[0] if len(trending) > 0 else None

    if request.method == "POST":
        movie_name = request.form.get("movie", "")
        genre = request.form.get("genre", "")

        if movie_name or genre:
            is_search = True
            
        if movie_name and not genre:
            recommendations = recommend_by_movie(movie_name)
        elif genre and not movie_name:
            recommendations = recommend_by_genre(genre)
        elif movie_name and genre:
            movie_recs = recommend_by_movie(movie_name)
            genre_recs = recommend_by_genre(genre)
            
            combined = movie_recs + genre_recs
            unique_movies = []
            seen = set()
            for m in combined:
                if m["title"] not in seen:
                    unique_movies.append(m)
                    seen.add(m["title"])
            recommendations = unique_movies

        if movie_name:
            omdb_data = api_services.get_omdb_movie(movie_name)
            if omdb_data:
                if not any(r["title"].lower() == omdb_data["title"].lower() for r in recommendations):
                    recommendations.insert(0, omdb_data)

    return render_template(
        "index.html",
        featured=featured_movie,
        trending=trending,
        top_rated=top_rated,
        action_movies=action_movies,
        gallery_movies=gallery_movies,
        recommendations=recommendations,
        movie_name=movie_name,
        genre=genre,
        is_search=is_search
    )

if __name__ == "__main__":
    app.run(debug=True)
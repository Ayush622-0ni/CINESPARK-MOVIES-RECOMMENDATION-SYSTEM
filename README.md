# Cinespark - Movie Recommendation App

Cinespark is a full-stack Flask web application that provides users with movie recommendations based on their favorite titles and genres. It leverages external APIs to fetch movie details and trailers dynamically, offering a seamless and engaging user experience.

## Features

- **Movie Discovery:** Browse trending, top-rated, action movies, and a massive gallery.
- **Recommendations:** Get personalized movie recommendations based on a specific title or genre.
- **Dynamic Metadata & Trailers:** Integrates with the OMDb API for rich movie metadata and the YouTube API for official trailers.
- **User Authentication:** Secure user registration, login, and session management using Flask-Login.

## Tech Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login
- **Frontend:** HTML, CSS, JavaScript
- **Database:** MySQL (using PyMySQL)
- **External APIs:** OMDb API, YouTube Data API v3

## Local Setup

### 1. Requirements

- Python 3.8+
- XAMPP (for local MySQL database)

### 2. Clone the Repository

```bash
git clone https://github.com/<your-username>/cinespark.git
cd cinespark
```

### 3. Install Dependencies

Create a virtual environment and install the required Python packages:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Environment Variables

Create a `.env` file in the root directory and add your API keys:

```env
OMDB_API_KEY=your_omdb_api_key
YOUTUBE_API_KEY=your_youtube_api_key
DATABASE_URL=mysql+pymysql://root:@localhost/cinespark
```

### 5. Setup Database

Start XAMPP and ensure the MySQL module is running. The application is configured to auto-create the `cinespark` database and required tables upon the first run.

### 6. Run the Application

```bash
python app.py
```

Navigate to `http://127.0.0.1:5000` in your web browser.

## Deployment (Render)

This project is configured to run on [Render](https://render.com/).

1. Push this code to your GitHub account.
2. Create an account on Render and click **New+** -> **Web Service**.
3. Connect your GitHub repository.
4. Set the **Build Command** to: `pip install -r requirements.txt`
5. Set the **Start Command** to: `gunicorn app:app`
6. Note: Render does not provide native MySQL. You can use an externally hosted MySQL database (like Aiven) or update `DATABASE_URL` in the Render Environment Variables to use Render's PostgreSQL database service (requires changing the connection scheme to `postgresql://...`).

## License

This project is open-source and available under the MIT License.

import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from fpdf import FPDF
except ImportError:
    install('fpdf')
    from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'CineSpark Project Documentation', 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        # Ensure text is encoded to latin-1 to avoid fpdf character issues
        body = body.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 6, body)
        self.ln()

pdf = PDF()
pdf.add_page()

# Introduction
intro_text = (
    "CineSpark is a movie recommendation web application built with Python and Flask. "
    "It integrates local dataset-based recommendations with live API data to provide accurate "
    "movie information and official trailers to authenticated users."
)
pdf.chapter_title('1. Project Overview')
pdf.chapter_body(intro_text)

# Technology Stack & Libraries
tech_text = (
    "Backend Framework:\n- Flask: The core web framework.\n"
    "- Flask-SQLAlchemy: Object Relational Mapper for database interaction.\n"
    "- Flask-Login: Manages user authentication sessions.\n"
    "- Werkzeug: Used for secure password hashing.\n\n"
    "Data Science & Machine Learning Libraries:\n"
    "- Pandas: Used to load, clean, and process the 'movies_metadata.csv' dataset.\n"
    "- Scikit-learn: Listed in requirements, likely for advanced ML algorithms.\n"
    "- Numpy: Used alongside pandas for numerical operations.\n\n"
    "Database:\n- MySQL (via PyMySQL): The relational database backend using XAMPP."
)
pdf.chapter_title('2. Technology Stack & Libraries')
pdf.chapter_body(tech_text)

# APIs Integrated
api_text = (
    "1. OMDb API: Fetches comprehensive movie metadata, including up-to-date plots, genres, and IMDb ratings.\n"
    "2. YouTube Data API v3: Dynamically queries and retrieves official movie trailer video IDs for playback.\n"
    "3. TMDB Image Repository: Utilized to load high-quality posters and backdrops using 'image.tmdb.org' URLs."
)
pdf.chapter_title('3. API Integrations')
pdf.chapter_body(api_text)

# Methodology
method_text = (
    "1. Data Ingestion & Preprocessing:\n"
    "   - Reads 'movies_metadata.csv' using Pandas.\n"
    "   - Drops incomplete entries (e.g., missing titles or poster paths).\n"
    "   - Uses AST evaluation safely to extract genre tags into lists.\n\n"
    "2. Content-Based Recommendation System:\n"
    "   - Recommend By Movie: Matches the input movie, extracting its genres to find related films.\n"
    "   - Recommend By Genre: Searches dataset for films containing the desired genre.\n"
    "   - Categorization logic to output 'Trending', 'Top Rated', 'Action', and a 'Massive Gallery' based on popularity or ratings.\n\n"
    "3. Web App Workflow:\n"
    "   - Users land on the index, register/login, and proceed to the discovery engine.\n"
    "   - Live API fallback: If a user searches an exact movie, the backend fetches fresh OMDB data to insert securely into the UI.\n"
    "   - YouTube Trailer Integration: Allows playing trailers dynamically when requested."
)
pdf.chapter_title('4. Structural Methodology')
pdf.chapter_body(method_text)

pdf.output("e:/as/Project_Documentation.pdf")
print("PDF created successfully at e:/as/Project_Documentation.pdf")

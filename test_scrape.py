from urllib.request import Request, urlopen
import re

def scrape_poster(tmdb_id):
    try:
        req = Request(f'https://www.themoviedb.org/movie/{tmdb_id}', headers={'User-Agent': 'Mozilla/5.0'})
        html = urlopen(req).read().decode('utf-8')
        m = re.search(r'<meta property="og:image" content="(.*?)"', html)
        if m:
            return m.group(1)
    except Exception as e:
        print("Error:", e)
    return None

print(scrape_poster(211672))

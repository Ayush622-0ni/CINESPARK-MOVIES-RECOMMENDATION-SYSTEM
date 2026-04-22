import requests
import re

def get_tmdb_poster(tmdb_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    res = requests.get(f'https://www.themoviedb.org/movie/{tmdb_id}', headers=headers)
    print(res.status_code)
    m = re.search(r'<meta property="og:image" content="(.*?)"', res.text)
    if m:
        return m.group(1)
    return None

print(get_tmdb_poster(211672))

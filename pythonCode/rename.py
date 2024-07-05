import re
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
import requests
from typing import List


app = FastAPI()

TMDB_API_KEY = '21fcb321815a4fd12fe0ed3029612929'  # Replace with your TMDB API key
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TVMAZE_BASE_URL = 'https://api.tvmaze.com'


#///////////RENAME MOVIE\\\\\\\\\\\\\\\\\\\\\

@app.post("/rename_movie/")
async def rename_movie(query: str = Form(...)):
    try:
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'en-US',
            'page': 1,
            'include_adult': False
        }
        response = requests.get(search_url, params=params)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses

        search_results = response.json()
        if search_results['total_results'] == 0:
            return {"message": "No movies found for the given query."}

        # Create a list of movie names formatted as [keyword + release_year]
        movie_names = [f"{result['title']} {result['release_date'][:4]}" for result in search_results['results']]

        return {"movie_name": movie_names}
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    

#///////////RENAME EPISODE\\\\\\\\\\\\\\\\\\\\\

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_KEY = '21fcb321815a4fd12fe0ed3029612929'

# Define the input model for episodes list
class EpisodesList(BaseModel):
    episodes: List[str]

# Function to extract details from the filename
def parse_filename(filename: str):
    pattern = re.compile(r'(.+?)\s*(?:season|s|Season|S)\s*(\d+)\s*(?:episode|ep|e|Episode|Ep|E)\s*(\d+)', re.IGNORECASE)
    match = pattern.match(filename)
    if match:
        title, season, episode = match.groups()
        return title.strip(), int(season), int(episode)
    else:
        raise HTTPException(status_code=400, detail="Filename format not recognized. Expected format: 'title Season 1 Episode 2'.")

# Function to search for TV series using TMDb API
def search_tv_series(query):
    search_url = f"{TMDB_BASE_URL}/search/tv"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "en-US",
        "page": 1
    }
    response = requests.get(search_url, params=params)
    response.raise_for_status()
    return response.json()["results"]

# Function to get episode details using TMDb API
def get_episode_details(series_id, season_number, episode_number):
    episode_url = f"{TMDB_BASE_URL}/tv/{series_id}/season/{season_number}/episode/{episode_number}"
    params = {"api_key": TMDB_API_KEY}
    response = requests.get(episode_url, params=params)
    response.raise_for_status()
    return response.json()

# Function to rename a single episode using TMDb API
def rename_single_episode(title, season, episode_number):
    try:
        # Step 1: Search for the show to get the show_id
        series_list = search_tv_series(title)
        if not series_list:
            return "No shows found for the given query."

        show_id = series_list[0]['id']

        # Step 2: Fetch episode details using show_id, season, and episode number
        episode_data = get_episode_details(show_id, season, episode_number)
        
        # Format the response
        formatted_response = f"{title.replace(' ', '-')}-season-{season}-ep-{episode_number}-{episode_data['name'].replace(' ', '-')}-{episode_data['air_date'][:4]}"

        return formatted_response
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return "not found"
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        return "not found"

@app.post("/rename_episodes/")
async def rename_episodes(episodes_list: EpisodesList):
    renamed_episodes = []
    for episode in episodes_list.episodes:
        try:
            title, season, episode_number = parse_filename(episode)
            renamed_episode = rename_single_episode(title, season, episode_number)
        except HTTPException as e:
            renamed_episode = "not found"
        renamed_episodes.append(renamed_episode)
    
    return {"renamed_episodes": renamed_episodes}
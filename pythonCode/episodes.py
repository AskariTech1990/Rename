import asyncio
from fastapi import FastAPI, HTTPException, Form
import requests
import httpx
from fastapi.responses import JSONResponse
from typing import Optional



#//////////////ANIME EPISODES\\\\\\\\\\\\\\\\\\\

app = FastAPI()

JIKAN_BASE_URL = "https://api.jikan.moe/v4"
async def fetch_with_retry(url, params, retries=3):
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Too Many Requests
                # Exponential backoff: wait for 2^attempt seconds before retrying
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            else:
                raise
    # If all retries fail, raise the last exception
    raise e


@app.post("/multi_anime_search_jikan/")
async def search_anime(query: str = Form(...)):
    try:
        search_url = f"{JIKAN_BASE_URL}/anime"
        params = {'q': query, 'sfw': True}
        response = await fetch_with_retry(search_url, params)

        search_results = response.json()

        if not search_results['data']:
            return JSONResponse(content={"message": "No anime found for the given query."}, status_code=404)

        anime_list = []
        for result in search_results['data'][:5]:  # Limiting to top 5 results
            anime_id = result['mal_id']
            details_url = f"{JIKAN_BASE_URL}/anime/{anime_id}/moreinfo"
            details_response = await fetch_with_retry(details_url, {})
            details_data = details_response.json()

            # Extracting season information if available
            if 'airing_start' in details_data:
                airing_start = details_data['airing_start']
                airing_end = details_data.get('airing_end', "Ongoing")
                number_of_seasons = f"Season {details_data['season']} ({airing_start} to {airing_end})"
            else:
                number_of_seasons = "Not specified"

            anime_details = {
                'name': result['title'],
                'id': anime_id,
                'poster': result['images']['jpg']['image_url'],
                'seasons': number_of_seasons
            }
            anime_list.append(anime_details)

        return JSONResponse(content={"results": anime_list})
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/episodes_list_Jikan/")
async def search_episodes(show_id: int = Form(...), option: str = Form(...), season_number: int = Form(None)):
    # Validate option
    if option not in ["by_date", "by_season"]:
        raise HTTPException(status_code=400, detail="Invalid option. Choose 'by_date' or 'by_season'.")

    try:
        async with httpx.AsyncClient() as client:
            # Get the anime details to fetch its name
            anime_url = f"{JIKAN_BASE_URL}/anime/{show_id}"
            anime_response = await client.get(anime_url)
            anime_response.raise_for_status()
            anime_data = anime_response.json()

            # Extract anime name
            anime_name = anime_data.get('data', {}).get('title')

            if anime_name is None:
                raise HTTPException(status_code=500, detail="Anime name not found in the response.")

            # Get the list of episodes for the anime
            episodes_url = f"{JIKAN_BASE_URL}/anime/{show_id}/episodes"
            episodes_response = await client.get(episodes_url)
            episodes_response.raise_for_status()

            episodes = episodes_response.json()['data']

            # Filter episodes by the specified season if provided
            if season_number is not None:
                season_episodes = [ep for ep in episodes if ep.get('season') == season_number]
            else:
                season_episodes = episodes

            # Check if there are episodes after filtering
            if not season_episodes:
                return JSONResponse(content={"message": "No episodes found for the given criteria."}, status_code=404)

            # Extract episode titles in the desired format
            formatted_episodes = []
            for ep in season_episodes:
                aired_date = ep['aired'].split('T')[0]  # Extracting only the date part
                if option == "by_date":
                    formatted_episodes.append(f"{anime_name} - {aired_date} - {ep['title']}")
                else:  # option == "by_season"
                    formatted_episodes.append(f"{anime_name} - S{ep.get('season', '1')}x{ep['mal_id']} - {ep['title']}")

            return JSONResponse(content={"episodes": formatted_episodes})
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))

    


#/////////////////EPISODES_TMDB\\\\\\\\\\\\\\\\\\\

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_KEY = '21fcb321815a4fd12fe0ed3029612929'

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


def get_series_details(series_id):
    series_url = f"{TMDB_BASE_URL}/tv/{series_id}"
    params = {"api_key": TMDB_API_KEY}
    response = requests.get(series_url, params=params)
    response.raise_for_status()
    series_data = response.json()
    return {
        "id": series_data["id"],
        "poster": f"https://image.tmdb.org/t/p/original{series_data['poster_path']}",
        "name": series_data["name"],
        "num_seasons": series_data["number_of_seasons"]
    }

# Endpoint to search for anime or TV series and fetch their details
@app.post("/search_tv_series/")
async def search_tv_series_endpoint(query: str = Form(...)):
    try:
        series_list = search_tv_series(query)
        if not series_list:
            raise HTTPException(status_code=404, detail="No TV series found for the given query.")
        
        # Retrieve details for all results
        results = []
        for series in series_list:
            series_id = series["id"]
            series_details = get_series_details(series_id)
            results.append({
                "id": series_details["id"],
                "name": series_details["name"],
                "poster": series_details["poster"],
                "num_seasons": series_details["num_seasons"]
            })
        
        return results
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/episodes_list_TMDB/")
async def search_episodes(show_id: int = Form(...), season_number: int = Form(None), option: str = Form(...)):
    # Validate option
    if option not in ["by_date", "by_season"]:
        raise HTTPException(status_code=400, detail="Invalid option. Choose 'by_date' or 'by_season'.")

    try:
        async with httpx.AsyncClient() as client:
            show_url = f"{TMDB_BASE_URL}/tv/{show_id}"
            show_params = {
                'api_key': TMDB_API_KEY,
                'language': 'en-US'
            }
            show_response = await client.get(show_url, params=show_params)
            show_response.raise_for_status()
            show_details = show_response.json()
            show_title = show_details['name']

            regular_episodes = []
            special_episodes = []

            for season in show_details['seasons']:
                season_url = f"{TMDB_BASE_URL}/tv/{show_id}/season/{season['season_number']}"
                season_response = await client.get(season_url, params=show_params)
                season_response.raise_for_status()

                season_data = season_response.json()
                for episode in season_data['episodes']:
                    if episode['air_date']:  # Ensure there's an air date
                        episode_date = episode['air_date'].replace('-', '')
                        formatted_episode_by_date = f"{show_title} - {episode_date} - {episode['name']}"
                        formatted_episode_by_season = f"{show_title} - S{season['season_number']}x{episode['episode_number']:02d} - {episode['name']}"
                        episode_tuple = (episode_date, formatted_episode_by_date, formatted_episode_by_season, season['season_number'])
                        if season['season_number'] == 0:
                            special_episodes.append(episode_tuple)
                        else:
                            regular_episodes.append(episode_tuple)

            # Decide format based on option
            if option == "by_date":
                all_episodes = sorted(regular_episodes + special_episodes, key=lambda x: x[0])
                formatted_episodes = [ep[1] for ep in all_episodes]  # by_date format
            else:
                combined_episodes = regular_episodes + special_episodes
                combined_episodes_sorted = sorted(combined_episodes, key=lambda x: (x[3], x[0]))  # Sort by season, then by date
                formatted_episodes = [ep[2] for ep in combined_episodes_sorted]  # by_season format

            # Filter episodes by season number if provided
            if season_number is not None:
                if season_number == 0:
                    filtered_episodes = [ep[1] if option == "by_date" else ep[2] for ep in special_episodes]
                else:
                    filtered_episodes = [ep[1] if option == "by_date" else ep[2] for ep in regular_episodes if ep[3] == season_number]
                return JSONResponse(content={"episodes": filtered_episodes})

            else:
                return JSONResponse(content={"episodes": formatted_episodes})

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))




#///////////EPISODES_LIST_TVMAZE\\\\\\\\\\\\\\\\\\\\\
    

TVMAZE_BASE_URL = 'https://api.tvmaze.com'

@app.post("/tv_series_details_TVMAZE/")
async def tv_series_details_by_name(query: str = Form(...)):
    try:
        # Search for the TV show
        search_url = f"{TVMAZE_BASE_URL}/search/shows"
        params = {'q': query}
        async with httpx.AsyncClient() as client:
            response = await client.get(search_url, params=params)
            response.raise_for_status()

            search_results = response.json()
            if not search_results:
                return JSONResponse(content={"message": "No TV show found for the given query."}, status_code=404)

            # Extract details for each search result
            results = []
            for result in search_results:
                show = result['show']
                show_id = show['id']
                num_seasons = show.get('seasons', "Information not available")  # Providing a default value
                poster = show['image']['original'] if show['image'] else None
                title = show['name']
                results.append({"id": show_id, "name": title, "poster": poster, "num_seasons": num_seasons})

            return JSONResponse(content=results)
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tv_series_episodes_list_TVMAZE/")
async def search_episodes(show_id: int = Form(...), season_number: Optional[int] = Form(None), option: str = Form(...)):
    # Validate option
    if option not in ["by_date", "by_season"]:
        raise HTTPException(status_code=400, detail="Invalid option. Choose 'by_date' or 'by_season'.")

    try:
        async with httpx.AsyncClient() as client:
            # Get details of the TV show
            show_url = f"{TVMAZE_BASE_URL}/shows/{show_id}"
            show_response = await client.get(show_url)
            show_response.raise_for_status()

            show_details = show_response.json()
            series_name = show_details.get("name", "Unknown Series")

            # Get all episodes for the show
            episodes_url = f"{TVMAZE_BASE_URL}/shows/{show_id}/episodes"
            episodes_response = await client.get(episodes_url)
            episodes_response.raise_for_status()

            episodes = episodes_response.json()

            # Filter episodes by the specified season if season_number is provided
            if season_number is not None:
                season_episodes = [ep for ep in episodes if ep['season'] == season_number]
            else:
                season_episodes = episodes

            # Extract episode titles in the desired format
            formatted_episodes = []
            for ep in season_episodes:
                if option == "by_date":
                    formatted_episodes.append(f"{series_name} - {ep['airdate']} - {ep['name']}")
                else:  # option == "by_season"
                    formatted_episodes.append(f"{series_name} - S{ep['season']}x{ep['number']} - {ep['name']}")

            return JSONResponse(content={"episodes": formatted_episodes})
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))
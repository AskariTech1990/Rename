from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
import requests
import httpx
from typing import Optional, List

app = FastAPI()


#//////////////BOOK SEARCH \\\\\\\\\\\\\\\
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

@app.post("/search_books/")
async def get_book_details(query: str = Form(...)):
    params = {
        "q": query,
        "maxResults": 1  # Limiting to 1 result for simplicity
    }
    response = requests.get(GOOGLE_BOOKS_API_URL, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            book_info = data["items"][0]["volumeInfo"]
            title = book_info.get("title", "N/A")
            author = book_info.get("authors", ["N/A"])[0]
            first_publish_year = book_info.get("publishedDate", "N/A").split("-")[0]
            poster_image = book_info.get("imageLinks", {}).get("thumbnail", "N/A")
            description = book_info.get("description", "N/A")
            genre = book_info.get("categories", ["N/A"])[0]
            rating = book_info.get("averageRating", "N/A")
            
            return {
                "title": title,
                "author": author,
                "first_publish_year": first_publish_year,
                "poster_image": poster_image,
                "description": description,
                "genre": genre,
                "rating": rating
            }
        else:
            raise HTTPException(status_code=404, detail="Book not found")
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch book details from Google Books API")
    

#/////////////////MOVIE DETAILS\\\\\\\\\\\\\\\\\\\
        
TMDB_API_KEY = '21fcb321815a4fd12fe0ed3029612929'  # Replace with your TMDB API key
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
        
class MovieDetails(BaseModel):
    title: str
    release_date: str
    overview: str
    vote_average: float
    genres: List[str]
    poster_image: Optional[str] = None



@app.post("/search_movie/", response_model=MovieDetails)
async def search_movie(query: str = Form(...)):
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

        # Take the first result
        movie_id = search_results['results'][0]['id']

        # Get movie details
        details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        details_params = {
            'api_key': TMDB_API_KEY,
            'language': 'en-US'
        }
        details_response = requests.get(details_url, params=details_params)
        details_response.raise_for_status()

        movie_details = details_response.json()
        genres = [genre['name'] for genre in movie_details['genres']]
        poster_image = f"https://image.tmdb.org/t/p/original{movie_details['poster_path']}" if movie_details.get('poster_path') else None

        return MovieDetails(
            title=movie_details['title'],
            release_date=movie_details['release_date'],
            overview=movie_details['overview'],
            vote_average=movie_details['vote_average'],
            genres=genres,
            poster_image=poster_image
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    


#//////////////SEARCH SHOWS\\\\\\\\\\\\\\\\\

TVMAZE_BASE_URL = 'https://api.tvmaze.com'

class ShowDetails(BaseModel):
    name: str
    premiered: str
    summary: str
    rating: float
    genres: list[str]
    poster_image: str

def clean_html(raw_html):
    clean_text = raw_html.replace("<p>", "").replace("</p>", " ").replace("<b>", "").replace("</b>", " ")
    clean_text = clean_text.replace("\n", " ")  # Replace newlines with spaces
    return clean_text

@app.post("/search_show/", response_model=ShowDetails)
async def search_show(query: str = Form(...)):
    try:
        search_url = f"{TVMAZE_BASE_URL}/search/shows"
        params = {
            'q': query
        }
        response = requests.get(search_url, params=params)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses

        search_results = response.json()
        if not search_results:
            return {"message": "No shows found for the given query."}

        # Take the first result
        show_info = search_results[0]['show']

        # Extract relevant details
        genres = show_info.get('genres', [])
        rating = show_info['rating']['average'] if show_info['rating']['average'] is not None else None
        poster_image = show_info['image']['original'] if show_info['image'] and 'original' in show_info['image'] else None

        # Remove HTML tags from summary
        summary_html = show_info['summary']
        summary = clean_html(summary_html)

        return ShowDetails(
            name=show_info['name'],
            premiered=show_info['premiered'],
            summary=summary,
            rating=rating,
            genres=genres,
            poster_image=poster_image
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    


#//////////////SEARCH ANIME\\\\\\\\\\\\\\\\\\
    
JIKAN_BASE_URL = "https://api.jikan.moe/v4"

@app.post("/search-anime/")
async def search_anime(query: str = Form(...)):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{JIKAN_BASE_URL}/anime", params={"q": query})
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error fetching data from Jikan API")

        data = response.json()

        if not data.get("data"):
            raise HTTPException(status_code=404, detail="Anime not found")

        # Get the top anime result
        anime = data["data"][0]
        details_data = anime
        genres = details_data.get("genres", [])
        anime_id = details_data.get("mal_id", "Unknown")
        synopsis = details_data.get("synopsis", "No synopsis available.").replace("\n", " ")

        start_date = details_data.get("aired", {}).get("from", "Unknown")
        end_date = details_data.get("aired", {}).get("to", "Unknown")

        # Remove time portion if date is available
        if start_date and start_date != "Unknown":
            start_date = start_date.split("T")[0]
        if end_date and end_date != "Unknown":
            end_date = end_date.split("T")[0]
        
        anime_detail = {
            "id": anime_id,
            "title": details_data.get("title", "Unknown"),
            "synopsis": synopsis,
            "startDate": start_date,
            "endDate": end_date,
            "posterImage": details_data.get("images", {}).get("jpg", {}).get("image_url", ""),
            "totalEpisodes": details_data.get("episodes", "Unknown"),
            "genres": [genre["name"] for genre in genres],  # Include genres in the response
            "rating": details_data.get("score", "No rating")
        }

        return anime_detail
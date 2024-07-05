from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import JSONResponse, FileResponse
from opensubtitlescom import OpenSubtitles
import json
import os

app = FastAPI()

API_KEY = "IC4pI4SjwaJjK85T0FKIMWwZ66fwW2cq"
USERNAME = "askari"
PASSWORD = "askaritech"
APP_NAME = "askari"
APP_VERSION = "1.0.0"

# Initialize the OpenSubtitles client
subtitles = OpenSubtitles(f"{APP_NAME} v{APP_VERSION}", API_KEY)

# Log in (retrieve auth token)
subtitles.login(USERNAME, PASSWORD)

@app.post("/search_subtitles/")
async def search_subtitles(
    query: str = Form(...),
    season_number: int = Form(None),
    episode_number: int = Form(None),
    language: str = Form("en")
):
    try:
        # Search for subtitles
        response = subtitles.search(query=query, season_number=season_number, episode_number=episode_number, languages=language)

        subtitles_info = []

        for subtitle in response.data:
            subtitle_info = {
                'file_id': subtitle.file_id,
                'file_name': subtitle.file_name,
                'language': subtitle.language  # Ensure the attribute names match exactly
            }
            subtitles_info.append(subtitle_info)

        # Convert the list of dictionaries to a JSON format
        subtitles_info_json = json.dumps(subtitles_info)
        
        # Return the JSON response
        return JSONResponse(content=subtitles_info_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/download_subtitles/")
async def download_subtitles(file_id: int = Form(...)):
    try:
        # Print the current working directory
        print("Current working directory:", os.getcwd())

        # Ensure the 'temp_subtitles' directory exists
        temp_subtitles_dir = 'temp_subtitles'
        os.makedirs(temp_subtitles_dir, exist_ok=True)
        
        # Print a confirmation that the directory has been created or exists
        print(f"Directory '{temp_subtitles_dir}' created or already exists.")

        # Download the subtitle using the file_id and save it to 'temp_subtitles' directory
        local_srt_file = subtitles.download_and_save(file_id)

        # Print the path of the downloaded file
        print("Downloaded file path:", local_srt_file)

        # Return the subtitle file
        return FileResponse(path=local_srt_file, filename=os.path.basename(local_srt_file))
    except Exception as e:
        # Print the exception message
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
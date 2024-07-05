# import os
# from fastapi import FastAPI, File, UploadFile, HTTPException
# from pymediainfo import MediaInfo
# import io
# import tempfile

# app = FastAPI()

# @app.post("/mediainfo/")
# async def get_media_info(file: UploadFile = File(...)):
#     try:
#         # Read the file content into memory
#         content = await file.read()

#         # Use a temporary file-like object to store the content
#         with tempfile.NamedTemporaryFile(delete=False) as temp_file:
#             temp_file.write(content)
#             temp_file_path = temp_file.name

#         # Analyze the media file using pymediainfo
#         media_info = MediaInfo.parse(temp_file_path)
#         audio_tracks = []
#         video_tracks = []

#         for track in media_info.tracks:
#             if track.track_type == "Audio":
#                 audio_info = {
#                     "language": track.language,
#                     "channels": track.channel_s,
#                     "format": track.format
#                 }
#                 audio_tracks.append(audio_info)
#             elif track.track_type == "Video":
#                 video_info = {
#                     "width": track.width,
#                     "height": track.height,
#                     "resolution": f"{track.width}x{track.height}",
#                     "format": track.format
#                 }
#                 video_tracks.append(video_info)

#         # Clean up the temporary file
#         os.remove(temp_file_path)

#         # Prepare response data
#         response_data = {
#             "audio_tracks": audio_tracks,
#             "video_tracks": video_tracks
#         }

#         return response_data

#     except Exception as e:
#         print(f"Error: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

from fastapi import FastAPI, File, UploadFile, HTTPException
from pymediainfo import MediaInfo
import tempfile
import os

app = FastAPI()

@app.post("/mediainfo/")
async def get_media_info(file: UploadFile = File(...)):
    try:
        # Get the name of the uploaded file
        file_name = file.filename

        # Read the file content into memory
        content = await file.read()

        # Use a temporary file-like object to store the content
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Analyze the media file using pymediainfo
        media_info = MediaInfo.parse(temp_file_path)
        audio_tracks = []
        video_tracks = []

        for track in media_info.tracks:
            if track.track_type == "Audio":
                audio_info = f"{track.channel_s} {track.format} {track.language or 'Unknown'}"
                audio_tracks.append(audio_info)
            elif track.track_type == "Video":
                video_info = {
                    "width": track.width,
                    "height": track.height,
                    "resolution": f"{track.width}x{track.height}",
                    "format": track.format
                }
                video_tracks.append(video_info)

        # Clean up the temporary file
        os.remove(temp_file_path)

        # Format the response string
        if video_tracks:
            resolution = f"[{video_tracks[0]['height']}p]"
        else:
            resolution = ""

        if audio_tracks:
            audio_info = ", ".join(audio_tracks)
            audio_string = f"[{audio_info}]"
        else:
            audio_string = ""

        response_string = f"{file_name} {resolution} {audio_string}"

        return {"detail": response_string}

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from moviepy.editor import ImageClip, AudioFileClip
import os
from urllib.parse import urlparse
import datetime  # Add this import

app = FastAPI()

class MessageBody(BaseModel):
    url: str  # URL of the MP3 file
    number: str  # Number or ID for output filename

IMAGE_PATH = "360_F_406919209_O9Sy4SKu3dVx0mE3RqYfCH5hqMwVWbOk.jpg"  # Local file path to the static image

# Supabase configuration
SUPABASE_URL = "https://oqhygqxpxpdjtvaahwxk.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xaHlncXhweHBkanR2YWFod3hrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTYxNTY5MSwiZXhwIjoyMDQxMTkxNjkxfQ.oYECwS4Y6ymOwGuXOVKh0lIWQVlgnbDOlDCfYY1AUVk"  # Replace with your Supabase API key
SUPABASE_BUCKET = "video"  # Name of your storage bucket

if not SUPABASE_URL or not SUPABASE_API_KEY or not SUPABASE_BUCKET:
    raise Exception("Supabase configuration is missing. Please set SUPABASE_URL, SUPABASE_API_KEY, and SUPABASE_BUCKET environment variables.")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/sendMessage")
async def say_hello(body: MessageBody):
    mp3_url = body.url

    # Extract the filename from the URL
    parsed_url = urlparse(mp3_url)
    filename = os.path.basename(parsed_url.path)
    base_filename, ext = os.path.splitext(filename)

    # Generate a timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    # Create a new video filename that includes the timestamp
    video_filename = f"{base_filename}_{timestamp}.mp4"

    # Download the MP3 from the provided URL
    try:
        mp3_response = requests.get(mp3_url)
        mp3_response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading MP3: {str(e)}")

    mp3_path = filename  # Use the extracted filename
    with open(mp3_path, "wb") as mp3_file:
        mp3_file.write(mp3_response.content)

    # Verify that the MP3 file exists and is accessible
    if not os.path.exists(mp3_path):
        raise HTTPException(status_code=500, detail="MP3 file not found after download.")

    # Load the audio
    try:
        audio_clip = AudioFileClip(mp3_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading audio: {str(e)}")

    # Create a video using the image and the MP3 audio
    try:
        image_clip = ImageClip(IMAGE_PATH, duration=audio_clip.duration)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading image: {str(e)}")

    video = image_clip.set_audio(audio_clip)

    # Write the video file with appropriate codecs
    try:
        video.write_videofile(
            video_filename,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=f"temp-audio-{base_filename}_{timestamp}.m4a",  # Use timestamp in temp audio filename
            remove_temp=True,
            threads=4,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing video file: {str(e)}")

    # Upload the video to Supabase storage
    try:
        with open(video_filename, "rb") as video_file:
            video_data = video_file.read()

        upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{video_filename}"

        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Bearer {SUPABASE_API_KEY}",
            "Content-Type": "video/mp4",
        }

        response = requests.post(upload_url, headers=headers, data=video_data)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading video to Supabase: {str(e)}")

    # Delete the audio and video files from the system
    try:
        os.remove(mp3_path)
        os.remove(video_filename)
    except Exception as e:
        print(f"Error deleting files: {str(e)}")

    # Construct the public URL of the uploaded video
    video_public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{video_filename}"

    # Send the video message via WhatsApp using Facebook Graph API
    try:
        graph_api_url = "https://graph.facebook.com/v15.0/330351516817410/messages"

        headers = {
            "Authorization": "Bearer EAAQHiLvKGhoBO2i0ZAZAnZCyPCGhQ2GvucJa5naoliRhGmg2SvOzyueA4bWjipeJwym6ZBCaVKx1UMZATZALeDhopTMfdPbuXRMdatAbCJxagZBAZAuG9ch4v6SZBaRp5ZAvwMoxGiyk29KtIbYFnhQuIgiAcbdZBZCMyOeXi0w3ZAKZAkRdZAyZCIlYA9sMBOtFNVIc950RlBjt4ZB5YNnW4e67m7uGsKSiA9HMZD",  # Replace with your access token
            "Content-Type": "application/json"
        }

        data = {
            "messaging_product": "whatsapp",
            "to": body.number,
            "type": "video",
            "video": {
                "link": video_public_url
            }
        }

        response = requests.post(graph_api_url, headers=headers, json=data)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending video message via WhatsApp: {str(e)}")

    return {
        "affected": 1,
        "video_url": video_public_url
    }

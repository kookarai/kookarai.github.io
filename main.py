import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from moviepy.editor import ImageClip, AudioFileClip
import os

app = FastAPI()

class MessageBody(BaseModel):
    url: str  # URL of the MP3 file
    number: str  # Number or ID for output filename

IMAGE_PATH = "360_F_406919209_O9Sy4SKu3dVx0mE3RqYfCH5hqMwVWbOk.jpg"  # Local file path to the static image

# Supabase configuration
SUPABASE_URL = "https://oqhygqxpxpdjtvaahwxk.supabase.co" # e.g., "https://your-project.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xaHlncXhweHBkanR2YWFod3hrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTYxNTY5MSwiZXhwIjoyMDQxMTkxNjkxfQ.oYECwS4Y6ymOwGuXOVKh0lIWQVlgnbDOlDCfYY1AUVk"  # Your Supabase API key
SUPABASE_BUCKET = "video" # Name of your storage bucket

if not SUPABASE_URL or not SUPABASE_API_KEY or not SUPABASE_BUCKET:
    raise Exception("Supabase configuration is missing. Please set SUPABASE_URL, SUPABASE_API_KEY, and SUPABASE_BUCKET environment variables.")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/sendMessage")
async def say_hello(body: MessageBody):
    mp3_url = body.url

    # Download the MP3 from the provided URL
    try:
        mp3_response = requests.get(mp3_url)
        mp3_response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading MP3: {str(e)}")

    mp3_path = f"audio_{body.number}.mp3"
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
    # Load the image and set its duration to match the audio's duration
    try:
        image_clip = ImageClip(IMAGE_PATH, duration=audio_clip.duration)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading image: {str(e)}")

    # Set the audio of the video to the MP3 file
    video = image_clip.set_audio(audio_clip)
    video_path = f"output_video_{body.number}.mp4"

    # Write the video file with appropriate codecs
    try:
        video.write_videofile(
            video_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=f"temp-audio-{body.number}.m4a",
            remove_temp=True,
            threads=4,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing video file: {str(e)}")

    # Upload the video to Supabase storage
    try:
        with open(video_path, "rb") as video_file:
            video_data = video_file.read()

        upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{video_path}"

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
        os.remove(video_path)
    except Exception as e:
        print(f"Error deleting files: {str(e)}")

    # Construct the public URL of the uploaded video
    video_public_url = f"{SUPABASE_URL.replace('.co', '.in')}/storage/v1/object/public/{SUPABASE_BUCKET}/{video_path}"

    return {
        "message": f"Video created and uploaded successfully with ID: {body.number}",
        "video_url": video_public_url
    }

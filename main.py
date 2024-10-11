import datetime  # Add this import
import json
import os
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from moviepy.editor import ImageClip, AudioFileClip
from pydantic import BaseModel
from starlette.responses import HTMLResponse

app = FastAPI()

# Mount static files directory
app.mount("/static", StaticFiles(directory="new"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

IMAGE_PATH = "360_F_406919209_O9Sy4SKu3dVx0mE3RqYfCH5hqMwVWbOk.jpg"  # Local file path to the static image

# Supabase configuration
SUPABASE_URL = "https://oqhygqxpxpdjtvaahwxk.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xaHlncXhweHBkanR2YWFod3hrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTYxNTY5MSwiZXhwIjoyMDQxMTkxNjkxfQ.oYECwS4Y6ymOwGuXOVKh0lIWQVlgnbDOlDCfYY1AUVk"  # Replace with your Supabase API key
SUPABASE_BUCKET = "video"  # Name of your storage bucket

LLM_API_URL_TEMPLATE = "http://13.127.104.196:8000/process_msg?house_id={}&cook_id={}&user_message={}"

if not SUPABASE_URL or not SUPABASE_API_KEY or not SUPABASE_BUCKET:
    raise Exception(
        "Supabase configuration is missing. Please set SUPABASE_URL, SUPABASE_API_KEY, and SUPABASE_BUCKET environment variables.")


class Payload(BaseModel):
    number: str  # Number or ID for output filename
    url: str  # URL of the audio file


class MessageBody(BaseModel):
    payload: Payload  # Nested payload containing number and URL


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/root", response_class=HTMLResponse)
async def read_root(request: Request):
    event = datetime.datetime.now()
    return templates.TemplateResponse("index.html", {"request": request, "event": event})


@app.post("/process_ticket/{ticket_id}")
async def process_ticket(ticket_id: int):
    try:
        headers = {
            "apikey": SUPABASE_API_KEY,
            "Authorization": f"Authorization {SUPABASE_API_KEY}",
            "Content-Type": "application/json"
        }
        # Fetch the ticket details using Supabase API
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/ticket_master?id=eq.{ticket_id}",
            headers=headers
        )

        if response.status_code != 200 or not response.json():
            raise HTTPException(status_code=404, detail="Ticket not found")

        ticket_info = response.json()[0]
        house_id = ticket_info['house_id']
        cook_id = ticket_info['cook_id']
        conversations = ticket_info['conversations']

        llm_api_url = LLM_API_URL_TEMPLATE.format(house_id, cook_id, conversations)

        # Call the external LLM API
        if cook_id:
            try:
                llm_response = requests.get(llm_api_url, timeout=60)
                if llm_response.status_code == 200:
                    llm_response_data = llm_response.json()

                    # Update the llm_response in ticket_master using Supabase API
                    update_data = {
                        "llm_message": llm_response_data,
                        "llm_message_duplicate": llm_response_data['message'][1],
                        "llm_intent": llm_response_data['message'][0],
                        "llm_status": "PENDING"
                    }

                    update_response = requests.patch(
                        f"{SUPABASE_URL}/rest/v1/ticket_master?id=eq.{ticket_id}",
                        headers=headers,
                        data=json.dumps(update_data)
                    )

                    if update_response.status_code == 204:
                        return {"message": "LLM response saved successfully", "llm_message": llm_response_data}
                    else:
                        raise HTTPException(status_code=500, detail="Failed to update the llm_response in Supabase")
                else:
                    raise HTTPException(status_code=llm_response.status_code, detail="Error from LLM API")

            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=500, detail=f"Error calling LLM API: {e}")
        else:
            return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing ticket: {e}")


@app.post("/sendMessage")
async def say_hello(body: MessageBody):
    mp3_url = body.payload.url

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
            "Authorization": "Bearer EAAQHiLvKGhoBO5owKwKQEDK9zix4lf5f0aDo2bqmCi36JHxsxB3vfhdKUR40DA515N91dxWMaUZBUY3kCBGq8FEvHX0x3VCKnuWb1hq7ZCqBUPhrxPUDhPnvMnr1V2CQQpz1xmZAyZC22jHleOJeSiMZCrRE4efxcngJfrj7wV23TWGgvjxXO1uwbZA9HxIGWfDP1rbaCXHa4GhWUHvOlJFf95ZAogZD",  # Replace with your access token
            "Content-Type": "application/json"
        }

        data = {
            "messaging_product": "whatsapp",
            "to": body.payload.number,
            "type": "video",
            "video": {
                "link": video_public_url
            }
        }

        response = requests.post(graph_api_url, headers=headers, json=data)
        print(response)
        print(body.payload.number)
        response.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending video message via WhatsApp: {str(e)}")

    return {
        "affected": 1,
        "video_url": video_public_url
    }
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app",host="localhost",port=8000,reload=True)
FROM python:3.8.11-slim

WORKDIR /app

COPY requirements.txt .
COPY . .

RUN apt-get -y update && \
    python -m pip install --upgrade pip && \
    apt-get install ffmpeg libsm6 libxext6  -y && \
    pip3 install -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
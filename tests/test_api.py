from src.config import YOUTUBE_API_KEY
import requests

print("KEY:", YOUTUBE_API_KEY)

url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id=dQw4w9WgXcQ&key={YOUTUBE_API_KEY}"
print(requests.get(url).json())

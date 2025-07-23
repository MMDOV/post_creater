from urllib.parse import uses_relative
from aibot import OpenAi
from wordpress import WordPress
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

FILE_PATH = "machinee.csv"

api_key = os.getenv("API_KEY")
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
site_url = os.getenv("SITE_URL")
if not api_key or not username or not password or not site_url:
    raise RuntimeError(
        "Missing one or more required environment variables: API_KEY, USERNAME, PASSWORD, SITE_URL"
    )

try:
    file = pd.read_csv(FILE_PATH, nrows=1)
    question = str(file["text"][0])

    client = OpenAi(api_key=api_key)

    response = client.get_text_response(prompt=question)
    image_path = client.get_image_response(prompt=question)

    wordpress = WordPress(username=username, password=password, site_url=site_url)
    image_id, image_url = wordpress.upload_image(image_path=image_path)
    wordpress.create_post(
        title=question, content=response, media_id=image_id, image_url=image_url
    )
    df = pd.read_csv(FILE_PATH, skiprows=1)

    df.to_csv(FILE_PATH, index=False)
except KeyError:
    print("File out of words")
except FileNotFoundError:
    print("there is no such file")
except Exception as e:
    print("Unkown error:", e)

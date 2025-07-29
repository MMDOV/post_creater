from aibot import OpenAi
from wordpress import WordPress
import pandas as pd
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import sys

load_dotenv()

log_file = f"wp_poster_{datetime.now().strftime('%Y-%m-%d')}.log"
CSV_FILE_PATH = "machine.csv"

logging.basicConfig(
    filename=log_file,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.CRITICAL)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)


def main():
    api_key = os.getenv("API_KEY")
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    site_url = os.getenv("SITE_URL")
    if not api_key or not username or not password or not site_url:
        logging.error(
            "Missing one or more required environment variables: API_KEY, USERNAME, PASSWORD, SITE_URL",
            exc_info=True,
        )
        raise RuntimeError(
            "Missing one or more required environment variables: API_KEY, USERNAME, PASSWORD, SITE_URL"
        )

    try:
        file = pd.read_csv(CSV_FILE_PATH, nrows=1)
        question = str(file["text"][0])

        client = OpenAi(api_key=api_key)

        response = client.get_text_response(prompt=question)
        image_path = client.get_image_response(prompt=question)
        with open("file.html", "w", encoding="utf-8") as f:
            f.write(response)

        wordpress = WordPress(username=username, password=password, site_url=site_url)
        image_id, image_url = wordpress.upload_image(image_path=image_path)
        wordpress.create_post(
            title=question, content=response, media_id=image_id, image_url=image_url
        )
        df = pd.read_csv(CSV_FILE_PATH)
        df = df.drop(index=0)
        df.to_csv(CSV_FILE_PATH, index=False)
    except KeyError:
        logging.error("File out of words", exc_info=True)
    except FileNotFoundError:
        logging.error("there is no such file", exc_info=True)
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()

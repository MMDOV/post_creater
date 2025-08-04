import asyncio
import aiohttp
import aiofiles
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


async def main():
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

        # wordpress = WordPress(username=username, password=password, site_url=site_url)
        client = OpenAi(api_key=api_key, keyword=question, categories=[], tags=[])
        get_img_task = asyncio.create_task(client.get_valid_farsi_images())
        print("image task started")
        get_text_task = asyncio.create_task(client.get_text_response())
        print("text task started")
        print("awaiting img task")
        img_urls = await get_img_task
        i = 0

        # TODO: modify the images using Pillow
        print("saving images")

        async def download_image(session, url: str, filename: str):
            async with session.get(url) as response:
                if response.status == 200:
                    img_data = await response.read()
                    async with aiofiles.open(filename, "wb") as f:
                        await f.write(img_data)

        tasks = []
        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(img_urls, start=1):
                img_type = url.split(".")[-1]
                filename = f"{client.keyword}{i}.{img_type}"
                task = asyncio.create_task(download_image(session, url, filename))
                tasks.append(task)
            await asyncio.gather(*tasks)

            # image_id, image_url = await wordpress.upload_image(
            #    image_path=f"image{i}.{img_type}"
            # )

        print("awaiting text task")
        json_output, html_output = await get_text_task
        print(json_output)
        with open("file.html", "w", encoding="utf-8") as f:
            f.write(html_output)

        # TODO: need to still edit this wordpress part after getting access to it
        # await wordpress.create_post(
        #    title=question, content=response, media_id=image_id, image_url=image_url
        # )
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
    asyncio.run(main())

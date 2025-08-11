import asyncio
import re
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


# TODO: figure out a way to handle the filters meaning how to determine them automatically or
# if they need to be added manually how can we make the procceses as easy as possible
# TODO: all the info that we need is probably taken in a yaml or env file
# TODO: should be a layer above both of te bots that handles everything
# so that we could get a site, its info, all the categories, tags,
# and pillar words (which are our keywords)
# and then call the keyword bot on each category and so on
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

        wordpress = WordPress(username=username, password=password, site_url=site_url)
        client = OpenAi(
            openai_api_key=api_key, keyword=question, categories=[], tags=[]
        )

        # TODO: handle json output which is tags / categories
        # TODO: test the images
        json_output, html_output = await client.get_text_response()
        # get_image_task = asyncio.create_task(client.get_image_links())
        # img_urls = await get_img_task

        # there are placeholders
        # we get every placeholder and serach for images
        # we give ai the images to rank based on the query
        # pick the best image and upload it
        # get the link and replace the image placeholder
        queries = re.findall(r"<placeholder-img>(.*?)</placeholder-img>", html_output)
        placeholders = re.findall(
            r"<placeholder-img>.*?</placeholder-img>", html_output
        )
        for query, placeholder in zip(queries, placeholders):
            images = await client.google_image_search(query)
            best_image_url = await client.pick_best_image(images, query)

            async with aiohttp.ClientSession() as session:
                img_type = best_image_url.split(".")[-1]
                filename = f"{query.replace(' ', '_')}.{img_type}"
                await download_image(session, best_image_url, filename)
            _, image_url = await wordpress.upload_image(
                image_path=f"{query.replace(' ', '_')}.{img_type}"
            )
            new_tag = f'<img src="{image_url}" alt="{query}">'
            html_output = html_output.replace(placeholder, new_tag)
        # TODO: modify the images using Pillow

        # print(json_output)
        # with open("file.html", "w", encoding="utf-8") as f:
        #    f.write(html_output)

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


async def download_image(session, url: str, filename: str):
    async with session.get(url) as response:
        if response.status == 200:
            img_data = await response.read()
            async with aiofiles.open(filename, "wb") as f:
                await f.write(img_data)


if __name__ == "__main__":
    asyncio.run(main())

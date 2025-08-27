import asyncio
import json
import re
import aiohttp
import aiofiles
from aibot import OpenAi
from wordpress import WordPress
from scrape import Scrape
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
# WARNING: not a lot of error handling. DO NOT PUSH TO PRODUCTION LIKE THIS
# ps: I know you're not gonna listen to me and push anyway but hey I tried
async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    wp_api_user = os.getenv("WP_API_USER")
    wp_api_pass = os.getenv("WP_API_PASS")
    site_url = os.getenv("SITE_URL")
    google_api = os.getenv("GOOGLE_API")
    google_cse = os.getenv("GOOGLE_CSE")
    if (
        not api_key
        or not wp_api_user
        or not wp_api_pass
        or not site_url
        or not google_api
        or not google_cse
    ):
        logging.error(
            "Missing one or more required environment variables: API_KEY, USERNAME, PASSWORD, SITE_URL, GOOGLE_API, GOOGLE_CSE",
            exc_info=True,
        )
        raise RuntimeError(
            "Missing one or more required environment variables: API_KEY, USERNAME, PASSWORD, SITE_URL, GOOGLE_API, GOOGLE_CSE"
        )

    try:
        file = pd.read_csv(CSV_FILE_PATH, nrows=1)
        # question = str(file["text"][0])
        question = "سرما خوردگی"

        wordpress = WordPress(
            username=wp_api_user, password=wp_api_pass, site_url=site_url
        )
        all_tags = await wordpress.get_tags()
        all_categories = await wordpress.get_categories()

        scraper = Scrape(
            google_api_key=google_api,
            google_cse_id=google_cse,
            query=question,
        )
        try:
            top_results_info = await scraper.get_top_results_info()
        except Exception:
            top_results_info = []

        client = OpenAi(
            openai_api_key=api_key,
            google_api_key=google_api,
            google_cse_id=google_cse,
            keyword=question,
            categories=list(all_categories.values()),
            tags=list(all_tags.values()),
            related_articles=[],
            top_results_info=top_results_info,
        )

        html_file = f"{question}.html"
        json_file = f"{question}.json"
        if not os.path.exists(json_file) or not os.path.exists(html_file):
            json_output, html_output = await client.get_text_response()
            async with aiofiles.open(json_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(json_output, indent=2, ensure_ascii=False))

            async with aiofiles.open(html_file, "w", encoding="utf-8") as f:
                await f.write(html_output)
        else:
            async with aiofiles.open(json_file, "r", encoding="utf-8") as f:
                json_output = json.loads(await f.read())

            async with aiofiles.open(html_file, "r", encoding="utf-8") as f:
                html_output = await f.read()
        picked_category_names = json_output["categories"]
        picked_category_ids = [
            cid for cid, name in all_categories.items() if name in picked_category_names
        ]
        picked_tag_names = json_output["tags"]
        picked_tag_ids = [
            cid for cid, name in all_tags.items() if name in picked_tag_names
        ]

        # there are placeholders
        # we get every placeholder and serach for images
        # we give ai the images to rank based on the query
        # pick the best image and upload it
        # get the link and replace the image placeholder
        queries = re.findall(r"<placeholder-img>(.*?)</placeholder-img>", html_output)
        placeholders = re.findall(
            r"<placeholder-img>.*?</placeholder-img>", html_output
        )

        if queries:
            for query, placeholder in zip(queries, placeholders):
                async with aiohttp.ClientSession() as session:
                    images = await client.google_image_search(query)
                    links = [str(image["link"]) for image in images]
                    files = [
                        await download_image(
                            session, link, f"{str(i)}.{link.split('.')[-1]}"
                        )
                        for i, link in enumerate(links)
                    ]
                    if len(files) >= 1:
                        best_image = files[0]
                    else:
                        html_output = html_output.replace(placeholder, "")
                        continue
                    img_type = best_image.split(".")[-1]
                    for file in files:
                        if file != best_image:
                            os.remove(file)
                    os.rename(best_image, f"{query.replace(' ', '_')}.{img_type}")
                    print(best_image)
                image_url = await wordpress.upload_image(
                    image_path=f"{query.replace(' ', '_')}.{img_type}"
                )
                new_tag = f'<img src="{image_url}" alt="{query}">'
                html_output = html_output.replace(placeholder, new_tag)
                async with aiofiles.open(html_file, "w", encoding="utf-8") as f:
                    await f.write(html_output)
        # TODO: modify the images using Pillow

        await wordpress.create_post(
            title=question,
            content=html_output,
            categories=picked_category_ids,
            tags=picked_tag_ids,
        )
        # df = pd.read_csv(CSV_FILE_PATH)
        # df = df.drop(index=0)
        # df.to_csv(CSV_FILE_PATH, index=False)
    except KeyError:
        logging.error("File out of words", exc_info=True)
    except FileNotFoundError:
        logging.error("there is no such file", exc_info=True)
    except Exception as e:
        logging.error(e, exc_info=True)


async def download_image(session, url: str, filename: str):
    print(f"downloading image {filename}")
    async with session.get(url) as response:
        if response.status == 200:
            img_data = await response.read()
            async with aiofiles.open(filename, "wb") as f:
                await f.write(img_data)

    return filename


if __name__ == "__main__":
    asyncio.run(main())

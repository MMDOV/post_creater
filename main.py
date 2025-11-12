import asyncio
from dataclasses import dataclass
from typing import List, Dict
import json
import aiofiles
from aibot import OpenAi
from yoast import Yoast
from wordpress import WordPress
from scrape import Scrape
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
async def main() -> None:
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    wp_api_user: str = os.getenv("WP_API_USER", "")
    wp_api_pass: str = os.getenv("WP_API_PASS", "")
    site_url: str = os.getenv("SITE_URL", "")
    google_api: str = os.getenv("GOOGLE_API", "")
    google_cse: str = os.getenv("GOOGLE_CSE", "")
    if not api_key or not wp_api_user or not wp_api_pass or not site_url:
        logging.error(
            "Missing one or more required environment variables: API_KEY, USERNAME, PASSWORD, SITE_URL, GOOGLE_API, GOOGLE_CSE",
            exc_info=True,
        )
        raise RuntimeError(
            "Missing one or more required environment variables: API_KEY, USERNAME, PASSWORD, SITE_URL, GOOGLE_API, GOOGLE_CSE"
        )

    try:
        keyphrase = "سرما خوردگی"
        # keyphrase = str(input("Enter your keyword: "))

        wordpress = WordPress(
            username=wp_api_user, password=wp_api_pass, site_url=site_url
        )
        all_tags = await wordpress.get_tags()
        print(f"all tags:{all_tags}")
        all_categories = await wordpress.get_categories()
        print(f"all categories:{all_categories}")

        scraper = Scrape(
            google_api_key=google_api,
            google_cse_id=google_cse,
        )

        # TODO: clean this up more to the point of nothing but class and/or function calls being here
        html_file = f"{keyphrase}.html"
        json_file = f"{keyphrase}.json"
        if not os.path.exists(json_file) or not os.path.exists(html_file):
            print("files not found")
            top_results_info = await scraper.get_top_results_info(query=keyphrase)

            client = OpenAi(
                openai_api_key=api_key,
                keyword=keyphrase,
                categories=list(all_categories.values()),
                tags=list(all_tags.values()),
            )
            json_output, html_output = await client.get_full_response(
                top_results_info=top_results_info
            )
            async with aiofiles.open(json_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(json_output, indent=2, ensure_ascii=False))

            async with aiofiles.open(html_file, "w", encoding="utf-8") as f:
                await f.write(html_output)
        else:
            print("vanilla files exist")
            async with aiofiles.open(json_file, "r", encoding="utf-8") as f:
                json_output = json.loads(await f.read())

            async with aiofiles.open(html_file, "r", encoding="utf-8") as f:
                html_output = await f.read()

        print(json.dumps(json_output, indent=2, ensure_ascii=False))
        data = separate_json_data(json_output, all_tags, all_categories)

        picked_category_ids = data.picked_category_ids
        picked_tag_ids = data.picked_tag_ids
        faqs = data.faqs
        post_title = data.post_title
        meta = data.meta
        slug = data.slug
        sources = data.sources
        conversation_id = data.conversation_id
        client = OpenAi(
            openai_api_key=api_key,
            keyword=keyphrase,
            categories=list(all_categories.values()),
            tags=list(all_tags.values()),
            conversation_id=conversation_id,
            html_output=html_output,
            json_output=json_output,
        )

        analyzer = Yoast(
            filters=[
                "images",
                "imageKeyphrase",
                "slugKeyword",
                "internalLinks",
            ]
        )
        analyzer.analyze(
            keyword=keyphrase,
            title=post_title,
            meta=meta,
            slug=slug,
            text=html_output,
            locale="fa",
        )
        analysys = analyzer.get_analysis()

        while len(analysys) >= 1:
            analyzer.analyze(
                keyword=keyphrase,
                title=post_title,
                meta=meta,
                slug=slug,
                text=html_output,
                locale="fa",
            )
            analysys = analyzer.get_analysis()
            # this part is for testing
            # ++++++++++++++++++++++++
            print(html_output)
            print(
                json.dumps(
                    analyzer.get_analysis(["_identifier", "text"]),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            print(len(analysys))
            user_input = str(input("would you like to improve? (y/n)")).lower()
            if user_input != "y":
                break
            # ++++++++++++++++++++++++
            json_output, html_output = await client.improve_article(
                title=post_title, yoast_info=analysys
            )

            print(json.dumps(json_output, indent=2, ensure_ascii=False))
            data = separate_json_data(json_output, all_tags, all_categories)

            picked_category_ids = data.picked_category_ids
            picked_tag_ids = data.picked_tag_ids
            faqs = data.faqs
            post_title = data.post_title
            meta = data.meta
            sources = data.sources
            conversation_id = data.conversation_id
            async with aiofiles.open(json_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(json_output, indent=2, ensure_ascii=False))

            async with aiofiles.open(html_file, "w", encoding="utf-8") as f:
                await f.write(html_output)

        await wordpress.create_post(
            keyword=keyphrase,
            title=post_title,
            content=html_output,
            slug=slug,
            faqs=faqs,
            meta=meta,
            article_sources=sources,
            categories=picked_category_ids,
            tags=picked_tag_ids,
        )
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


@dataclass
class JsonData:
    picked_category_ids: List[int]
    picked_tag_ids: List[int]
    faqs: List[Dict[str, str]]
    post_title: str
    meta: str
    slug: str
    sources: List[Dict[str, str]]
    conversation_id: str


# FIX: the tags and categories are not being sent to the api currectly
def separate_json_data(json: dict, all_tags: dict, all_categories: dict) -> JsonData:
    print("got json data, separating...")
    print(json)
    picked_category_names = json["categories"]
    picked_category_ids = [
        cid for cid, name in all_categories.items() if name in picked_category_names
    ]

    picked_tag_names = json["tags"]
    picked_tag_ids = [cid for cid, name in all_tags.items() if name in picked_tag_names]
    print(f"categories id:{picked_category_ids}")
    print(f"categories:{picked_category_names}")
    print(f"tags id:{picked_tag_ids}")
    print(f"tags:{picked_tag_names}")

    return JsonData(
        picked_category_ids=picked_category_ids,
        picked_tag_ids=picked_tag_ids,
        faqs=json["faqs"],
        post_title=json["title"],
        meta=json["meta"],
        slug=json["slug"],
        sources=json["sources"],
        conversation_id=json["conversation_id"],
    )


if __name__ == "__main__":
    asyncio.run(main())

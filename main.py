import asyncio
import json
from aibot import OpenAi
from yoast import Yoast
from wordpress import WordPressClient
from scrape import Scrape
from config import (
    validate_environment,
    api_key,
    google_api,
    google_cse,
    related_article_data,
)
from models import SiteInfo, PostData, PostJsonData
from workflow import generate_post_if_missing, optimize_until_valid


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
    site_info: SiteInfo = SiteInfo()
    post_info: PostData = PostData()
    validate_environment(site_info, post_info)
    wordpress = WordPressClient(
        username=site_info.wp_api_user,
        password=site_info.wp_api_pass,
        site_url=site_info.site_url,
    )
    site_info.all_tags = await wordpress.get_tags()
    site_info.all_categories = await wordpress.get_categories()
    print(f"all tags:{site_info.all_tags}")
    print(f"all categories:{site_info.all_categories}")
    related_articles = (
        await wordpress.get_posts_info(related_article_data)
        if related_article_data
        else []
    )
    print(related_articles)

    scraper = Scrape(
        google_api_key=google_api,
        google_cse_id=google_cse,
    )
    client = OpenAi(
        openai_api_key=api_key,
        keyword=post_info.keyphrase,
        categories=list(site_info.all_categories.values()),
        tags=list(site_info.all_tags.values()),
        related_articles=related_articles,
    )

    json_output, html_output = await generate_post_if_missing(
        post_info, scraper, client
    )
    print(json.dumps(json_output, indent=2, ensure_ascii=False))
    post_info.html = html_output
    post_info.json = PostJsonData.from_json(json=json_output, site_info=site_info)

    client.conversation_id = post_info.json.conversation_id
    client.html_output = html_output
    client.json_output = json_output
    analyzer = Yoast(
        filters=[
            "images",
            "imageKeyphrase",
            "slugKeyword",
        ]
    )
    await optimize_until_valid(client, analyzer, post_info, site_info)
    await wordpress.create_post(
        post_data=post_info,
    )


if __name__ == "__main__":
    asyncio.run(main())

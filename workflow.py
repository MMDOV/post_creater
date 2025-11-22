from models import PostData, SiteInfo
from aibot import OpenAi
from yoast import Yoast
from models import PostJsonData
import json
from file_utils import read_json_file, read_text_file, save_to_file
from scrape import Scrape


async def optimize_until_valid(
    client: OpenAi,
    analyzer: Yoast,
    post_data: PostData,
    site_data: SiteInfo,
    maximum_iterations: int = 100,
    maximum_problems: int = 1,
):
    iteration = 0
    html_file = f"{post_data.keyphrase}.html"
    json_file = f"{post_data.keyphrase}.json"
    while True:
        analyzer.analyze(
            keyword=post_data.keyphrase,
            title=post_data.json.post_title,
            meta=post_data.json.meta,
            slug=post_data.json.slug,
            text=post_data.html,
            permalink=site_data.site_url,
            locale="fa",
        )
        analysis = analyzer.get_analysis()
        # optional: print/debug
        user_input = input("Would you like to improve? (y/n)").lower()
        if user_input != "y":
            break
        json_output, html_output = await client.improve_article(
            title=post_data.json.post_title,
            yoast_info=analysis,
        )
        post_data.json = PostJsonData.from_json(json_output, site_data)
        post_data.html = html_output
        await save_to_file(
            json_file, json.dumps(json_output, indent=2, ensure_ascii=False)
        )
        await save_to_file(html_file, html_output)
        iteration += 1
        if len(analysis) <= maximum_problems or iteration >= maximum_iterations:
            break


async def generate_post_if_missing(
    post_info: PostData, scraper: Scrape, client: OpenAi
):
    json_file = f"{post_info.keyphrase}.json"
    html_file = f"{post_info.keyphrase}.html"

    try:
        json_output = await read_json_file(json_file)
        html_output = await read_text_file(html_file)
    except FileNotFoundError:
        top_results_info = await scraper.get_top_results_info(query=post_info.keyphrase)
        json_output, html_output = await client.get_full_response(
            top_results_info=top_results_info
        )
        await save_to_file(
            json_file, json.dumps(json_output, indent=2, ensure_ascii=False)
        )
        await save_to_file(html_file, html_output)

    return json_output, html_output

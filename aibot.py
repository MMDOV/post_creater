from openai import AsyncOpenAI
import re
import json
import aiohttp


class OpenAi:
    def __init__(
        self,
        openai_api_key: str,
        google_api_key: str,
        google_cse_id: str,
        keyword: str,
        categories: list[str],
        tags: list[str],
        related_articles: list[dict],
    ) -> None:
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id
        self.keyword = keyword
        self.categories = categories
        self.tags = tags
        self.related_articles = related_articles

    async def get_image_links(self):
        image_response = await self.client.responses.create(
            model="gpt-5",
            tools=[{"type": "web_search_preview"}],
            input=[
                {
                    "role": "user",
                    "content": f"Find 10 high-quality, royalty-free images relevant to '{self.keyword}' "
                    "and return only direct image URLs in a plain list, no HTML, no markdown.",
                }
            ],
        )

        return image_response

    async def get_text_response(self) -> tuple[dict, str]:
        # TODO: still need to figure out how are we adding the pillar page

        print("getting text responsse")
        print("keyword:", self.keyword)
        article_response = await self.client.responses.create(
            model="gpt-5",
            reasoning={"effort": "medium"},
            tools=[{"type": "web_search_preview"}],
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Return the result as clean HTML, but do NOT include <html>, <head>, or <body> tags. "
                        "Wrap the entire content in a <div> with lang='fa' and dir='rtl'. "
                        "Style the content for good readability with appropriate spacing and formatting for Persian. "
                        "Verify your info and make sure it is up to date and correct. "
                        "Only return valid HTML. No code blocks or markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
                        Create a 1500-word SEO-optimized article focused on Primary Keyword “{self.keyword}”.
                        Structure the article with 12 headings that integrate the primary keyword naturally in the first 100 words,
                        2–3 subheadings, and the conclusion. Include a meta description (under 160 characters) containing Primary Keyword.
                        Use simple language, short paragraphs (≤3 lines), and ensure readability (Flesch-Kincaid Grade 8–9).

                        Add 3 FAQs addressing common user queries about the Topic, formatted as: Q: ... A:...

                        Here is a list of related internal blog articles. Insert hyperlinks to them wherever relevant 
                        in the article, using natural descriptive anchor text from their titles or summaries. 
                        You may link multiple times to the same article if it’s relevant in different sections, 
                        but avoid keyword stuffing. Do not make up links that are not in this list.

                        Related Articles:
                        {self.related_articles}

                        Whenever you mention something that could be illustrated visually, insert an HTML placeholder tag like:
                        <placeholder-img>short descriptive sentence of the image to search for</placeholder-img>
                        The description should be specific enough to search for relevant images on Google.
                        Do not insert actual <img> tags or image URLs, only this placeholder.

                        After the article, return a JSON block (outside of the HTML) selecting the most relevant
                        categories and tags from the lists below based on the content you generated:

                        Categories: {self.categories}
                        Tags: {self.tags}

                        Output format (outside the HTML):
                        {{
                          "categories": ["category1", "category2"],
                          "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
                        }}

                        Output format:
                        Meta Description
                        Introduction (100 words ending with 'In this guide, we’ll cover...')
                        12 headings with content
                        FAQs
                        Internal links placed naturally in the HTML
                        Image placeholders inserted where relevant
                    """,
                },
            ],
        )
        print(article_response.output_text)
        json_output, html_output = await separate_json(article_response.output_text)

        return json_output, html_output

    async def google_image_search(self, query, num_results=5) -> list[dict]:
        print("searching google")
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "cx": self.google_cse_id,
            "key": self.google_api_key,
            "searchType": "image",
            "num": min(num_results * 2, 10),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params) as response:
                response.raise_for_status()
                results = await response.json()

        images = []
        async with aiohttp.ClientSession() as session:
            for item in results.get("items", []):
                link = item.get("link", "")
                if await is_valid_image(session, link) and str(link).endswith(
                    (".jpg", ".jpeg", ".png", ".webp")
                ):
                    images.append(
                        {
                            "title": item.get("title"),
                            "link": link,
                            "thumbnail": item.get("image", {}).get("thumbnailLink"),
                            "context_link": item.get("image", {}).get("contextLink"),
                        }
                    )
                if len(images) >= num_results:
                    break
        print(json.dumps(images, indent=4, sort_keys=True))

        return images

    async def pick_best_image(self, file_paths: list[str], query: str) -> str:
        files = [await self.create_file(image) for image in file_paths]
        prompt_text = (
            f"Rank the following images from best to worst in describing the word '{query}'. "
            "Return your answer ONLY as a JSON object with keys 'best' and 'ranking', "
            "where 'best' is the number of the best image and 'ranking' is a list of all URLs ordered "
            "only send back numbers no other follow up words just the number"
        )
        print("picking best image")
        print(file_paths)
        best_img_response = await self.client.responses.create(
            model="gpt-5",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt_text,
                        },
                        *[
                            {
                                "type": "input_image",
                                "file_id": file,
                            }
                            for file in files
                        ],
                    ],
                }
            ],
        )
        result = json.loads(best_img_response.output_text)
        print(result)
        best_url_idx = result.get("best")
        for file_id in files:
            await self.client.files.delete(file_id)
        return best_url_idx

    async def create_file(self, file_path):
        with open(file_path, "rb") as file_content:
            result = await self.client.files.create(
                file=file_content,
                purpose="vision",
            )
            return result.id


async def separate_json(text: str) -> tuple[dict, str]:
    print("trying to seperate")
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        json_text = match.group()
        try:
            json_output = json.loads(json_text)
        except json.JSONDecodeError:
            json_output = {"categories": [], "tags": []}
        html_output = text[: match.start()].strip()
    else:
        json_output = {"categories": [], "tags": []}
        html_output = text.strip()
    return json_output, html_output


async def is_valid_image(session, url: str) -> bool:
    try:
        async with session.head(url, allow_redirects=True) as resp:
            if resp.status == 200:
                content_type = resp.headers.get("Content-Type", "")
                return content_type.startswith("image/")
    except Exception as e:
        print(e)
        return False
    return False

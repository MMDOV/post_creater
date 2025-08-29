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
        top_results_info: list[dict],
    ) -> None:
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id
        self.keyword = keyword
        self.categories = categories
        self.tags = tags
        self.related_articles = related_articles
        self.top_results_info = top_results_info

    async def get_text_response(self) -> tuple[dict, str]:
        # TODO: still need to figure out how are we adding the pillar page
        # TODO: add and test search apis other than google for images
        # FIX: overall fixup the prompt probably remove a lot of it, maybe search for other prompts
        # TODO: test the new prompt and see if it works things added are:
        ## top result info
        ## search phrases are now better (not english yet that needs test too)
        ## should include summery
        ## should not have custom styling
        ## the title and faq should be part of the json and usable
        # FIX: make sure that the prompt including {} doesnt break it when sending the request

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
                        "Use clean HTML for structure only (e.g., <h1>, <h2>, <p>, <ul>, <ol>, <a>, etc.). "
                        "Do NOT add inline styles, CSS classes, or custom attributes so that the WordPress theme styling is not broken. "
                        "Verify your info and make sure it is up to date and correct. "
                        "Only return valid HTML. No code blocks or markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
                        Create a 1500-word SEO-optimized article focused on Primary Keyword: “{
                        self.keyword
                    }”.

                        Take into account the following data extracted from the top 5 Google results for this keyword:
                        {self.top_results_info}

                        Use this information to improve relevance, heading structure, and content coverage, while ensuring originality (do not copy text).

                        Structure:
                        - Title: Write a compelling, SEO-friendly blog post title.
                        - Summary: Provide a short summary paragraph at the very top that concisely explains what the entire article covers.
                        - Meta description (≤160 characters) containing the Primary Keyword.
                        - Introduction (≈100 words ending with: "In this guide, we’ll cover...")
                        - 12 main headings (include the Primary Keyword naturally in the first 100 words).
                        - 2–3 subheadings under relevant main headings.
                        - Short paragraphs (≤3 lines) written in simple, clear language (Flesch-Kincaid Grade 8–9).
                        - Conclusion.
                        - 3 FAQs addressing common user queries about the Topic (these must also be included in the JSON output).

                        Internal Linking:
                        Here is a list of related internal blog articles. Insert hyperlinks to them wherever relevant in the article, using natural descriptive anchor text from their titles or summaries. You may link multiple times to the same article if relevant, but avoid keyword stuffing. Do not make up links that are not in this list.

                        Related Articles:
                        {self.related_articles}

                        Image Placeholders:
                        Whenever you mention something that could be illustrated visually, insert an HTML placeholder tag like:
                        <placeholder-img>{
                        self.keyword
                    }: short descriptive sentence of the image to search for</placeholder-img>
                        The description must always include the Primary Keyword (or part of it) to ensure relevance to the article topic.
                        Do not insert actual <img> tags or URLs, only this placeholder.

                        Final Output:
                        After the full article (HTML content), provide a JSON block containing:
                        - The post title you generated.
                        - The most relevant categories and tags.
                        - The FAQs as structured objects.

                        Categories: {self.categories}
                        Tags: {self.tags}

                        Output format (outside the HTML):
                        {{
                        "title": "Generated SEO Title Here",
                          "categories": ["category1", "category2"],
                          "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
                          "faqs": [
                            {{"question": "Q1 text", "answer": "A1 text"}},
                            {{"question": "Q2 text", "answer": "A2 text"}},
                            {{"question": "Q3 text", "answer": "A3 text"}}
                          ]
                        }}

                    """,
                },
            ],
        )
        print(article_response.output_text)
        json_output, html_output = await separate_json(article_response.output_text)

        return json_output, html_output

    async def google_image_search(self, query, num_results=1) -> list[dict]:
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

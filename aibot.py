from openai import AsyncOpenAI
from ddgs import DDGS
import aiohttp
import asyncio
import base64


class OpenAi:
    def __init__(self, api_key: str, keyword: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.keyword = keyword

    async def get_text_response(self) -> str:
        response = await self.client.responses.create(
            model="gpt-4.1",
            tools=[{"type": "web_search_preview"}],
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Return the result as clean HTML, but do NOT include <html>, <head>, or <body> tags. "
                        "Wrap the entire content in a <div> with lang='fa' and dir='rtl'. "
                        "Style the content for good readability with appropriate spacing and formatting for Persian. "
                        "Verify your info and make sure it is up to date and correct "
                        "Only return valid HTML. No code blocks or markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
                        Create a 1500-word SEO-optimized article focused on Primary Keyword “{self.keyword}”. Structure the article with 12 headings that integrate the primary keyword naturally in the first 100 words, 2–3 subheadings, and the conclusion. Include a meta description (under 160 characters) containing Primary Keyword. Use simple language, short paragraphs (≤3 lines), and ensure readability (Flesch-Kincaid Grade 8–9).  

                        Add 3 FAQs addressing common user queries about the Topic, formatted as: Q: ... A:...
                          
                        Suggest 2 internal links:
                        Link 1: Use anchor text [Anchor Text 1].
                        Link 2: Use anchor text [Anchor Text 2].

                        Avoid keyword stuffing and maintain a conversational tone. Output format:
                        Meta Description
                        Introduction (100 words ending with 'In this guide, we’ll cover...')
                        12 headings with content
                        FAQs
                        Internal linking suggestions with placement notes."
                    """,
                },
            ],
        )
        return response.output_text

    async def get_valid_farsi_images(self, max_results=10):
        query = f"{self.keyword} عکس site:.ir"

        def run_search():
            with DDGS() as ddgs:
                return list(
                    ddgs.images(
                        query,
                        max_results=max_results,
                        region="wt-wt",
                        size="Medium",
                    )
                )

        results = await asyncio.to_thread(run_search)

        async def is_valid_image_url(session, url):
            try:
                async with session.head(
                    url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        return url
            except Exception:
                pass
            return None

        urls = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for result in results:
                url = result.get("image")
                if url and url.endswith((".jpg", ".png")):
                    tasks.append(is_valid_image_url(session, url))
                if len(tasks) >= max_results * 2:
                    break

            checked = await asyncio.gather(*tasks)
            urls = [u for u in checked if u][:3]

        return urls

    async def get_image_response(self, prompt: str) -> str:
        image_prompt = f"""
        Generate an image that describes the text below best:\n\n
        {prompt}
        """

        result = await self.client.images.generate(
            model="dall-e-3", prompt=image_prompt, response_format="b64_json"
        )

        if result:
            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            with open(f"{prompt.replace(' ', '_')}.png", "wb") as f:
                f.write(image_bytes)

        return f"{prompt}.png"

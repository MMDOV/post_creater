from openai import AsyncOpenAI, responses
import re
import json
import base64


class OpenAi:
    def __init__(
        self,
        openai_api_key: str,
        keyword: str,
        categories: list[str],
        tags: list[str],
        related_articles: list[dict],
    ) -> None:
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.keyword = keyword
        self.categories = categories
        self.tags = tags
        self.related_articles = related_articles
        self.conversation_id = None

    async def _initialize_conversation(self) -> None:
        if not self.conversation_id:
            conversation = await self.client.conversations.create()
            self.conversation_id = conversation.id

    async def _get_text_response(self, input):
        await self._initialize_conversation()
        self.current_response = await self.client.responses.create(
            model="gpt-5",
            reasoning={"effort": "medium"},
            tools=[{"type": "web_search_preview"}],
            input=input,
            conversation=self.conversation_id,
        )

    async def get_full_response(self, top_results_info) -> tuple[dict, str]:
        # TODO: still need to figure out how are we adding the pillar page
        # TODO: make this conversation based so you could feed it more data
        # FIX: change the prompt so it knows about the conversation and we can feed it more data

        print("getting text responsse")
        print("keyword:", self.keyword)
        initial_input = [
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
                        {top_results_info}
                        You can change the number of stuff (Headings, images, etc) that you include based on this info but keep the main structure the way that is described to you.

                        Use this information to improve relevance, heading structure, and content coverage, while ensuring originality (do not copy text).

                        Structure:
                        - Title: Write a compelling, SEO-friendly blog post title.
                        - Summary: Provide a short summary paragraph at the very top that concisely explains what the entire article covers.
                        - Introduction (≈100 words)
                        - 12 main headings (include the Primary Keyword naturally in the first 100 words).
                        - 2–3 subheadings under relevant main headings.
                        - Short paragraphs (≤3 lines) written in simple, clear language (Flesch-Kincaid Grade 8–9).
                        - Conclusion.

                        Internal Linking:
                        Here is a list of related internal blog articles. Insert hyperlinks to them wherever relevant in the article, using natural descriptive anchor text from their titles or summaries. You may link multiple times to the same article if relevant, but avoid keyword stuffing. Do not make up links that are not in this list.

                        Related Articles:
                        {self.related_articles}

                        Image Placeholders:
                        Whenever you mention something that could be illustrated visually, insert an HTML placeholder tag like:
                        <placeholder-img>short descriptive sentence of the image to search for in english</placeholder-img>
                        The description must always include the Primary Keyword (or part of it) in english to ensure relevance to the article topic.
                        notice that unlike the post itself the description of the image should be in english including the primary keyword (or part of it)
                        Do not insert actual <img> tags or URLs, only this placeholder.

                        Final Output:
                        After the full article (HTML content), provide a JSON block containing:
                        - The post title you generated.
                        - The most relevant categories and tags.
                        - 3 FAQs addressing common user queries about the Topic as structured objects (these must only be included in the JSON output).
                        - Meta description (≤160 characters) containing the Primary Keyword.

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
                          "meta" : "Generated meta description"
                        }}

                    """,
            },
        ]
        await self._get_text_response(input=initial_input)
        print(self.current_response.output_text)
        json_output, html_output = await separate_json(
            self.current_response.output_text
        )

        return json_output, html_output

    async def get_image_response(self, prompt: str) -> str:
        image_prompt = f"""
        Generate an image that describes the text below best:\n\n
        {prompt}
        """

        result = await self.client.images.generate(
            model="dall-e-3", prompt=image_prompt, response_format="b64_json"
        )
        print(result)

        if result:
            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            with open("1.png", "wb") as f:
                f.write(image_bytes)

        return "1.png"


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

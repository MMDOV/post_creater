from openai import AsyncOpenAI
import re
import json


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

    async def get_full_response(self, top_results_info: list[dict]) -> tuple[dict, str]:
        # TODO: still need to figure out how are we adding the pillar page

        print("getting text responsse")
        print("keyword:", self.keyword)

        messages = [
            {
                "role": "developer",
                "content": (
                    "You are an assistant that will receive instructions for writing a Persian SEO blog post.\n"
                    "- Do NOT generate any blog content until I explicitly send the signal [FINAL].\n"
                    "- For every message before [FINAL], simply acknowledge (e.g. 'Noted').\n"
                    "- When [FINAL] is received, combine ALL previously provided data with the final generation "
                    "instructions to produce the complete output."
                ),
            },
            {
                "role": "developer",
                "content": (
                    "When generation begins:\n"
                    "• Return the result as clean HTML only—NO <html>, <head>, or <body> tags.\n"
                    "• Wrap the entire content in a single <div lang='fa' dir='rtl'>.\n"
                    "• Use only clean structural tags (<h1>, <h2>, <p>, <ul>, <ol>, <a>, etc.).\n"
                    "• Do NOT add inline styles, CSS classes, or custom attributes (to avoid breaking theme styling).\n"
                    "• Verify all information and ensure it is up-to-date and correct.\n"
                    "• After the HTML, append a JSON block containing:\n"
                    '   - "title": generated SEO title\n'
                    '   - "categories": [list of relevant categories]\n'
                    '   - "tags": [list of 5 relevant tags]\n'
                    '   - "faqs": [3 objects {"question","answer"}]\n'
                    '   - "meta": meta description (≤160 characters containing the Primary Keyword)\n'
                    '   - "sources": list of objects with "title" and "link" for every source you referenced in the article'
                ),
            },
            {
                "role": "user",
                "content": (
                    f'Primary Keyword: "{self.keyword}"\n'
                    "Do not write the article yet—just acknowledge."
                ),
            },
            {
                "role": "user",
                "content": (
                    "You will receive the data extracted from the top 5 Google results for this keyword. "
                    "Each message will contain one result. "
                    "Do NOT generate the article yet; just acknowledge each part.\n\n"
                    "Important guidance:\n"
                    "- You can change the number of elements (headings, images, etc.) based on this info, "
                    "but keep the main structure as described.\n"
                    "- Use this information to improve relevance, heading structure, and coverage, while ensuring originality. "
                    "Do not copy text."
                ),
            },
            *[
                {
                    "role": "user",
                    "content": (
                        f"Top result #{i + 1}:\n{info}\n"
                        "Acknowledge only. Incorporate this later when generating the article."
                    ),
                }
                for i, info in enumerate(top_results_info)
            ],
            {
                "role": "user",
                "content": (
                    "Related internal blog articles for internal linking:\n"
                    f"{self.related_articles}\n"
                    "Insert natural descriptive anchor text links to these wherever relevant, but avoid keyword stuffing.\n"
                    "Acknowledge only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Categories: {self.categories}\nTags: {self.tags}\nAcknowledge only."
                ),
            },
            {
                "role": "user",
                "content": (
                    "[FINAL]\n"
                    "Now generate a 1500-word SEO-optimized article using ALL information above.\n"
                    "Follow this structure exactly:\n"
                    "• **Title:** A compelling, SEO-friendly blog post title.\n"
                    "• **Summary:** A short opening paragraph summarizing the article.\n"
                    "• **Introduction (~100 words).**\n"
                    "• **12 main headings** (include the Primary Keyword naturally in the first 100 words).\n"
                    "• 2–3 subheadings under relevant main headings.\n"
                    "• Short paragraphs (≤3 lines) in clear, simple language (Flesch-Kincaid Grade 8–9).\n"
                    "• **Conclusion.**\n\n"
                    "Image Placeholders:\n"
                    "Whenever you mention something that could be illustrated visually, insert an HTML placeholder tag like:\n"
                    "<placeholder-img>short descriptive sentence of the image to search for in english</placeholder-img>\n"
                    "• The placeholder description MUST include the Primary Keyword (or part of it) in English to ensure relevance.\n\n"
                    "JSON Output:\n"
                    "After the HTML content, return a JSON block with:\n"
                    "• title: the generated SEO title\n"
                    "• categories: list of relevant categories\n"
                    "• tags: list of 5 relevant tags\n"
                    "• faqs: 3 objects with question/answer\n"
                    "• meta: meta description (≤160 characters containing the Primary Keyword)\n"
                    "• sources: list of objects with 'title' and 'link' for every source you referenced in the article\n\n"
                    "Only return valid HTML followed by the JSON block."
                ),
            },
        ]
        for message in messages:
            await self._get_text_response(
                input=[{"role": message["role"], "content": message["content"]}],
            )
        print(self.current_response.output_text)
        json_output, html_output = await separate_json(
            self.current_response.output_text
        )

        return json_output, html_output

    async def improve_article(self, yoast_info: list[dict]) -> tuple[dict, str]:
        input = [
            {
                "role": "user",
                "content": (
                    "As you know yoast is a tool for SEO optimization\n"
                    "This is the result of your article passed into yoast\n"
                    "Use this information to improve the article\n"
                    "Give me the article with the exact same structure\n"
                    f"{yoast_info}\n"
                ),
            }
        ]
        await self._get_text_response(input)
        json_output, html_output = await separate_json(
            self.current_response.output_text
        )

        return json_output, html_output


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

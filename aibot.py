from openai import AsyncOpenAI
import re
import json
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)


class OpenAi:
    def __init__(
        self,
        openai_api_key: str,
        keyword: str,
        categories: list[str],
        tags: list[str],
        related_articles: list[dict],
        conversation_id: str | None,
    ) -> None:
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.keyword = keyword
        self.categories = categories
        self.tags = tags
        self.related_articles = related_articles
        self.conversation_id = conversation_id

    async def _initialize_conversation(self) -> None:
        if not self.conversation_id:
            conversation = await self.client.conversations.create()
            self.conversation_id = conversation.id

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def _get_text_response(self, input):
        await self._initialize_conversation()
        print("getting text responsse")
        self.current_response = await self.client.responses.create(
            model="gpt-5",
            reasoning={"effort": "medium"},
            tools=[{"type": "web_search_preview"}],
            input=input,
            conversation=self.conversation_id,
        )

    async def get_full_response(self, top_results_info: list[dict]) -> tuple[dict, str]:
        # TODO: still need to figure out how are we adding the pillar page

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
                    '   - "slug": an SEO-friendly English slug to be used as the URL (avoid Persian characters)\n'
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
                    "• slug: an SEO-friendly English slug to be used as the URL (avoid Persian characters)\n"
                    "• categories: list of relevant categories\n"
                    "• tags: list of 5 relevant tags\n"
                    "• faqs: 3 objects with question/answer\n"
                    "• meta: meta description (≤160 characters containing the Primary Keyword)\n"
                    "• sources: list of objects with 'title' and 'link' for every source you referenced in the article\n\n"
                    "Only return valid HTML followed by the JSON block."
                ),
            },
        ]
        for i, message in enumerate(messages):
            print(f"Message {i}")
            await self._get_text_response(
                input=[{"role": message["role"], "content": message["content"]}],
            )
        print(self.current_response.output_text)
        json_output, html_output = await self.separate_json(
            self.current_response.output_text
        )

        return json_output, html_output

    async def improve_article(
        self, title: str, yoast_info: list[dict]
    ) -> tuple[dict, str]:
        input_prompt = [
            {
                "role": "user",
                "content": (
                    "You are an SEO assistant. Below is the result of a Yoast SEO analysis "
                    "for your previously written article. Your job is to revise the article "
                    "to fix ONLY the issues listed in the analysis, keeping the same tone, "
                    "topic, and overall structure.\n\n"
                    "Yoast analysis:\n"
                    f"{yoast_info}\n\n"
                    "Article details:\n"
                    f"Title: {title}\n"
                    f"Primary Keyword/Keyphrase: {self.keyword}\n\n"
                    "Here is the full article you previously wrote:\n"
                    f"{self.current_response.output_text}\n\n"
                    "Instructions:\n"
                    "- Read the Yoast feedback carefully and address every issue listed.\n"
                    "- Keep paragraph and heading structure unless a fix requires otherwise.\n"
                    "- Do NOT change the tone, meaning, or topic.\n"
                    "- Only modify text where necessary to fix Yoast issues.\n\n"
                    "Output format (must match the initial generation format):\n"
                    "• Return the improved article as clean HTML only—NO <html>, <head>, or <body> tags.\n"
                    "• Wrap the entire content in a single <div lang='fa' dir='rtl'>.\n"
                    "• Use only clean structural tags (<h1>, <h2>, <p>, <ul>, <ol>, <a>, etc.).\n"
                    "• Do NOT add inline styles, CSS classes, or custom attributes.\n"
                    "• After the HTML, append a JSON block containing:\n"
                    '   - "title": improved SEO title (if relevant)\n'
                    '   - "categories": [list of relevant categories]\n'
                    '   - "tags": [list of 5 relevant tags]\n'
                    '   - "faqs": [3 objects {"question","answer"}]\n'
                    '   - "meta": meta description (≤160 characters, must include the Primary Keyword)\n'
                    '   - "sources": list of objects with "title" and "link" for every source referenced in the article\n\n'
                    "Ensure the format is identical to the one used in the original generation step so it can be parsed correctly."
                ),
            }
        ]

        await self._get_text_response(input_prompt)

        json_output, html_output = await self.separate_json(
            text=self.current_response.output_text
        )

        return json_output, html_output

    async def separate_json(self, text: str, max_fixes: int = 3) -> tuple[dict, str]:
        print("trying to separate")
        # Store conversation_id before any processing
        conversation_id = self.conversation_id

        for attempt in range(1, max_fixes + 1):
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                json_text = match.group()
                html_output = text[: match.start()].strip()
                try:
                    json_output = json.loads(json_text)
                except json.JSONDecodeError:
                    json_output = {}
            else:
                html_output = text.strip()
                json_output = {}

            # Add conversation_id to json_output
            json_output["conversation_id"] = conversation_id

            issues = validate_post_json(json_output)
            if not issues:
                print(f"JSON validated successfully after {attempt} attempt(s)")
                return json_output, html_output

            print(f"Attempt {attempt}: JSON has issues -> {issues}")
            missing_keys = ", ".join(issues)
            fix_message = (
                f"The JSON you provided is missing or invalid in the following fields: {missing_keys}.\n"
                "Please fix it and return the full HTML and JSON again, in the same format as before.\n"
                "Reminder: JSON format should include keys: title, slug, categories, tags, faqs, meta, and sources."
            )

            try:
                await self._get_text_response(
                    [{"role": "user", "content": fix_message}]
                )
                text = self.current_response.output_text
            except Exception as e:
                print("Error while requesting fix:", e)
                break
        # Final attempt processing
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            json_text = match.group()
            html_output = text[: match.start()].strip()
            try:
                json_output = json.loads(json_text)
            except json.JSONDecodeError:
                json_output = {}
        else:
            html_output = text.strip()
            json_output = {}
        # Add conversation_id to the final json_output
        json_output["conversation_id"] = conversation_id

        # Fill in missing structure
        required_structure = {
            "title": "",
            "slug": "",
            "categories": [],
            "tags": [],
            "faqs": [{"question": "", "answer": ""}],
            "meta": "",
            "sources": [{"title": "", "link": ""}],
        }
        for key, value in required_structure.items():
            if key not in json_output:
                json_output[key] = value
        print("Could not get a valid JSON after several attempts.")
        return json_output, html_output


def validate_post_json(data: dict):
    issues = []

    # expected top-level structure
    schema = {
        "title": str,
        "slug": str,
        "categories": list,
        "tags": list,
        "faqs": list,
        "meta": str,
        "sources": list,
    }

    # check top-level keys and types
    for key, expected_type in schema.items():
        if key not in data:
            issues.append(f"Missing key: {key}")
            continue
        if not isinstance(data[key], expected_type):
            issues.append(
                f"Invalid type for '{key}': expected {expected_type.__name__}, got {type(data[key]).__name__}"
            )

    # check FAQs
    if isinstance(data.get("faqs"), list):
        for i, faq in enumerate(data["faqs"], start=1):
            if not isinstance(faq, dict):
                issues.append(f"faqs[{i}] is not an object")
                continue
            for subkey in ("question", "answer"):
                if subkey not in faq:
                    issues.append(f"Missing key in faqs[{i}]: {subkey}")
                elif not isinstance(faq[subkey], str):
                    issues.append(
                        f"Invalid type in faqs[{i}]['{subkey}']: expected str"
                    )
    else:
        issues.append("faqs must be a list")

    # check sources
    if isinstance(data.get("sources"), list):
        for i, src in enumerate(data["sources"], start=1):
            if not isinstance(src, dict):
                issues.append(f"sources[{i}] is not an object")
                continue
            for subkey in ("title", "link"):
                if subkey not in src:
                    issues.append(f"Missing key in sources[{i}]: {subkey}")
                elif not isinstance(src[subkey], str):
                    issues.append(
                        f"Invalid type in sources[{i}]['{subkey}']: expected str"
                    )
    else:
        issues.append("sources must be a list")

    return issues

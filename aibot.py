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
        categories: list[str] = [],
        tags: list[str] = [],
        related_articles: list[dict] = [],
        conversation_id: str | None = None,
        html_output: str = "",
        json_output: dict = {},
    ) -> None:
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.keyword: str = keyword
        self.categories: list[str] = categories
        self.tags: list[str] = tags
        self.related_articles: list[dict] = related_articles
        self.conversation_id: str | None = conversation_id
        self.html_output: str = html_output
        self.json_output = json_output

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
        print(self.current_response.output_text)

    async def get_full_response(self, top_results_info: list[dict]) -> tuple[dict, str]:
        print("keyword:", self.keyword)
        print("Categories:", self.categories)
        print("tags:", self.tags)

        messages = [
            {
                "role": "developer",
                "content": (
                    "You are an expert Persian SEO content writer and assistant.\n"
                    "Your task is to generate structured, SEO-optimized Persian blog posts using information provided step-by-step.\n\n"
                    "### Core Rules:\n"
                    "- NEVER generate any article content until you explicitly receive the command [FINAL].\n"
                    "- Before [FINAL], your only valid responses are brief acknowledgements such as 'Noted' or 'Understood'.\n"
                    "- On receiving [FINAL], you must combine **all previously provided context** (keyword, Google results, related articles, tags/categories, etc.) "
                    "to generate the full, final output.\n"
                    "- Maintain a professional, informative tone and natural Persian phrasing (avoid translation-like structures)."
                ),
            },
            {
                "role": "developer",
                "content": (
                    "### Output Format (only used during [FINAL]):\n"
                    "1. Return clean HTML only — no <html>, <head>, or <body> tags.\n"
                    "2. Wrap the entire article in:\n"
                    "   <div lang='fa' dir='rtl'> ... </div>\n"
                    "3. Use only structural tags (<h1>, <h2>, <h3>, <p>, <ul>, <ol>, <a>, <img>, etc.).\n"
                    "4. Do NOT use inline styles, CSS classes, or custom attributes.\n"
                    "5. Ensure factual accuracy and current information.\n\n"
                    "After the HTML, append a valid JSON block with the following fields:\n"
                    "{\n"
                    '  "title": "Generated SEO title",\n'
                    '  "slug": "english-seo-slug",\n'
                    '  "categories": [list of relevant categories],\n'
                    '  "tags": [exactly 5 relevant tags],\n'
                    '  "faqs": [{"question": "...", "answer": "..."}, ... 3 total],\n'
                    '  "meta": "≤160 characters meta description (must include the primary keyword)",\n'
                    '  "sources": [{"title": "...", "link": "..."}, ...]\n'
                    "}\n"
                    "Do not output anything outside this format."
                ),
            },
            {
                "role": "user",
                "content": (
                    f'Primary Keyword: "{self.keyword}"\n'
                    "Acknowledge only. Do not write any article content yet."
                ),
            },
            {
                "role": "user",
                "content": (
                    "You will now receive the top 5 Google search results for this keyword.\n"
                    "Each result will arrive separately. Do NOT generate any text yet — just acknowledge each one.\n\n"
                    "### When generating later:\n"
                    "- Use insights from these results to match or exceed their coverage.\n"
                    "- Do NOT copy text. Rephrase ideas in your own words.\n"
                    "- Improve structure, readability, and topical depth using these insights.\n"
                    "- Incorporate common subtopics and related questions found across multiple results."
                ),
            },
            *[
                {
                    "role": "user",
                    "content": (
                        f"Top result #{i + 1}:\n{info}\n"
                        "Acknowledge only. Incorporate this data later when generating the article."
                    ),
                }
                for i, info in enumerate(top_results_info)
            ],
            {
                "role": "user",
                "content": (
                    "Related internal blog articles (for internal linking):\n"
                    f"{self.related_articles}\n\n"
                    "Instructions for internal linking:\n"
                    "- Insert links naturally in sentences where they add value and context.\n"
                    "- Use descriptive, reader-friendly anchor text derived from the article title, summary, or categories.\n"
                    "- Avoid keyword stuffing and do not force links into unrelated sentences.\n"
                    "- Limit to 2–5 internal links per article, distributed across different sections.\n"
                    "- Before placing a link, **derive the primary intent of each article** based on the information provided (title, summary, tags, categories). "
                    "Use this intent to guide where in the article the link fits best.\n"
                    "  • Informational: for readers seeking general knowledge.\n"
                    "  • Educational / Research: for deeper analysis, comparisons, or detailed explanations.\n"
                    "  • Commercial Investigation: for evaluating options before a purchase or decision.\n"
                    "  • Transactional: for readers ready to buy, book, or submit a form.\n"
                    "  • Navigational: when a reader is looking specifically for a brand, product, or website.\n"
                    "  • Local Intent: when a reader is searching for location-specific results.\n"
                    "Acknowledge only; do not generate article content yet."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Available categories: {self.categories}\n"
                    f"Available tags: {self.tags}\n\n"
                    "Rules:\n"
                    "- Select only from these lists when filling the JSON.\n"
                    "- Do NOT create new category or tag names.\n"
                    "- Pick those most relevant to your article’s focus.\n"
                    "Acknowledge only."
                ),
            },
            {
                "role": "developer",
                "content": (
                    "### HTML Formatting Guidelines:\n"
                    "- Use <strong> for bold emphasis.\n"
                    "- Use <em> for italic emphasis.\n"
                    "- Use <blockquote> for quotes or cited statements.\n"
                    "- Use <ul>/<ol> and <li> for bullet and numbered lists.\n"
                    "- Use <table>, <tr>, <th>, <td> where it helps organize information clearly.\n"
                    "- Use <mark> to highlight key terms if needed.\n"
                    "- Maintain consistent semantic HTML formatting throughout the article.\n\n"
                    "When generating the article on [FINAL], follow these HTML guidelines along with the JSON structure requirements."
                ),
            },
            {
                "role": "user",
                "content": (
                    "[FINAL]\n"
                    "Now generate a complete 1500-word Persian blog post optimized for Yoast SEO.\n\n"
                    "### Structure:\n"
                    "• **Title:** Compelling, SEO-friendly title including the primary keyword near the start.\n"
                    "• **Summary paragraph:** 1 short paragraph summarizing the article.\n"
                    "• **Introduction (~100 words)** introducing the topic naturally.\n"
                    "• **12 main headings (H2)** with 2–3 subheadings (H3) under relevant sections.\n"
                    "• Short paragraphs (≤3 lines), clear sentences, and transition words (مثل «از طرفی»، «در نتیجه»، «به طور کلی»).\n"
                    "• **Conclusion:** A concise wrap-up paragraph.\n"
                    "• Use HTML formatting as described in the previous guidelines where appropriate (bold, italic, blockquotes, lists, tables, and highlights).\n\n"
                    "### SEO Guidelines:\n"
                    "- Include the primary keyword naturally in the title, first paragraph, meta description, and several times in the text.\n"
                    "- Maintain a natural flow — avoid keyword stuffing.\n"
                    "- Add internal and external links naturally where relevant.\n"
                    "- Use informative, keyword-rich headings.\n"
                    "- Keep readability high (simple, clear language).\n\n"
                    "### JSON Output:\n"
                    "Follow the schema described above. Output only HTML followed by JSON, nothing else."
                ),
            },
        ]
        for i, message in enumerate(messages):
            print(f"Message {i}")
            await self._get_text_response(
                input=[{"role": message["role"], "content": message["content"]}],
            )
        print(self.current_response.output_text)
        await self.separate_json(self.current_response.output_text)

        return self.json_output, self.html_output

    async def improve_article(
        self, title: str, yoast_info: list[dict]
    ) -> tuple[dict, str]:
        input_prompt = [
            {
                "role": "user",
                "content": (
                    "IMPORTANT: Do not include explanations, suggestions, or commentary. "
                    "Only return the improved HTML and JSON in the specified format.\n\n"
                    "You are an expert Persian SEO assistant and editor.\n"
                    "Your task is to improve an existing article using the feedback from Yoast SEO analysis.\n\n"
                    "### Yoast analysis fields:\n"
                    "- '_identifier': the issue type (e.g., 'sentenceBeginnings', 'subheadingsKeyword').\n"
                    "- 'text': human-readable description of the issue.\n"
                    "- 'rating': severity ('good', 'ok', 'bad').\n"
                    "- 'problemSentences': list of exact sentences that violate the rule (if available), "
                    "each entry containing 'fullSentence' and 'firstWord'.\n"
                    "For 'subheadingsKeyword', consider all <h2> and <h3> headings as problem sentences.\n"
                    "Rephrase only the sentences listed in 'problemSentences' minimally to fix the issue. "
                    "If needed, rewrite the sentences fully but keep the original meaning.\n\n"
                    "### Yoast quantitative guidance (apply these ranges when making edits):\n"
                    "- **Keyword density:** 0.5%–3% of total words (e.g., for 1500 words, 8–30 occurrences).\n"
                    "- **Meta description:** 120–156 characters, must include the primary keyword.\n"
                    "- **Subheadings with keyword:** 30–75% of H2/H3 should include the keyword.\n"
                    "- **Consecutive sentences starting with the same word:** No more than 2 sentences in a row starting with the same word.\n"
                    "- **Sentence length:** Prefer sentences under 20 words.\n"
                    "- **Transition words:** Use in ≥30% of sentences.\n"
                    "- **Passive voice:** Keep under 10% of sentences.\n"
                    "- **Paragraph length:** ≤150 words per paragraph.\n\n"
                    "### Instructions for improvement:\n"
                    "- Apply the **smallest possible edits** needed to resolve each Yoast issue.\n"
                    "- Do NOT rewrite large portions of text unless absolutely necessary.\n"
                    "- Preserve previously correct optimizations.\n"
                    "- Only modify sections directly related to the issues provided.\n"
                    "- When adjusting ranges (like keyword density or subheading usage), move slightly toward the target without overcompensating.\n"
                    "- Keep tone, topic, structure, headings, and tags/categories unchanged unless absolutely necessary.\n\n"
                    "### Actionable fixes for common Yoast issues:\n"
                    "- **Consecutive sentence beginnings:** Use the 'problemSentences' field to identify sequences of 3 or more sentences starting with the same word. "
                    "Rephrase only the second and third sentences in each sequence using synonyms, pronouns, or slight restructuring. "
                    "If necessary, fully rewrite the sentence while keeping the meaning.\n"
                    "- **Keyword density too high / too low:** Gradually add or remove occurrences to reach the target range (0.5–3%). Preserve naturally placed keywords.\n"
                    "- **Subheadings missing the keyword (subheadingsKeyword):**\n"
                    "  Treat all <h2> and <h3> headings as problem sentences. "
                    "Ensure 30–75% of subheadings contain the primary keyword or a close synonym. "
                    "Lightly adjust only the minimum number required by inserting the keyword or a synonym into the most suitable headings. "
                    "Do not rewrite headings that already contain the keyword. "
                    "Do not exceed 75% keyword usage across all subheadings. "
                    "Do not change heading structure or meaning beyond what is necessary.\n"
                    "- **Meta description too short / too long:** Adjust length to 120–156 characters, including the primary keyword naturally.\n"
                    "- **Sentence length too long:** Split sentences over ~20 words into shorter sentences, keeping meaning and flow.\n"
                    "- **Transition words / readability issues:** Add transition words (e.g., «از طرفی», «در نتیجه») in underrepresented sentences.\n"
                    "- **Passive voice too high:** Rewrite sentences to active voice where necessary.\n"
                    "- **Paragraphs too long:** Split paragraphs >150 words into multiple shorter paragraphs.\n\n"
                    "### Context:\n"
                    f"Title: {title}\n"
                    f"Primary Keyword/Keyphrase: {self.keyword}\n\n"
                    f"Yoast analysis feedback:\n{yoast_info}\n\n"
                    "Full article HTML:\n"
                    f"{self.html_output}\n\n"
                    "Original JSON data (for reference):\n"
                    f"{self.json_output}\n\n"
                    "### Output requirements:\n"
                    "1. Return **improved article as clean HTML** only — no <html>, <head>, or <body> tags.\n"
                    "2. Wrap content in a single <div lang='fa' dir='rtl'> ... </div>\n"
                    "3. Use only structural tags (<h1>, <h2>, <h3>, <p>, <ul>, <ol>, <a>, <img>, etc.)\n"
                    "4. Do NOT add inline styles, CSS classes, or custom attributes.\n\n"
                    "5. Append a **valid JSON block** after the HTML with:\n"
                    '   - "title": improved SEO title (if relevant)\n'
                    '   - "categories": [list of relevant categories]\n'
                    '   - "tags": [list of 5 relevant tags]\n'
                    '   - "faqs": [3 objects {"question","answer"}]\n'
                    '   - "meta": meta description (≤160 characters, must include the Primary Keyword)\n'
                    '   - "sources": list of objects with "title" and "link" for every source referenced in the article\n\n'
                    "### IMPORTANT: Self-check step:\n"
                    "- Before returning HTML and JSON, review each Yoast issue:\n"
                    "  • Make sure you actually have made changes and are not just returning the same thing\n"
                    "  • Count consecutive sentence beginnings; ensure ≤2 per sequence.\n"
                    "  • Verify keyword density and subheading percentages are within target ranges.\n"
                    "  • Confirm meta description length, sentence lengths, transition words, passive voice, and paragraph lengths meet the thresholds above.\n"
                    "- Only return the final improved HTML and JSON when all adjustments are within range.\n\n"
                    "Ensure format is identical to original generation so it can be parsed correctly."
                ),
            }
        ]

        await self._get_text_response(input_prompt)
        await self.separate_json(text=self.current_response.output_text)

        return self.json_output, self.html_output

    async def separate_json(self, text: str, max_fixes: int = 3):
        print("trying to separate")
        conversation_id = self.conversation_id

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            print("initial: theres a match")
            html_output = text[: match.start()].strip()
            json_text = match.group()
        else:
            print("initial: no match found")
            html_output = text.strip()
            json_text = "{}"

        try:
            json_output = json.loads(json_text)
        except json.JSONDecodeError:
            print("initial: json decode error")
            json_output = {}

        for attempt in range(1, max_fixes + 1):
            json_output["conversation_id"] = conversation_id
            issues = validate_post_json(json_output)

            if not issues:
                print(f"JSON validated successfully after {attempt} attempt(s)")
                self.json_output = json_output
                self.html_output = html_output
                return

            print(f"Attempt {attempt}: JSON has issues -> {issues}")
            missing_keys = ", ".join(issues)
            fix_message = (
                f"The JSON you provided is missing or invalid in the following fields: {missing_keys}.\n"
                "Please fix the JSON and return only the corrected JSON object, nothing else.\n"
                "Reminder: JSON format should include keys: title, slug, categories, tags, faqs, meta, and sources."
            )

            try:
                await self._get_text_response(
                    [{"role": "user", "content": fix_message}]
                )
                response_text = self.current_response.output_text.strip()
                try:
                    json_output = json.loads(response_text)
                except json.JSONDecodeError:
                    print("json decode error in fix attempt")
                    json_output = {}
            except Exception as e:
                print("Error while requesting fix:", e)
                break

        # --- Final fallback after all attempts ---
        json_output["conversation_id"] = conversation_id
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
        self.json_output = json_output
        self.html_output = html_output


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

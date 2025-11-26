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
        print("related articles:", self.related_articles)
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
                    "- Before [FINAL], your only valid responses are one word response brief acknowledgements such as 'Noted' or 'Understood'.\n"
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
                    '  "synonyms": [list of relevant synonyms]\n'
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
                    "### Related internal articles format:\n"
                    "- Each item is a dictionary with the following fields:\n"
                    "  • 'title': the article title\n"
                    "  • 'url': full URL of the article\n"
                    "  • 'categories': list of category names\n"
                    "  • 'tags': list of tag names\n"
                    "  • 'first_paragraphs': the first one or two paragraphs of the article\n"
                    "- Use these fields to insert natural, descriptive anchor text links.\n"
                    "- Before placing a link, **derive the primary intent of each article** based on this information.\n"
                    "  • Informational: for readers seeking general knowledge.\n"
                    "  • Educational / Research: for deeper analysis, comparisons, or detailed explanations.\n"
                    "  • Commercial Investigation: for evaluating options before a purchase or decision.\n"
                    "  • Transactional: for readers ready to buy, book, or submit a form.\n"
                    "  • Navigational: when a reader is looking specifically for a brand, product, or website.\n"
                    "  • Local Intent: when a reader is searching for location-specific results.\n"
                    "- Insert links naturally where they add value and context.\n"
                    "- Use descriptive, reader-friendly anchor text derived from the article title, first_paragraphs, or categories.\n"
                    "- Avoid keyword stuffing and do not force links into unrelated sentences.\n"
                    "- Limit to 2–5 internal links per article, distributed across different sections.\n"
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
                "role": "user",
                "content": (
                    "Rules for synonyms:\n"
                    "- Generate 3–5 concise, natural synonyms or alternative phrases for the primary keyword.\n"
                    "- Each synonym should be 1–3 words, reader-friendly, and suitable for Yoast SEO input.\n"
                    "- Synonyms must be in Persian (the same language as the primary keyword).\n"
                    "- Do not repeat the primary keyword itself.\n"
                    "- Ensure relevance and contextual accuracy.\n"
                    "Acknowledge only."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Instructions for using synonyms in the article:\n"
                    "- Treat the generated synonyms as secondary keyphrases.\n"
                    "- Naturally incorporate them into headings, subheadings, and body text.\n"
                    "- Ensure they appear multiple times but avoid overstuffing.\n"
                    "- Maintain natural Persian phrasing — do not force synonyms unnaturally.\n"
                    "- Continue using the primary keyword as usual alongside the synonyms.\n"
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
                    "### Important Rule:\n"
                    '- **Do NOT include any FAQs in the main HTML content.** All FAQ questions and answers must appear only in the JSON block under "faqs".\n\n'
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
                    "### HTML Guidelines:\n"
                    "- Follow the HTML formatting rules from the previous guidelines.\n"
                    '- **Do NOT include any FAQs in the main HTML content.** All FAQ questions and answers must appear only in the JSON block under "faqs".\n\n'
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
                    "You are an expert Persian SEO assistant and editor. "
                    "Your task is to improve an existing article using the feedback from Yoast SEO analysis.\n\n"
                    "### Yoast analysis fields:\n"
                    "- '_identifier': the issue type (e.g., 'sentenceBeginnings', 'subheadingsKeyword', 'metaDescription').\n"
                    "- 'text': human-readable description of the issue.\n"
                    "- 'rating': severity ('good', 'ok', 'bad').\n"
                    "- 'problemSentences': list of exact sentences that violate the rule (if available), "
                    "each entry containing 'fullSentence' and 'firstWord'.\n"
                    "For 'subheadingsKeyword', treat all <h2> and <h3> headings as problem sentences. "
                    "Rephrase only the sentences listed in 'problemSentences' minimally to fix the issue.\n\n"
                    "### Yoast quantitative guidance:\n"
                    "- **Keyword density:** 0.5%–3% of total words (adjust body text only).\n"
                    "- **Meta description:** 120–156 characters, must include the primary keyword.\n"
                    "- **Subheadings with keyword:** 30–75% of H2/H3 should include the primary keyword.\n"
                    "- **Consecutive sentences starting with the same word:** No more than 2 consecutive sentences starting with the same word.\n"
                    "- **Sentence length:** Prefer sentences under 20 words.\n"
                    "- **Transition words:** ≥30% of sentences.\n"
                    "- **Passive voice:** <10% of sentences.\n"
                    "- **Paragraph length:** ≤150 words per paragraph.\n\n"
                    "### Instructions for improvement:\n"
                    "- Apply the **smallest possible edits** to resolve each Yoast issue.\n"
                    "- Do NOT rewrite large portions unless absolutely necessary.\n"
                    "- Preserve previously correct optimizations.\n"
                    "- Only modify sections directly related to the issues provided.\n"
                    "- When adjusting ranges (keyword density, subheading coverage), move slightly toward the target without overcompensating.\n"
                    "- Keep tone, topic, structure, headings, and tags/categories unchanged unless absolutely necessary.\n"
                    "- Track adjustments to avoid repeatedly editing the same sentence or heading.\n"
                    "- Attempt only **one adjustment cycle per issue** per pass.\n\n"
                    "### Actionable fixes for common Yoast issues:\n"
                    "- **Consecutive sentence beginnings:** Rephrase only the 2nd and 3rd sentences in sequences of 3+ using slight restructuring. Fully rewrite only if needed.\n"
                    "- **Keyword density:** Adjust only body text, not subheadings. Add or remove minimal occurrences of the primary keyword **or any of its synonyms** (from the 'synonyms' list in the JSON) to reach 0.5–3%. Avoid overcorrection.\n"
                    "- **SubheadingsKeyword:** For each <h2>/<h3> heading listed in 'problemSentences':\n"
                    "  • Check if the primary keyword or any of its synonyms are present.\n"
                    "  • If missing, **first try to insert a synonym naturally** in the heading. Only use the primary keyword if no suitable synonym fits.\n"
                    "  • If the heading contains too many occurrences of the keyword or synonyms, remove extras.\n"
                    "  • Apply minimal edits but **ensure that after editing Yoast would no longer mark it as a problem**.\n"
                    "- **Meta description:** Only adjust if Yoast flagged it as too short or too long. If flagged, adjust to 120–156 characters including the primary keyword naturally. Do not modify otherwise.\n"
                    "- **Sentence length:** Split sentences >20 words while keeping meaning.\n"
                    "- **Transition words / readability:** Add in underrepresented sentences.\n"
                    "- **Passive voice:** Rewrite to active where necessary.\n"
                    "- **Paragraphs too long:** Split >150 words into shorter paragraphs.\n"
                    "- **Internal links:** Use provided related articles (title, first_paragraphs, categories, tags) naturally. Limit 2–5 internal links per article.\n\n"
                    "### Conflict resolution priority:\n"
                    "- If subheadingsKeyword and keyword density conflict, prioritize maintaining subheading coverage.\n"
                    "- Adjust body text first for density before touching subheadings.\n\n"
                    "### Context:\n"
                    f"Title: {title}\n"
                    f"Primary Keyword/Keyphrase: {self.keyword}\n"
                    f"Synonyms: {self.json_output.get('synonyms', [])}\n\n"
                    f"Yoast analysis feedback:\n{yoast_info}\n\n"
                    "Full article HTML:\n"
                    f"{self.html_output}\n\n"
                    "Original JSON data (for reference):\n"
                    f"{self.json_output}\n\n"
                    "### Output requirements:\n"
                    "1. Return **improved article as clean HTML** only — no <html>, <head>, or <body> tags.\n"
                    "2. Wrap content in a single <div lang='fa' dir='rtl'> ... </div>\n"
                    "3. Use only structural tags (<h1>, <h2>, <h3>, <p>, <ul>, <ol>, <a>, <img>, etc.)\n"
                    "4. Do NOT add inline styles, CSS classes, or custom attributes.\n"
                    "5. Append a **valid JSON block** after the HTML with:\n"
                    '   - "title": improved SEO title (if relevant)\n'
                    '   - "categories": [list of relevant categories]\n'
                    '   - "tags": [list of 5 relevant tags]\n'
                    '   - "faqs": [3 objects {"question","answer"}]\n'
                    '   - "meta": meta description (≤160 chars, must include the Primary Keyword, only edit if flagged by Yoast)\n'
                    '   - "sources": list of objects with "title" and "link" for every source referenced\n'
                    '   - "synonyms": [list of relevant synonyms]\n\n'
                    "### Self-check:\n"
                    "- Verify each Yoast issue is actually resolved.\n"
                    "- Consecutive sentence beginnings ≤2 per sequence.\n"
                    "- Keyword density 0.5–3%, using primary keyword and/or synonyms; subheadingsKeyword fixed as per problemSentences.\n"
                    "- Meta description only changed if flagged, otherwise unchanged.\n"
                    "- Sentence lengths, transition words, passive voice, paragraph lengths within thresholds.\n"
                    "- Only return final HTML and JSON when all adjustments are within range.\n\n"
                    "Ensure format is identical to original generation for correct parsing."
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
                "Only change the missing or invalid parts; do not alter correct sections.\n"
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
            "synonyms": [],
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
        "synonyms": list,
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

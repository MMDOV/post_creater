from openai import AsyncOpenAI
import re
import json
import aiohttp


class OpenAi:
    def __init__(
        self,
        openai_api_key: str,
        keyword: str,
        categories: list[str],
        tags: list[str],
        related_articles: list[dict],
        top_results_info: list[dict],
    ) -> None:
        self.client = AsyncOpenAI(api_key=openai_api_key)
        self.keyword = keyword
        self.categories = categories
        self.tags = tags
        self.related_articles = related_articles
        self.top_results_info = top_results_info

    async def get_text_response(self) -> tuple[dict, str]:
        # TODO: still need to figure out how are we adding the pillar page
        # TODO: test the new prompt and see if it works things added are:
        ## top result info
        ## search phrases are now better
        ## should include summery
        ## should not have custom styling
        ## the title and faq should be part of the json and usable
        ## should have acceptable images

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
                        <placeholder-img>short descriptive sentence of the image to search for in english</placeholder-img>
                        The description must always include the Primary Keyword (or part of it) to ensure relevance to the article topic.
                        notice that unlike the post itself the description of the image should be in english
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

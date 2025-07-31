from openai import OpenAI
import base64
import re


class OpenAi:
    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(api_key=api_key)

    def get_text_response(self, keyword: str) -> str:
        response = self.client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Return the result as clean HTML, but do NOT include <html>, <head>, or <body> tags. "
                        "Wrap the entire content in a <div> with lang='fa' and dir='rtl'. "
                        "Style the content for good readability with appropriate spacing and formatting for Persian. "
                        "Only return valid HTML. No code blocks or markdown formatting."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
                        Create a 1500-word SEO-optimized article focused on Primary Keyword “{keyword}”. Structure the article with 12 headings that integrate the primary keyword naturally in the first 100 words, 2–3 subheadings, and the conclusion. Include a meta description (under 160 characters) containing Primary Keyword. Use simple language, short paragraphs (≤3 lines), and ensure readability (Flesch-Kincaid Grade 8–9).  

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

    def get_image_response(self, prompt: str) -> str:
        image_prompt = f"""
        Generate an image that describes the text below best:\n\n
        {prompt}
        """

        result = self.client.images.generate(
            model="dall-e-3", prompt=image_prompt, response_format="b64_json"
        )

        if result:
            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            # Save the image to a file
            with open(f"{prompt.replace(' ', '_')}.png", "wb") as f:
                f.write(image_bytes)

        return f"{prompt}.png"

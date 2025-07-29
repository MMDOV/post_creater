from openai import OpenAI
import base64
import re


class OpenAi:
    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(api_key=api_key)

    def get_text_response(self, prompt: str) -> str:
        response = self.client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "developer",
                    "content": (
                        "Given any prompt, generate a Persian essay suitable for publishing on a blog. "
                        "The essay should be medium length — not too short, not too long. "
                        "Return the result as clean HTML, but do NOT include <html>, <head>, or <body> tags. "
                        "Wrap the entire content in a <div> with lang='fa' and dir='rtl'. "
                        "Style the content for good readability with appropriate spacing and formatting for Persian. "
                        "Only return valid HTML. No code blocks or markdown formatting."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        result = extract_code_block(response.output_text)
        return result

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


def extract_code_block(text):
    match = re.search(r"```(?:html)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text.strip()

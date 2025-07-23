from openai import OpenAI
import base64


class OpenAi:
    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(api_key=api_key)

    def get_text_response(self, prompt: str) -> str:
        response = self.client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "developer",
                    "content": "Whatever prompt you are given. give back an essay to post on a blog or website about the given prompt",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.output_text

    def get_image_response(self, prompt: str) -> str:
        prompt = f"""
        Generate an image that describes the text below best:\n\n
        {prompt}
        """

        result = self.client.images.generate(model="gpt-image-1", prompt=prompt)

        if result:
            image_base64 = result.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)

            # Save the image to a file
            with open(f"images/{prompt}.png", "wb") as f:
                f.write(image_bytes)

        return f"images/{prompt}.png"

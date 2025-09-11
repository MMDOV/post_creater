import aiohttp
import os
import json


class WordPress:
    def __init__(self, username: str, password: str, site_url: str) -> None:
        self.username = username
        self.password = password
        self.site_url = site_url

    # FIX: meta description of images should be included
    # FIX: the location shit that gpt gave you does nothing
    async def upload_image(self, image_path: str):
        print(f"uploading image {image_path}")
        image_filename = os.path.basename(image_path)
        url = f"{self.site_url}/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": f"attachment; filename={image_filename}",
            "Content-Type": "image/png",
        }

        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        ) as session:
            with open(image_path, "rb") as f:
                data = f.read()

            async with session.post(url, headers=headers, data=data) as resp:
                if resp.status != 201:
                    body = await resp.text()
                    raise Exception(f"Failed to upload image: {resp.status}, {body}")

                try:
                    result = await resp.json()
                    return result["source_url"]
                except aiohttp.ContentTypeError:
                    body = await resp.text()
                    raise Exception(f"Unexpected response type: {resp.status}, {body}")
                except json.JSONDecodeError:
                    location = resp.headers.get("Location")
                    if location:
                        return location
                    raise Exception(
                        "Upload succeeded but no JSON and no location header"
                    )

    # FIX: move metadescription to the appropreate place (find the place first)
    # TODO: add schema to the post
    # TODO: test faq to see if it works you might need to change it to the other version
    async def create_post(
        self,
        title: str,
        content: str,
        faqs: list[dict],
        categories: list = [],
        tags: list = [],
    ):
        faq_block = ""
        for faq in faqs:
            question = str(faq.get("question"))
            answer = str(faq.get("answer"))
            faq_template = '<!-- wp:faq/question {"question":"<question>"} -->\n<p><answer></p>\n<!-- /wp:faq/question -->'.replace(
                "<question>", question
            ).replace("<answer>", answer)
            faq_block = faq_block + "\n\n" + faq_template
        post_data = {
            "title": title,
            "content": content + faq_block,
            "status": "draft",
            "categories": categories,
            "tags": tags,
        }

        url = f"{self.site_url}/wp-json/wp/v2/posts"
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        ) as session:
            async with session.post(url, json=post_data) as resp:
                if resp.status != 201:
                    raise Exception(
                        f"Failed to create post: {resp.status}, {await resp.text()}"
                    )
                result = await resp.json()
                print("Post created:", result["link"])

    async def get_categories(self):
        params = {"per_page": 100}
        url = f"{self.site_url}/wp-json/wp/v2/categories"
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        ) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(
                        f"Failed to get categories: {resp.status}, {await resp.text()}"
                    )
                result = await resp.json()
                categories = {cat["id"]: cat["name"] for cat in result}
                return categories

    async def get_tags(self):
        params = {"per_page": 100}
        url = f"{self.site_url}/wp-json/wp/v2/tags"
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        ) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(
                        f"Failed to get tags: {resp.status}, {await resp.text()}"
                    )
                result = await resp.json()
                tags = {tag["id"]: tag["name"] for tag in result}
                return tags

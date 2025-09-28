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

    def _build_post_payload(
        self,
        title: str,
        content: str,
        meta: str,
        faqs: list[dict],
        article_sources: list[dict] = [],
        categories: list = [],
        tags: list = [],
        status: str = "draft",
    ) -> dict:
        """Return a dict ready for either create_post or yoast-preview render."""

        meta_block = f'<meta name="description" content="{meta}" />'

        faq_items = (
            {
                f"item-{i}": {
                    "faq_question": str(faq.get("question")),
                    "faq_answer": str(faq.get("answer")),
                }
                for i, faq in enumerate(faqs)
            }
            if faqs
            else {}
        )

        sources = (
            (
                "<ul>"
                + "".join(
                    f'<li><a href="{src["link"]}">{src["title"]}</a></li>'
                    for src in article_sources
                )
                + "</ul>"
            )
            if article_sources
            else ""
        )

        payload = {
            "title": title,
            "content": content + "\n\n" + meta_block,
            "meta": {
                "faq_items_v2": faq_items,
                "article_sources": sources,
            },
            "categories": categories,
            "tags": tags,
        }
        if status is not None:
            payload["status"] = status
        return payload

    # TODO: test and see if metadescription works
    async def create_post(
        self,
        title: str,
        content: str,
        meta: str,
        faqs: list[dict],
        article_sources: list[dict] = [],
        categories: list = [],
        tags: list = [],
        status: str = "draft",
    ):
        post_data = self._build_post_payload(
            title, content, meta, faqs, article_sources, categories, tags, status
        )
        url = f"{self.site_url}wp-json/wp/v2/posts"
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
                return result["id"]

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

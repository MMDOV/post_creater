import aiohttp
from html import unescape
from bs4 import BeautifulSoup
from typing import Any


class WordPressClient:
    def __init__(self, username: str, password: str, site_url: str) -> None:
        self.username: str = username
        self.password: str = password
        self.site_url: str = site_url

    async def _get_post_info(
        self,
        post_id: int = -1,
        post_slug: str = "",
        fields: list = ["title", "first_paragraphs", "categories", "tags", "url"],
    ) -> dict[str, str]:
        """
        Fetch a WordPress post and extract desired fields.
        Returns a dict with requested fields.
        """

        endpoint: str = f"{self.site_url}/wp-json/wp/v2/posts"
        if post_id != -1:
            url: str = f"{endpoint}/{post_id}"
        elif post_slug != "":
            url = f"{endpoint}?slug={post_slug}"
        else:
            raise ValueError("Must provide post_id or post_slug")

        auth = (
            aiohttp.BasicAuth(self.username, self.password)
            if self.username and self.password
            else None
        )

        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                data = await resp.json()
                if isinstance(data, list):
                    data = data[0]

        result: dict[str, Any] = {}
        if "title" in fields:
            title = BeautifulSoup(
                data.get("title", {}).get("rendered", ""), "html.parser"
            ).get_text()
            result["title"] = unescape(title).strip()

        if "first_paragraphs" in fields:
            content_html = data.get("content", {}).get("rendered", "")
            content_text = BeautifulSoup(content_html, "html.parser").get_text().strip()
            paragraphs = [p.strip() for p in content_text.split("\n") if p.strip()]
            summary_text = ""

            if paragraphs and paragraphs[0] == result["title"]:
                paragraphs = paragraphs[1:]

            if paragraphs:
                summary_text = " ".join(paragraphs[:2])

            result["first_paragraphs"] = unescape(summary_text)

        if "categories" in (fields or []):
            cat_map = await self.get_categories()
            result["categories"] = [
                cat_map.get(cat_id, str(cat_id))
                for cat_id in data.get("categories", [])
            ]

        if "tags" in (fields or []):
            tag_map = await self.get_tags()
            result["tags"] = [
                tag_map.get(tag_id, str(tag_id)) for tag_id in data.get("tags", [])
            ]

        if "url" in fields:
            result["url"] = data.get("link", "")

        return result

    async def get_posts_info(self, data_list: list[str | int]) -> list[dict[str, str]]:
        return [
            await self._get_post_info(post_id=item)
            if isinstance(item, int)
            else await self._get_post_info(post_slug=item)
            for item in data_list
        ]

    def _build_post_payload(
        self,
        keyword: str,
        title: str,
        content: str,
        slug: str,
        meta: str,
        faqs: list[dict],
        article_sources: list[dict] = [],
        categories: list = [],
        tags: list = [],
        status: str = "draft",
    ) -> dict[str, Any]:
        """Return a dict ready for either create_post or yoast-preview render."""

        faq_items: dict[str, dict[str, str]] = (
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

        sources: str = (
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

        payload: dict[str, Any] = {
            "title": title,
            "content": content,
            "slug": slug,
            "meta": {
                "faq_items_v2": faq_items,
                "article_sources": sources,
            },
            "categories": categories,
            "tags": tags,
            "yoast_description": meta,
            "yoast_keyword": keyword,
            "yoast_title": title,
        }
        if status is not None:
            payload["status"] = status
        return payload

    async def create_post(
        self,
        keyword: str,
        title: str,
        content: str,
        slug: str,
        meta: str,
        faqs: list[dict],
        article_sources: list[dict] = [],
        categories: list = [],
        tags: list = [],
        status: str = "draft",
    ) -> int:
        post_data: dict[str, Any] = self._build_post_payload(
            keyword,
            title,
            content,
            slug,
            meta,
            faqs,
            article_sources,
            categories,
            tags,
            status,
        )
        url: str = f"{self.site_url}wp-json/wp/v2/posts"
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

    async def get_categories(self) -> dict[int, str]:
        params: dict[str, int] = {"per_page": 100}
        url: str = f"{self.site_url}/wp-json/wp/v2/categories"
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        ) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(
                        f"Failed to get categories: {resp.status}, {await resp.text()}"
                    )
                result = await resp.json()
                return {category["id"]: category["name"] for category in result}

    async def get_tags(self) -> dict[int, str]:
        params: dict[str, int] = {"per_page": 100}
        url: str = f"{self.site_url}/wp-json/wp/v2/tags"
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        ) as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    raise Exception(
                        f"Failed to get tags: {resp.status}, {await resp.text()}"
                    )
                result = await resp.json()
                return {tag["id"]: tag["name"] for tag in result}

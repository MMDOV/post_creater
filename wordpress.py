import aiohttp
import json
from html import unescape
from bs4 import BeautifulSoup
from typing import Any
from urllib.parse import urlparse
from models import PostData


class WordPressClient:
    def __init__(self, username: str, password: str, site_url: str) -> None:
        self.username: str = username
        self.password: str = password
        self.site_url: str = site_url

    def _is_url(self, item: str) -> bool:
        try:
            p = urlparse(item)
            return p.scheme in ("http", "https") and p.netloc != ""
        except Exception:
            return False

    async def _resolve_page_hierarchy(self, url: str, session) -> dict[str, Any]:
        path: str = urlparse(url).path.strip("/")
        segments: list[str] = path.split("/")
        if not segments:
            raise ValueError("URL contains no valid slugs")

        parent_id = 0
        page: dict[str, Any] = {}

        for segment in segments:
            api: str = (
                f"{self.site_url}/wp-json/wp/v2/pages?slug={segment}&parent={parent_id}"
            )

            async with session.get(api) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if not data:
                    raise ValueError(
                        f"Could not resolve segment '{segment}' under parent '{parent_id}'"
                    )

                page = data[0]
                parent_id = page["id"]

        return page

    async def _resolve_post_or_page(
        self, *, post_id: int, post_slug: str, post_url: str, session
    ) -> dict[str, Any]:
        if post_id != -1:
            for ep in [
                f"{self.site_url}/wp-json/wp/v2/pages/{post_id}",
                f"{self.site_url}/wp-json/wp/v2/posts/{post_id}",
            ]:
                async with session.get(ep) as resp:
                    if resp.status == 200:
                        return await resp.json()

            raise ValueError(f"No post/page found for ID={post_id}")

        if post_url:
            try:
                return await self._resolve_page_hierarchy(post_url, session)
            except Exception:
                pass

            slug = urlparse(post_url).path.strip("/").split("/")[-1]
            post_slug = slug

        if post_slug:
            async with session.get(
                f"{self.site_url}/wp-json/wp/v2/pages?slug={post_slug}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        return data[0]

            async with session.get(
                f"{self.site_url}/wp-json/wp/v2/posts?slug={post_slug}"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data:
                        return data[0]

            raise ValueError(f"No post/page found for slug='{post_slug}'")

        raise ValueError("Must provide post_id, post_slug, or post_url")

    async def _get_post_info(
        self,
        post_id: int = -1,
        post_slug: str = "",
        post_url: str = "",
        fields: list = ["title", "first_paragraphs", "categories", "tags", "url"],
    ) -> dict[str, Any]:
        auth = (
            aiohttp.BasicAuth(self.username, self.password)
            if self.username and self.password
            else None
        )

        async with aiohttp.ClientSession(auth=auth) as session:
            wp_obj: dict[str, Any] = await self._resolve_post_or_page(
                post_id=post_id, post_slug=post_slug, post_url=post_url, session=session
            )
            result: dict[str, Any] = {}

            if "title" in fields:
                title: str = BeautifulSoup(
                    wp_obj.get("title", {}).get("rendered", ""), "html.parser"
                ).get_text()
                result["title"] = unescape(title).strip()

            if "first_paragraphs" in fields:
                content_html = wp_obj.get("content", {}).get("rendered", "")
                content_text = (
                    BeautifulSoup(content_html, "html.parser").get_text().strip()
                )
                paragraphs: list[str] = [
                    p.strip() for p in content_text.split("\n") if p.strip()
                ]
                summary = ""

                if paragraphs and paragraphs[0] == result["title"]:
                    paragraphs = paragraphs[1:]

                if paragraphs:
                    summary = " ".join(paragraphs[:2])

                result["first_paragraphs"] = unescape(summary)

            if "categories" in fields:
                cat_map: dict[int, str] = await self.get_categories()
                result["categories"] = [
                    cat_map.get(cid, str(cid)) for cid in wp_obj.get("categories", [])
                ]

            if "tags" in fields:
                tag_map: dict[int, str] = await self.get_tags()
                result["tags"] = [
                    tag_map.get(tid, str(tid)) for tid in wp_obj.get("tags", [])
                ]

            if "url" in fields:
                result["url"] = wp_obj.get("link", "")

            return result

    async def get_posts_info(self, data_list: list[str | int]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for item in data_list:
            if isinstance(item, int):
                info: dict[str, Any] = await self._get_post_info(post_id=item)

            elif isinstance(item, str) and self._is_url(item):
                info = await self._get_post_info(post_url=item)

            else:
                info = await self._get_post_info(post_slug=item)

            results.append(info)

        return results

    def _build_post_payload(
        self,
        post_data: PostData,
        status: str = "draft",
    ) -> dict[str, Any]:
        """Return a dict ready for either create_post or yoast-preview render."""

        faq_items: dict[str, dict[str, str]] = (
            {
                f"item-{i}": {
                    "faq_question": str(faq.get("question")),
                    "faq_answer": str(faq.get("answer")),
                }
                for i, faq in enumerate(post_data.json.faqs)
            }
            if post_data.json.faqs
            else {}
        )

        sources: str = (
            (
                "<ul>"
                + "".join(
                    f'<li><a href="{src["link"]}">{src["title"]}</a></li>'
                    for src in post_data.json.sources
                )
                + "</ul>"
            )
            if post_data.json.sources
            else ""
        )

        print("synonyms: ", post_data.json.synonyms)
        payload: dict[str, Any] = {
            "title": post_data.json.post_title,
            "content": post_data.html,
            "slug": post_data.json.slug,
            "meta": {
                "faq_items_v2": faq_items,
                "article_sources": sources,
            },
            "categories": post_data.json.picked_category_ids,
            "tags": post_data.json.picked_tag_ids,
            "yoast_description": post_data.json.meta,
            "yoast_keyword": post_data.keyphrase,
            "yoast_title": post_data.json.post_title,
            "yoast_synonyms": post_data.json.synonyms,
        }
        if status is not None:
            payload["status"] = status
        return payload

    async def create_post(
        self,
        post_data: PostData,
        status: str = "draft",
    ) -> int:
        post: dict[str, Any] = self._build_post_payload(
            post_data,
            status,
        )
        url: str = f"{self.site_url}wp-json/wp/v2/posts"
        async with aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password)
        ) as session:
            async with session.post(url, json=post) as resp:
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

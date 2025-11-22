from dataclasses import dataclass, field
from typing import List, Dict
from config import get_from_env


@dataclass
class SiteInfo:
    all_tags: Dict[int, str] = field(default_factory=dict)
    all_categories: Dict[int, str] = field(default_factory=dict)
    site_url: str = field(default_factory=lambda: get_from_env("SITE_URL"))
    wp_api_user: str = field(default_factory=lambda: get_from_env("WP_API_USER"))
    wp_api_pass: str = field(default_factory=lambda: get_from_env("WP_API_PASS"))


@dataclass
class PostJsonData:
    picked_category_ids: List[int] = field(default_factory=list)
    picked_tag_ids: List[int] = field(default_factory=list)
    faqs: List[Dict[str, str]] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    post_title: str = ""
    meta: str = ""
    slug: str = ""
    conversation_id: str = ""

    @classmethod
    def from_json(cls, json: dict, site_info: SiteInfo) -> "PostJsonData":
        picked_category_ids = [
            cid
            for cid, name in site_info.all_categories.items()
            if name in json["categories"]
        ]
        picked_tag_ids = [
            cid for cid, name in site_info.all_tags.items() if name in json["tags"]
        ]
        return cls(
            picked_category_ids=picked_category_ids,
            picked_tag_ids=picked_tag_ids,
            faqs=json["faqs"],
            post_title=json["title"],
            meta=json["meta"],
            slug=json["slug"],
            sources=json["sources"],
            conversation_id=json["conversation_id"],
        )


@dataclass
class PostData:
    keyphrase: str = field(default_factory=lambda: get_from_env("KEYPHRASE"))
    html: str = field(default_factory=str)
    json: PostJsonData = field(default_factory=PostJsonData)

from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import aiohttp
import trafilatura
from readability import Document


class Scrape:
    def __init__(
        self,
        google_api_key: str = "",
        google_cse_id: str = "",
    ) -> None:
        self.google_api_key: str = google_api_key
        self.google_cse_id: str = google_cse_id
        self.google_search_url: str = "https://www.googleapis.com/customsearch/v1"

    async def get_top_results_info(self, query: str) -> list[dict[str, str]]:
        if not self.google_cse_id or not self.google_api_key:
            raise Exception("google cse id and api key are needed for this action!")
        search_results = await self._google_search(query)
        data = []
        if search_results:
            for result in search_results:
                if len(data) >= 5:
                    break
                response = trafilatura.fetch_url(result)
                if not response:
                    print(f"[-] No response for url: {result}")
                    continue
                print(response[:500])
                response = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", response)
                replacement_character_ratio = response.count("\ufffd") / len(response)
                if replacement_character_ratio > 0.01:  # e.g., >1% replacement chars
                    print(f"[!] Skipping replacement garbled page: {result}")
                    continue

                print(
                    f"[+] Response type: {type(response)} | length: {len(response)} | url: {result}"
                )

                try:
                    doc = Document(response)
                    summary = doc.summary()
                    title = doc.title()

                    soup = BeautifulSoup(summary, "lxml")
                    plain_text = trafilatura.extract(response)

                    info = {
                        "main_title": str(title),
                        "headings": str(soup.find_all(["h1", "h2", "h3"])),
                        "word_count": str(len(plain_text.split()) if plain_text else 0),
                        "heading_count": str(len(soup.find_all(["h1", "h2", "h3"]))),
                        "image_count": str(len(soup.find_all("img"))),
                        "link_count": str(len(soup.find_all("a"))),
                        "audio_count": str(len(soup.find_all("audio"))),
                        "video_count": str(len(soup.find_all(["video", "iframe"]))),
                        "article_body": str(summary),
                    }

                    data.append(info)

                except Exception as e:
                    print(f"[ERROR] Failed to process {result}: {e}")
                    continue
        else:
            raise Exception("no search results found")
        print(f"data len: {len(data)}")
        return data

    async def _google_search(self, query: str, num_results=5) -> list[str]:
        print("searching google")
        params = {
            "q": query,
            "cx": self.google_cse_id,
            "key": self.google_api_key,
            "num": 10,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.google_search_url, params=params) as response:
                response.raise_for_status()
                results = await response.json()

        links = []
        for item in results.get("items", []):
            if len(links) >= num_results * 2:
                break
            netloc = urlparse(item["link"]).netloc
            if not netloc.endswith(".wikipedia.org"):
                links.append(item["link"])

        return links


async def is_valid_image(session, url: str) -> bool:
    try:
        async with session.head(url, allow_redirects=True) as resp:
            if resp.status == 200:
                content_type = resp.headers.get("Content-Type", "")
                return content_type.startswith("image/")
    except Exception as e:
        print(e)
        return False
    return False

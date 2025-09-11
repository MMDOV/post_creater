from bs4 import BeautifulSoup
import json
import aiohttp
import trafilatura
from readability import Document


class Scrape:
    def __init__(
        self,
        google_api_key: str = "",
        google_cse_id: str = "",
        pixabay_api_key: str = "",
        pexels_api_key: str = "",
    ) -> None:
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id
        self.google_search_url = "https://www.googleapis.com/customsearch/v1"
        self.pixabay_api_key = pixabay_api_key
        self.pexels_api_key = pexels_api_key

    # FIX: ignore wikipedia (and other sites if you can think of more)
    async def get_top_results_info(self, query: str) -> list[dict]:
        if not self.google_cse_id or not self.google_api_key:
            raise Exception("google cse id and api key are needed for this action!")
        search_results = await self._google_search(query)
        data = []
        if search_results:
            for result in search_results:
                response = trafilatura.fetch_url(result)
                if response:
                    doc = Document(response)
                    soup = BeautifulSoup(doc.summary(), "lxml")

                    plain_text = trafilatura.extract(response)
                    if plain_text:
                        word_count = len(plain_text.split())
                    else:
                        word_count = 0

                    headings = soup.find_all(
                        name=[
                            "h1",
                            "h2",
                            "h3",
                        ]
                    )
                    if headings:
                        heading_count = len(headings)
                    else:
                        heading_count = 0

                    images = soup.find_all(name="img")
                    if images:
                        image_count = len(images)
                    else:
                        image_count = 0

                    links = soup.find_all(name="a")
                    if links:
                        link_count = len(links)
                    else:
                        link_count = 0

                    audios = soup.find_all(name="audio")
                    if audios:
                        audio_count = len(audios)
                    else:
                        audio_count = 0

                    videos = soup.find_all(name=["video", "iframe"])
                    if videos:
                        video_count = len(videos)
                    else:
                        video_count = 0

                    info = {
                        "main_title": doc.title(),
                        "word_count": word_count,
                        "heading_count": heading_count,
                        "image_count": image_count,
                        "link_count": link_count,
                        "audio_count": audio_count,
                        "video_count": video_count,
                    }
                    data.append(info)
                else:
                    continue
        else:
            raise Exception("no search results found")
        print(data)
        return data

    async def _google_search(self, query: str, num_results=5) -> list[str]:
        print("searching google")
        params = {
            "q": query,
            "cx": self.google_cse_id,
            "key": self.google_api_key,
            "num": min(num_results, 10),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.google_search_url, params=params) as response:
                response.raise_for_status()
                results = await response.json()

        links = [item["link"] for item in results.get("items", [])]
        return links

    async def google_image_search(self, query: str, num_results: int = 1) -> list[dict]:
        if not self.google_cse_id or not self.google_api_key:
            raise Exception("google cse id and api key are needed for this action!")
        print("searching google")
        params = {
            "q": query,
            "cx": self.google_cse_id,
            "key": self.google_api_key,
            "searchType": "image",
            "num": min(num_results * 2, 10),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.google_search_url, params=params) as response:
                response.raise_for_status()
                results = await response.json()

        images = []
        async with aiohttp.ClientSession() as session:
            for item in results.get("items", []):
                link = item.get("link", "")
                if await is_valid_image(session, link) and str(link).endswith(
                    (".jpg", ".jpeg", ".png", ".webp")
                ):
                    images.append(link)
                if len(images) >= num_results:
                    break
        print(json.dumps(images, indent=4, sort_keys=True))

        return images

    async def pixabay_image_search(
        self,
        query: str,
        per_page: int = 3,
        lang: str = "en",
        image_type: str = "all",
        orientation: str = "all",
        category: str = "",
        min_width: int = 0,
        min_height: int = 0,
    ) -> list[str]:
        if not self.pixabay_api_key:
            raise Exception("pixabay api key is needed for this action!")
        print("Searching pixabay")
        pixabay_url = r"https://pixabay.com/api/"
        params = {
            "key": self.pixabay_api_key,
            "q": query,
            "per_page": per_page,
            "lang": lang,
            "image_type": image_type,
            "orientation": orientation,
            "min_height": min_height,
            "min_width": min_width,
        }
        if category:
            params.update({"category": category})

        async with aiohttp.ClientSession() as session:
            async with session.get(pixabay_url, params=params) as response:
                response.raise_for_status()
                results = await response.json()

        print(results)

        return [image["largeImageURL"] for image in results.get("hits")]

    async def pexels_image_search(
        self, query: str, per_page: int = 1, size: str = "large"
    ):
        if not self.pexels_api_key:
            raise Exception("pexels api key is needed for this action!")

        print("searching pexels")
        pexels_url = r"https://api.pexels.com/v1/search"
        headers = {"Authorization": self.pexels_api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "size": size,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                pexels_url, headers=headers, params=params
            ) as response:
                response.raise_for_status()
                results = await response.json()

        print(results)
        return [photo["src"]["original"] for photo in results["photos"]]


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

from bs4 import BeautifulSoup
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

                    summery: str = doc.summary()
                    info: dict[str, str] = {
                        "main_title": str(doc.title()),
                        "headings": str(headings),
                        "word_count": str(word_count),
                        "heading_count": str(heading_count),
                        "image_count": str(image_count),
                        "link_count": str(link_count),
                        "audio_count": str(audio_count),
                        "video_count": str(video_count),
                        "article_body": str(summery),
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
            "num": 10,
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(self.google_search_url, params=params) as response:
                response.raise_for_status()
                results = await response.json()

        links = []
        for item in results.get("items", []):
            if len(links) >= num_results:
                break
            if not item["link"].startswith("https://www.wikipedia.org/"):
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

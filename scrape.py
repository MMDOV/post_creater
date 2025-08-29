from bs4 import BeautifulSoup
import aiohttp
import trafilatura
from readability import Document


class Scrape:
    def __init__(self, google_api_key: str, google_cse_id: str, query: str) -> None:
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id
        self.query = query

    async def get_top_results_info(self) -> list[dict]:
        search_results = await self._google_search()
        data = []
        if search_results:
            for result in search_results:
                response = trafilatura.fetch_url(result)
                if response:
                    doc = Document(response)
                    soup = BeautifulSoup(doc.summary())

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
                        "body": doc.summary(html_partial=True),
                    }
                    data.append(info)
                else:
                    continue
        else:
            raise Exception("no search results found")
        return data

    async def _google_search(self, num_results=5) -> list[str]:
        print("searching google")
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": self.query,
            "cx": self.google_cse_id,
            "key": self.google_api_key,
            "num": min(num_results, 10),
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params) as response:
                response.raise_for_status()
                results = await response.json()

        links = [item["link"] for item in results.get("items", [])]
        return links

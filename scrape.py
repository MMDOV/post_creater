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

                    # TODO: add voice (if it has voice file or not)
                    ## also add video count
                    heading_count = len(
                        soup.find_all(
                            name=[
                                "h1",
                                "h2",
                                "h3",
                            ]
                        )
                    )
                    image_count = len(soup.find_all(name="img"))
                    link_count = len(soup.find_all(name="a"))
                    info = {
                        "heading": heading_count,
                        "image": image_count,
                        "link": link_count,
                        "body": doc.summary(),
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

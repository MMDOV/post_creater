import asyncio
import aiohttp
from dotenv import load_dotenv
import os

load_dotenv()

google_api = os.getenv("GOOGLE_API")
google_cse = os.getenv("GOOGLE_CSE")


class Scrape:
    def __init__(
        self,
        google_api_key: str,
        google_cse_id: str,
    ) -> None:
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id

    async def google_search(self, query, num_results=5) -> list[dict]:
        print("searching google")
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
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


async def main():
    scrape = Scrape(google_cse_id=google_cse, google_api_key=google_api)
    print(await scrape.google_search("سرماخوردگی"))


asyncio.run(main())

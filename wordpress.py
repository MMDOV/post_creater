import aiohttp
import os


class WordPress:
    def __init__(self, username: str, password: str, site_url: str) -> None:
        self.username = username
        self.password = password
        self.site_url = site_url

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
                    raise Exception(f"Failed to upload image: {resp.status}")
                result = await resp.json()
                return result["source_url"]

    async def create_post(self, title: str, content: str):
        post_data = {
            "title": title,
            "content": content,
            "status": "draft",
        }

        url = f"{self.site_url}/wp-json/wp/v2/posts"
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

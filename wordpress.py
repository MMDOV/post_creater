import requests
from requests.auth import HTTPBasicAuth


class WordPress:
    def __init__(self, username: str, password: str, site_url: str) -> None:
        self.username = username
        self.password = password
        self.site_url = site_url

    def upload_image(self, image_path: str):
        image_filename = image_path.split("/")[-1]

        with open(image_path, "rb") as img:
            media_headers = {
                "Content-Disposition": f"attachment; filename={image_filename}",
                "Content-Type": "image/png",
            }
            media_response = requests.post(
                f"{self.site_url}/wp-json/wp/v2/media",
                headers=media_headers,
                auth=HTTPBasicAuth(self.username, self.password),
                data=img,
            )

        media_response.raise_for_status()
        media_id = media_response.json()["id"]
        image_url = media_response.json()["source_url"]
        return media_id, image_url

    def create_post(self, title: str, content: str, media_id: str, image_url: str):
        post_data = {
            "title": title,
            "content": f'<img src="{image_url}" alt="AI-generated image" /><p>{content}</p>',
            "status": "publish",
            "featured_media": media_id,
        }

        post_response = requests.post(
            f"{self.site_url}/wp-json/wp/v2/posts",
            auth=HTTPBasicAuth(self.username, self.password),
            json=post_data,
        )

        post_response.raise_for_status()
        print("Post created:", post_response.json()["link"])

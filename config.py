import os
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

api_key: str = os.getenv("OPENAI_API_KEY", "")
google_api: str = os.getenv("GOOGLE_API", "")
google_cse: str = os.getenv("GOOGLE_CSE", "")
ids_str = os.getenv("RELATED_ARTICLE_IDS", "")
related_article_data: list[int | str] = [
    int(x) if x.isdigit() else str(x) for x in ids_str.split(",") if x
]


def get_from_env(var_name: str, default: str = "") -> str:
    return os.getenv(var_name, default)


def validate_environment(site_info, post_info):
    missing: list[str] = []
    if not api_key:
        missing.append("API_KEY")
    if not site_info.wp_api_user:
        missing.append("USERNAME")
    if not site_info.wp_api_pass:
        missing.append("PASSWORD")
    if not site_info.site_url:
        missing.append("SITE_URL")
    if not post_info.keyphrase:
        missing.append("KEYPHRASE")
    if missing:
        logging.error(
            f"Missing required environment variables: {', '.join(missing)}",
            exc_info=True,
        )
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


# logging setup
log_file = f"wp_poster_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.CRITICAL)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

import aiofiles
import json
from typing import Any


async def read_json_file(filename: str) -> Any:
    async with aiofiles.open(filename, "r", encoding="utf-8") as f:
        return json.loads(await f.read())


async def read_text_file(filename: str) -> str:
    async with aiofiles.open(filename, "r", encoding="utf-8") as f:
        return await f.read()


async def save_to_file(filename: str, data: Any) -> None:
    async with aiofiles.open(filename, "w", encoding="utf-8") as f:
        await f.write(data)

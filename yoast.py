import subprocess
import re
import json
from typing import Any, Pattern

TAG_PATTERN: Pattern = re.compile(r"<(h[1-6]|p|li)>(.*?)</\1>", re.DOTALL)


class Yoast:
    def __init__(self, filters: list[str]) -> None:
        self.filters: list[str] = filters
        self._analysis: list[dict[str, Any]] = []

    def analyze(
        self,
        keyword: str,
        synonyms: str,
        title: str,
        meta: str,
        slug: str,
        text: str,
        permalink: str,
        locale: str = "fa",
    ) -> None | str:
        self._analysis = []
        self.text: str = text
        input_data: dict[str, Any] = {
            "keyword": keyword,
            "synonyms": synonyms,
            "title": title,
            "metaDescription": meta,
            "slug": slug,
            "text": text,
            "locale": locale,
            "permalink": permalink,
        }
        proc = subprocess.run(
            ["node", "yoast_seo.js"],
            input=json.dumps(input_data).encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if proc.returncode != 0:
            return proc.stderr.decode()
        else:
            output: dict[str, Any] = json.loads(proc.stdout.decode())
            for key, value in output.items():
                if key != "inclusiveLanguage":
                    for seo in value:
                        if (
                            seo["rating"] != "good"
                            and seo["_identifier"] not in self.filters
                        ):
                            self._analysis.append(seo)

    def get_analysis(
        self,
        keys: list[str] = [
            "_identifier",
            "text",
            "score",
            "rating",
            "problemSentences",
        ],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in self._analysis:
            marks: list = item.get("marks", [])

            item["problemSentences"] = extract_problem_sentences(self.text, marks)

            if item.get("_identifier") == "subheadingsKeyword":
                headings: list[str] = re.findall(
                    r"<h[23][^>]*>.*?</h[23]>", self.text, flags=re.DOTALL
                )
                subheading_problems: list[dict[str, str]] = []
                for heading in headings:
                    text_only: str = re.sub(r"<[^>]+>", "", heading).strip()
                    first_word: str = text_only.split()[0] if text_only else ""
                    subheading_problems.append(
                        {"fullSentence": heading, "firstWord": first_word}
                    )

                item["problemSentences"] = subheading_problems

            entry: dict[str, Any] = {key: item.get(key) for key in keys}
            result.append(entry)

        return result


def normalize_first_word(text: str) -> str:
    stripped_text: str = re.sub(r"^[\(\[\"\'«»،؛\-\–\—\u200c]+", "", text.strip())
    if not stripped_text:
        return ""
    return re.sub(
        r"[\.،,:;!؟\?]+$", "", stripped_text.split()[0] if stripped_text.split() else ""
    )


def extract_problem_sentences(text: str, marks: list[dict]) -> list[dict[str, str]]:
    blocks: list[str] = re.split(r"(?=<[^>]+>)", text)

    problem_list: list[dict[str, str]] = []

    for mark in marks:
        start: int = mark.get("_properties", {}).get("position", {}).get("startOffset")
        end: int = mark.get("_properties", {}).get("position", {}).get("endOffset")
        if start is None or end is None:
            continue

        char_pos = 0
        for block in blocks:
            block_end: int = char_pos + len(block)
            if char_pos <= start <= block_end or char_pos <= end <= block_end + 1:
                cleaned: str = block.strip()
                if cleaned:
                    text_only: str = re.sub(r"<[^>]+>", "", cleaned).strip()
                    first_word: str = text_only.split()[0] if text_only else ""
                    problem_list.append(
                        {"fullSentence": cleaned, "firstWord": first_word}
                    )
                break

            char_pos: int = block_end

    return problem_list

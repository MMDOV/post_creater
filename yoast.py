import subprocess
import re
import json


class Yoast:
    def __init__(self, filters):
        self.filters = filters
        self._analysis = []

    def analyze(
        self,
        keyword: str,
        title: str,
        meta: str,
        slug: str,
        text: str,
        locale: str = "fa",
    ):
        self._analysis = []
        self.text = text
        input_data = {
            "keyword": keyword,
            "title": title,
            "metaDescription": meta,
            "slug": slug,
            "text": text,
            "locale": locale,
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
            output = json.loads(proc.stdout.decode())
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
    ):
        result = []
        for item in self._analysis:
            marks = item.get("marks", [])

            # Extract normal problem sentences
            item["problemSentences"] = extract_problem_sentences(self.text, marks)

            # Special case: subheadingsKeyword
            if item.get("_identifier") == "subheadingsKeyword":
                # Find all H2 and H3 tags in the HTML
                headings = re.findall(
                    r"<h[23][^>]*>.*?</h[23]>", self.text, flags=re.DOTALL
                )
                subheading_problems = []
                for h in headings:
                    # Extract first word without HTML
                    text_only = re.sub(r"<[^>]+>", "", h).strip()
                    first_word = text_only.split()[0] if text_only else ""
                    subheading_problems.append(
                        {"fullSentence": h, "firstWord": first_word}
                    )

                # Replace problemSentences with these headings
                item["problemSentences"] = subheading_problems

            entry = {key: item.get(key) for key in keys}
            result.append(entry)

        return result


TAG_PATTERN = re.compile(r"<(h[1-6]|p|li)>(.*?)</\1>", re.DOTALL)


def normalize_first_word(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    text = re.sub(r"^[\(\[\"\'«»،؛\-\–\—\u200c]+", "", text)
    first = text.split()[0] if text.split() else ""
    first = re.sub(r"[\.،,:;!؟\?]+$", "", first)
    return first


def extract_problem_sentences(text: str, marks: list[dict]):
    # Split based on block-level HTML tags rather than punctuation
    # This keeps the tags in the sentence
    blocks = re.split(r"(?=<[^>]+>)", text)

    problem_list = []

    for mark in marks:
        start = mark.get("_properties", {}).get("position", {}).get("startOffset")
        end = mark.get("_properties", {}).get("position", {}).get("endOffset")
        if start is None or end is None:
            continue

        # Find which block overlaps the Yoast mark range
        char_pos = 0
        for block in blocks:
            block_end = char_pos + len(block)
            if char_pos <= start <= block_end or char_pos <= end <= block_end + 1:
                cleaned = block.strip()
                if cleaned:
                    # extract first word (preserve HTML)
                    text_only = re.sub(r"<[^>]+>", "", cleaned).strip()
                    first_word = text_only.split()[0] if text_only else ""
                    problem_list.append(
                        {"fullSentence": cleaned, "firstWord": first_word}
                    )
                break

            char_pos = block_end

    return problem_list

import subprocess
import json


class Yoast:
    # TODO: Add more filters
    # TODO: figure out a better layout for this class.
    def __init__(self, filters):
        self.filters = filters
        self._analysis = []

    def analyze(self, text: str, locale: str = "fa"):
        self._analysis = []
        input_data = {"text": text, "locale": locale}
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
        self, keys: list[str] = ["_identifier", "text", "score", "rating"]
    ):
        return [{key: item.get(key) for key in keys} for item in self._analysis]

import subprocess
import json


class Yoast:
    # TODO: Add more filters
    # TODO: figure out a better layout for this class.
    def __init__(self, filters):
        self.filters = filters
        self._analysis = []

    def analyze(self, text: str, locale: str = "fa"):
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
                if key not in self.filters:
                    for seo in value:
                        if (
                            seo["rating"] != "good"
                            and seo["_identifier"] not in self.filters
                        ):
                            self._analysis.append(seo)

    def get_full_analysis(self):
        return self._analysis

    def get_ratings(self):
        return [item.get("rating") for item in self._analysis]

    def get_texts(self):
        return [item.get("text") for item in self._analysis]

    def get_scores(self):
        return [item.get("score") for item in self._analysis]

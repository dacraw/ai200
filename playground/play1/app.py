import json
import os
import time

import requests
from bs4 import BeautifulSoup
from flask import Flask, request

app = Flask(__name__)

WIKI_BASE = "https://warhammer40k.fandom.com"
DOCS_DIR = "wiki_docs"


def scrape_page(page: str) -> str:
    response = requests.get(f"{WIKI_BASE}/wiki/{page}")
    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", class_="mw-parser-output")
    paragraphs = [p.get_text() for p in content.find_all("p")]
    return "\n".join(paragraphs)


def list_all_pages(limit: int):
    titles = []
    apcontinue = None
    while len(titles) < limit:
        params = {"action": "query", "list": "allpages", "aplimit": "max", "format": "json"}
        if apcontinue:
            params["apcontinue"] = apcontinue
        data = requests.get(f"{WIKI_BASE}/api.php", params=params).json()
        titles.extend(page["title"] for page in data["query"]["allpages"])
        apcontinue = data.get("continue", {}).get("apcontinue")
        if not apcontinue:
            break
    return titles[:limit]


@app.route("/process_warhammer_question", methods=["POST"])
def process_warhammer_question():
    question = request.get_json()["question"]

    return question


@app.route("/wiki/<page>", methods=["GET"])
def get_wiki_page(page: str):
    return scrape_page(page)


@app.route("/wiki/scrape_all", methods=["POST"])
def scrape_all_pages():
    limit = int(request.args.get("limit", 50))
    os.makedirs(DOCS_DIR, exist_ok=True)

    saved = []
    for title in list_all_pages(limit):
        page = title.replace(" ", "_").replace("/", "_")
        content = scrape_page(page)
        with open(os.path.join(DOCS_DIR, f"{page}.json"), "w", encoding="utf-8") as f:
            json.dump({"title": title, "content": content}, f, ensure_ascii=False, indent=2)
        saved.append(page)
        time.sleep(0.5)

    return {"saved": saved}

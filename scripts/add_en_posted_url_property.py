"""Legt die URL-Property "Richard LinkedIn Posted URL EN" in der Content-DB an.

Warum (27.08.2026): Das EN-Szenario 9517015 schrieb die EN-Feed-URL bisher in
"LinkedIn Post URL". Dort steht die URL des Quell-Posts, die
get_existing_post_urls() als Duplikat-Filter liest; nach dem EN-Post fiel die
Zeile aus dem Filter. Modul 6 des Szenarios schreibt jetzt in diese Property.

Idempotent: existiert die Property, passiert nichts.
"""
import os
import sys

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

NAME = "Richard LinkedIn Posted URL EN"


def main() -> None:
    token = os.environ["NOTION_TOKEN"]
    db = os.environ["NOTION_DB_ID"]
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
               "Content-Type": "application/json"}
    base = f"https://api.notion.com/v1/databases/{db}"
    props = requests.get(base, headers=headers, timeout=30).json()["properties"]
    if NAME in props:
        print(f"{NAME}: existiert bereits ({props[NAME]['type']})")
        return
    resp = requests.patch(base, headers=headers, json={"properties": {NAME: {"url": {}}}}, timeout=30)
    resp.raise_for_status()
    print(f"{NAME}: angelegt (url)")


if __name__ == "__main__":
    main()

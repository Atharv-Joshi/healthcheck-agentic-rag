"""Fetch public Contentstack docs (Markdown export) + check text from Postgres, chunk, embed into Chroma.
Usage: python -m scripts.ingest_docs [--refresh]   (pages are cached in data/docs_cache/)"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Check
from app.config import get_settings
from app.rag import store
from app.rag.chunking import chunk_markdown
from app.rag.store import COLLECTION, get_collection

BASE = "https://www.contentstack.com/docs/"
CACHE = Path(__file__).resolve().parents[1] / "data" / "docs_cache"
# path -> Healthcheck category the page mostly informs
PAGES = {
    "administration/about-single-sign-on-sso": "Security",
    "administration/multi-factor-authentication": "Security",
    "administration/security-configuration": "Security",
    "administration/create-custom-roles": "Security",
    "administration/about-administration-roles": "Security",
    "administration/organization-users": "Security",
    "administration/monitor-organization-activities-in-audit-log": "Security",
    "headless-cms/about-management-tokens": "Security",
    "headless-cms/about-delivery-tokens": "Security",
    "headless-cms/about-stack-roles": "Security",
    "headless-cms/about-webhooks": "Security",
    "administration/webhook-configuration": "Security",
    "headless-cms/about-content-modeling": "Content Modeling",
    "headless-cms/content-modeling-best-practices": "Content Modeling",
    "headless-cms/about-content-types": "Content Modeling",
    "headless-cms/limitations-of-content-types": "Content Modeling",
    "headless-cms/field-limitations": "Content Modeling",
    "headless-cms/global-fields-within-group-fields": "Content Modeling",
    "headless-cms/about-nested-reference-publishing": "Content Modeling",
    "headless-cms/about-assets": "Content",
    "headless-cms/file-size-limit": "Content",
    "headless-cms/asset-limitations": "Content",
    "headless-cms/entries-limitations": "Content",
    "headless-cms/about-publish-rules": "Content",
    "developers/apis/image-delivery-api": "Content",
    "developers/apis/image-delivery-api/automate-optimization": "Content",
    "developers/apis/image-delivery-api/control-quality": "Content",
    "developers/apis/image-delivery-api/convert-formats": "Content",
    "developers/apis/image-delivery-api/resize-images": "Content",
    "developers/apis/content-delivery-api/api-best-practices": "Content",
    "headless-cms/about-environments": "Other Configurations",
    "headless-cms/about-workflows": "Other Configurations",
    "headless-cms/about-workflow-stages": "Other Configurations",
    "headless-cms/about-languages": "Other Configurations",
    "headless-cms/about-fallback-languages": "Other Configurations",
    "headless-cms/about-releases": "Other Configurations",
    "developer-hub/app-development-best-practices": "Other Configurations",
}


def fetch(path: str, refresh: bool) -> dict | None:
    """Uses the official Markdown export of each docs page (listed in sitemap-md.xml)."""
    f = CACHE / (path.replace("/", "__") + ".json")
    if f.exists() and not refresh:
        return json.loads(f.read_text())
    r = httpx.get(f"{BASE}{path}.md", headers={"User-Agent": "healthcheck-qa-portfolio-bot/0.1"},
                  follow_redirects=True, timeout=30)
    if r.status_code != 200:
        print(f"  skip {path}: HTTP {r.status_code}")
        return None
    body = r.text
    title = path
    if body.startswith("---"):
        _, front, body = body.split("---", 2)
        m = re.search(r'^title:\s*"?(.+?)"?\s*$', front, re.M)
        title = m.group(1) if m else path
    page = {"path": path, "url": BASE + path, "title": title, "text": body.strip()}
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(page))
    time.sleep(0.5)  # be polite
    return page


def main() -> None:
    refresh = "--refresh" in sys.argv
    ids, docs, metas = [], [], []

    def add(text, source, title, category):
        for i, c in enumerate(chunk_markdown(text, title)):
            ids.append(hashlib.md5(f"{source}#{i}".encode()).hexdigest())
            docs.append(c)
            metas.append({"source": source, "title": title, "category": category})

    for path, category in PAGES.items():
        print("fetching", path)
        page = fetch(path, refresh)
        if page:
            add(page["text"], page["url"], page["title"], category)

    with SessionLocal() as db:
        for c in db.scalars(select(Check)):
            add(f"{c.name}. {c.description} Recommendation: {c.recommendation_text}",
                f"healthcheck-check:{c.name}", c.name, c.category)

    import chromadb
    client = chromadb.PersistentClient(path=str(get_settings().chroma_dir))
    if COLLECTION in [c if isinstance(c, str) else c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    store.reset()
    col = get_collection()
    for i in range(0, len(ids), 128):
        col.add(ids=ids[i:i+128], documents=docs[i:i+128], metadatas=metas[i:i+128])
    print(f"Indexed {len(ids)} chunks from {len(set(m['source'] for m in metas))} sources")


if __name__ == "__main__":
    main()

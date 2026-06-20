import json
import re
from pathlib import Path
from scraper.scraper import ask_google_ai
from scraper.query_builder import build_search_query
from models.search_models import SEARCH_MODELS
from models.json_models import JSON_MODELS
from config.settings import API_KEY,CATEGORY_NAME
from utils.logging_config import setup_logging
from enrichment.prompt_template import (
    TEMPLATE_FILLER
)
from enrichment.gemini_client import (
    GeminiClient
)

logger = setup_logging()


def safe_filename(text):
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()

def ensure_dirs():
    Path("data/output").mkdir(parents=True, exist_ok=True)
    Path("logs/html").mkdir(parents=True, exist_ok=True)
    Path("logs/screenshots").mkdir(parents=True, exist_ok=True)


def clean_enrichment_result(result):
    invalid_sources = {
        "overview",
        "justdial",
        "justdial.com",
        "weddingwire",
        "weddingwire.in",
        "weddingwire.com",
    }
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return result

    sources = data.get("sources")
    if isinstance(sources, list):
        data["sources"] = [
            source
            for source in sources
            if str(source).strip().lower() not in invalid_sources
        ]

    return json.dumps(data, ensure_ascii=False, indent=2)

vendors = None
with open("input.json","r") as f:
    vendors=json.load(f)

gemini = GeminiClient(API_KEY)
ensure_dirs()

logger.info("Scraper started with %s vendor(s)", len(vendors))

for vendor in vendors:
    vendor_name = vendor["name"]
    file_stem = safe_filename(vendor_name)
    logger.info(
        "Starting vendor: name=%s city=%s state=%s",
        vendor_name,
        vendor["city"],
        vendor["state"],
    )

    query = build_search_query(
        vendor_name,
        vendor["city"],
        SEARCH_MODELS.get(CATEGORY_NAME)
    )
    
    text = ask_google_ai(query)
    print("===========scraped Data===========")
    print(text.get("answer") or text.get("error"))
    if not text.get("success") or not text.get("answer"):
        logger.error(
            "Scraping failed for %s: %s",
            vendor_name,
            text.get("error", "empty answer"),
        )
        continue

    prompt = (
        TEMPLATE_FILLER
        .substitute(
            vendor_name=vendor_name,
            city=vendor["city"],
            state=vendor["state"],
            content=text["answer"],
            output_format=JSON_MODELS.get(CATEGORY_NAME)
        )
    )
    
    logger.info("Built Gemini prompt for %s (%s chars)", vendor_name, len(prompt))

    logger.info("Calling Gemini enrichment for %s", vendor_name)
    result = gemini.enrich(prompt)
    result = clean_enrichment_result(result)
    logger.info("Gemini enrichment completed for %s (%s chars)", vendor_name, len(result))

    output_file = Path("data/output") / f"{vendor_name}.json"
    logger.info("Writing enrichment output for %s to %s", vendor_name, output_file)

    with output_file.open("w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Finished vendor: %s", vendor_name)

logger.info("Scraper finished")

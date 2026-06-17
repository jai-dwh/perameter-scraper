import re
from pathlib import Path
from scraper.scraper import ask_google_ai
from scraper.query_builder import build_search_query
from utils.models import WEDDING_VANUES
from config.settings import API_KEY
from utils.logging_config import setup_logging

from config.prompt_template import (
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

vendors = [
    {
        "name": "Rams Event",
        "city": "Alwar",
        "state": "Rajasthan"
    }
]

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
        WEDDING_VANUES
    )
    
    text = ask_google_ai(query)
    print("===========scraped Data===========")
    print(text)

    prompt = (
        TEMPLATE_FILLER
        .substitute(
            vendor_name=vendor_name,
            city=vendor["city"],
            state=vendor["state"],
            content=text["answer"]
        )
    )
    
    logger.info("Built Gemini prompt for %s (%s chars)", vendor_name, len(prompt))

    logger.info("Calling Gemini enrichment for %s", vendor_name)
    result = gemini.enrich(prompt)
    logger.info("Gemini enrichment completed for %s (%s chars)", vendor_name, len(result))

    output_file = Path("data/output") / f"{vendor_name}.json"
    logger.info("Writing enrichment output for %s to %s", vendor_name, output_file)

    with output_file.open("w", encoding="utf-8") as f:
        f.write(result)

    logger.info("Finished vendor: %s", vendor_name)

logger.info("Scraper finished")

import json
import re
from pathlib import Path

from scraper.scraper import ask_google_ai
from scraper.query_builder import (
    build_profile_query,
    build_services_query,
)
from models.search_models import SEARCH_MODELS
from models.json_models import JSON_MODELS
from config.settings import API_KEY, CATEGORY_NAME
from utils.logging_config import setup_logging
from enrichment.prompt_template import TEMPLATE_FILLER
from enrichment.gemini_client import GeminiClient

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


def get_category_display_name(category_name):
    return category_name.replace("_", " ").title()


with open("input.json", "r", encoding="utf-8") as f:
    vendors = json.load(f)

gemini = GeminiClient(API_KEY)

ensure_dirs()

logger.info("Scraper started with %s vendor(s)", len(vendors))

model = SEARCH_MODELS.get(CATEGORY_NAME)

if not model:
    raise ValueError(f"Unknown category: {CATEGORY_NAME}")

for vendor in vendors:
    vendor_name = vendor["name"]
    city = vendor["city"]
    state = vendor["state"]

    logger.info(
        "Starting vendor: name=%s city=%s state=%s",
        vendor_name,
        city,
        state,
    )

    category_display = get_category_display_name(CATEGORY_NAME)

    # ------------------------------------------------------------------
    # PROFILE QUERY
    # ------------------------------------------------------------------

    profile_query = build_profile_query(
        vendor_name=vendor_name,
        city=city,
        category=category_display,
        parameters=model["profile"],
    )

    logger.info("Running profile search for %s", vendor_name)
    profile_response = ask_google_ai(profile_query)

    profile_text = (
        profile_response.get("answer")
        if profile_response.get("success")
        else ""
    )

    if not profile_text:
        logger.warning(
            "Profile search failed for %s: %s",
            vendor_name,
            profile_response.get("error"),
        )

    # ------------------------------------------------------------------
    # SERVICES QUERY
    # ------------------------------------------------------------------

    services_query = build_services_query(
        vendor_name=vendor_name,
        city=city,
        category=category_display,
        parameters=model["services"],
    )

    logger.info("Running services search for %s", vendor_name)

    services_response = ask_google_ai(services_query)

    services_text = (
        services_response.get("answer")
        if services_response.get("success")
        else ""
    )

    if not services_text:
        logger.warning(
            "Services search failed for %s: %s",
            vendor_name,
            services_response.get("error"),
        )

    # ------------------------------------------------------------------
    # COMBINED RAW TEXT
    # ------------------------------------------------------------------

    if not profile_text and not services_text:
        logger.error("Both searches failed for %s", vendor_name)
        continue

    combined_text = f"""
================ PROFILE SEARCH ================

{profile_text}

================ SERVICES SEARCH ================

{services_text}
""".strip()

    print("=========== PROFILE DATA ===========")
    print(profile_text or profile_response.get("error"))

    print("=========== SERVICES DATA ===========")
    print(services_text or services_response.get("error"))

    # ------------------------------------------------------------------
    # SAVE RAW TEXT
    # ------------------------------------------------------------------

    text_dir = Path("data/extracted_text") / CATEGORY_NAME / city
    text_dir.mkdir(parents=True, exist_ok=True)

    raw_text_file = text_dir / f"{safe_filename(vendor_name)}.txt"

    with raw_text_file.open("w", encoding="utf-8") as f:
        f.write(combined_text)

    logger.info(
        "Saved combined raw text for %s to %s",
        vendor_name,
        raw_text_file,
    )

    # ------------------------------------------------------------------
    # GEMINI ENRICHMENT
    # ------------------------------------------------------------------

    prompt = TEMPLATE_FILLER.substitute(
        vendor_name=vendor_name,
        city=city,
        state=state,
        content=combined_text,
        output_format=JSON_MODELS.get(CATEGORY_NAME),
    )

    logger.info(
        "Built Gemini prompt for %s (%s chars)",
        vendor_name,
        len(prompt),
    )

    logger.info("Calling Gemini enrichment for %s", vendor_name)

    result = gemini.enrich(prompt)

    result = clean_enrichment_result(result)

    logger.info(
        "Gemini enrichment completed for %s (%s chars)",
        vendor_name,
        len(result),
    )

    # ------------------------------------------------------------------
    # SAVE JSON OUTPUT
    # ------------------------------------------------------------------

    output_dir = Path("data/output") / CATEGORY_NAME / city
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{safe_filename(vendor_name)}.json"

    with output_file.open("w", encoding="utf-8") as f:
        f.write(result)

    logger.info(
        "Finished vendor: %s -> %s",
        vendor_name,
        output_file,
    )

logger.info("Scraper finished")
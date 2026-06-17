from bs4 import BeautifulSoup
from markdownify import markdownify as md


REMOVE_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "canvas",
    "meta",
    "link",
    "form",
    "input",
    "button",
    "header",
    "footer",
    "nav"
}


def extract_ai_mode_markdown(html: str) -> str:

    soup = BeautifulSoup(html, "lxml")

    # Remove junk
    for tag in soup.find_all(REMOVE_TAGS):
        tag.decompose()

    # Find AI response area
    response_root = None

    for div in soup.find_all():

        text = div.get_text(
            " ",
            strip=True
        )

        if (
            "Price Range" in text
            and "Trust Rating" in text
        ):
            response_root = div
            break

    if not response_root:
        response_root = soup.body

    # Remove action buttons
    for tag in response_root.find_all():

        text = tag.get_text(
            " ",
            strip=True
        ).lower()

        if text in {
            "copy",
            "good response",
            "bad response",
            "new thread"
        }:
            tag.decompose()

    markdown = md(
        str(response_root),
        heading_style="ATX"
    )

    # cleanup
    lines = []

    for line in markdown.splitlines():

        line = line.strip()

        if not line:
            continue

        if len(line) < 2:
            continue

        lines.append(line)

    return "\n\n".join(lines)
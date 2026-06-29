from textwrap import dedent


def _normalize_parameters(parameters):
    if isinstance(parameters, (list, tuple)):
        return "\n".join(
            f"- {str(p).strip()}"
            for p in parameters
            if str(p).strip()
        )

    return f"- {str(parameters).strip()}"


def _single_line(text):
    return " ".join(str(text).split())


def build_search_query(
    vendor_name,
    city,
    category,
    search_group,
):
    """
    Build a focused Google AI Search prompt.

    Each call starts a new browser context, therefore every prompt
    must be completely self-contained.
    """

    parameters = _normalize_parameters(search_group["fields"])

    description = search_group.get("description", "")

    if search_group["name"] == "contact":

        sources = dedent("""
        1. Official Website
        2. Google Business Profile
        3. Instagram
        4. Facebook
        5. Business Directories
        """)

    elif search_group["name"] == "pricing":

        sources = dedent("""
        1. Official Website
        2. Pricing Pages
        3. Instagram Posts
        4. Facebook Posts
        5. Wedding Blogs
        """)

    elif search_group["name"] == "reviews":

        sources = dedent("""
        1. Google Business Profile
        2. Official Website
        3. Facebook
        4. News Articles
        """)

    else:

        sources = dedent("""
        1. Official Website
        2. Portfolio Pages
        3. Instagram
        4. Facebook
        5. Event Galleries
        6. Customer Reviews
        7. Blogs
        """)

    prompt = f"""
You are researching a business.

Business Name:
{vendor_name}

Category:
{category}

Location:
{city}, India

Search Objective:
{description}

Search every parameter independently.

Parameters:

{parameters}

Search Sources (highest priority first):

{sources}

Rules:

1. Search EVERY parameter individually.
2. Do not stop after finding some information.
3. Never guess.
4. Never estimate.
5. Never infer missing information.
6. Only use information that can be verified.
7. If multiple values exist, choose the highest priority source.
8. If conflicting values exist, report the highest priority source.
9. If information cannot be verified after checking all sources,
   return exactly:

Not Found

Return the result exactly in this format:

Parameter:
Value:
Source URL:

Repeat for every parameter.
"""

    return _single_line(prompt)
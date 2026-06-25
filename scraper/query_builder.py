def _normalize_parameters(parameters):
    if isinstance(parameters, (list, tuple)):
        return ", ".join(
            str(p).strip()
            for p in parameters
            if str(p).strip()
        )

    return " ".join(str(parameters or "").split()).strip(" ,")

def _single_line(text):
    return " ".join(str(text).split())

def build_profile_query(vendor_name, city, category, parameters):
    parameter_text = _normalize_parameters(parameters)

    prompt = (
        f"Research {category} vendor: {vendor_name}. "
        f"Location: {city}, India. "
        f"For each of the following parameters: {parameter_text}. "
        "Provide the exact value found, supporting evidence, and source URL for each parameter. "
        "Prioritize sources in this order: official website, Instagram, Facebook, "
        "Google Business Profile, news articles, then wedding blogs. "
        "Exclude JustDial, WeddingWire.in and WeddingWire.com. "
        "Return 'Not Found' if information is unavailable."
    )

    return _single_line(prompt)

def build_services_query(vendor_name, city, category, parameters):
    parameter_text = _normalize_parameters(parameters)

    prompt = (
        f"Research {category} vendor: {vendor_name}. "
        f"Location: {city}, India. "
        f"For each of the following parameters: {parameter_text}. "
        "Provide the exact value found, supporting evidence, and source URL for each parameter. "
        "Search official website, Instagram, Facebook, portfolio pages, event galleries, "
        "customer reviews and wedding blogs. "
        "Exclude JustDial, WeddingWire.in and WeddingWire.com. "
        "Return 'Not Found' if information is unavailable."
    )

    return _single_line(prompt)
    parameter_text = _normalize_parameters(parameters)

    prompt= f"""
Research {category} vendor "{vendor_name}" based in {city}, India.

Search official website, Instagram posts, Facebook posts, portfolio pages,
event galleries, wedding directories, interviews, blogs and customer reviews.

For EVERY parameter below return:

Parameter:
Value:
Supporting Evidence:
Source URL:

Parameters:
{parameter_text}

Rules:
- Do NOT skip any parameter.
- If unavailable return exactly "Not Found".
- Infer services only when clearly supported by evidence.
- Do not invent information.
- Use evidence from:
  * service descriptions
  * portfolio pages
  * wedding galleries
  * social media posts
  * about sections
  * customer testimonials
- When multiple values are found, return a comma-separated list.
- Include supporting evidence explaining how the value was determined.
- Prioritize sources in this order:
  1. Official Website
  2. Instagram
  3. Facebook
  4. Portfolio Pages
  5. News Articles
  6. Wedding Blogs
- Exclude JustDial, WeddingWire.com and WeddingWire.in.
- Return results in a structured format.
- Include source URL for every parameter.
""".strip()
    return _single_line(prompt)
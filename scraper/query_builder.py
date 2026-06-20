def build_search_query(vendor_name, city, Perameters):
    parameters = " ".join(Perameters.split())
    return (
        f"For {vendor_name} in {city}, search and give information about: "
        f"{parameters}. Exclude and do not cite information from justdial.com, "
        "weddingwire.in, or weddingwire.com."
    )

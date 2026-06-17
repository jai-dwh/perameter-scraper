def build_search_query(vendor_name, city,Perameters):
    return f"""
    for {vendor_name} {city}
    
    search and give information about
    
    {Perameters}
    
    do not include information from the following sources:
    -site:justdial.com
    -site:weddingwire.in
    -site:weddingwire.com
    """.strip()
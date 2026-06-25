import json

# Read input file
with open("alwar.json", "r", encoding="utf-8") as f:
    vendors = json.load(f)

output = []

for vendor in vendors:
    output.append({
        "id": int(vendor["id"]) if str(vendor["id"]).isdigit() else vendor["id"],
        "name": vendor.get("name"),
        "city": vendor.get("city_name"),
        "state": vendor.get("state_name"),
    })

# Save output
with open("input.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print(f"Extracted {len(output)} vendors")
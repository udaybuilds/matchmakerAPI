import numpy

def int_anls(table, payload):
    print(payload["email"])
    response = table.get_item(Key={"Email": payload["email"]})
    item = response.get('Item', {})

    # Check if 'genre_counts' is missing or empty
    if not item.get("genre_counts"):
        return {"status": "Not enough Data"}

    # Check if 'interest_areas' contains 'unknown'
    interest_areas = item.get("interest_areas", [])
    if "Unknown" in interest_areas:
        return {"status": "Data not ready"}

    # Convert any sets to lists
    for key, value in item.items():
        if isinstance(value, set):
            item[key] = list(value)

    print(item.get('interest_areas', []))
    return item
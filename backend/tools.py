import re


def parse_price(price):

    if not price:
        return 0.0

    cleaned = re.sub(
        r"[^\d.]",
        "",
        str(price)
    )

    try:
        return float(cleaned)
    except:
        return 0.0


def prepare_products(products):

    cleaned = []

    for p in products:

        cleaned.append(
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "category": p.get("main_category"),
                "rating": p.get("ratings"),
                "actual_price": p.get("actual_price"),
                "discount_price": p.get("discount_price"),
                "discount_percent": p.get(
                    "discount_percent"
                )
            }
        )

    return cleaned


def filter_by_budget(
    products,
    max_price
):

    filtered = []

    for p in products:

        price = parse_price(
            p.get("discount_price")
        )

        if (
            price <= max_price
            and p.get("name")
        ):
            filtered.append(p)

    return filtered


def add_discount_percentage(products):

    for p in products:

        actual = parse_price(
            p.get("actual_price")
        )

        discount = parse_price(
            p.get("discount_price")
        )

        if actual > 0:

            p["discount_percent"] = round(
                (
                    (actual - discount)
                    / actual
                ) * 100,
                2
            )

        else:

            p["discount_percent"] = 0

    return products
"""Demand metadata carried outside the unchanged concept core."""
CHANNELS = {"Помощь людям": "help_people", "Учёба": "education",
            "Малый бизнес и НКО": "small_business_nonprofit", "Профессии": "professions"}


def bundle_audience(record):
    channel = record.get("channel")
    if channel in CHANNELS:
        return {"channel": channel, "rubric": CHANNELS[channel], "profession": None,
                "people": channel in {"Помощь людям", "Учёба"}}
    return {"rubric": "help_people", "profession": None, "people": True}

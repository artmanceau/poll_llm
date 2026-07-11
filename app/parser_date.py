import re
from datetime import datetime

months = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}

def parse_poll_date(s, year=2022):
    s = (
        s.lower()
        .replace("\xa0", " ")
        .replace("1er", "1")
    )

    found_months = [
        (m, months[m])
        for m in months
        if m in s
    ]

    numbers = [
        int(x)
        for x in re.findall(r"\d+", s)
    ]

    if len(found_months) == 1:
        month = found_months[0][1]

        if len(numbers) == 1:
            start = end = numbers[0]
        else:
            start, end = numbers[:2]

        start_date = datetime(year, month, start)
        end_date = datetime(year, month, end)

    else:
        start_month = found_months[0][1]
        end_month = found_months[1][1]

        start = numbers[0]
        end = numbers[1]

        start_date = datetime(year, start_month, start)
        end_date = datetime(year, end_month, end)

    return start_date + (end_date - start_date) / 2
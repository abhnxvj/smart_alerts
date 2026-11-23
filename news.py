import csv
import json
import hashlib
import urllib.parse
import feedparser


def load_portfolio(path="portfolio.csv"):
    holdings = []
    f = open(path, newline="", encoding="utf-8")
    for row in csv.DictReader(f):
        kw = []
        for k in row["keywords"].split(";"):
            if k.strip() != "":
                kw.append(k.strip())
        qty = float(row["qty"])
        price = float(row["avg_price"])
        holdings.append({
            "symbol": row["symbol"].strip(),
            "name": row["name"].strip(),
            "qty": qty,
            "value": qty * price,
            "keywords": kw,
        })
    f.close()

    total = 0
    for h in holdings:
        total += h["value"]
    for h in holdings:
        h["weight"] = h["value"] / total
    return holdings


def make_id(title):
    t = title.lower().strip()
    return hashlib.md5(t.encode()).hexdigest()


def split_source(title):
    # google news titles look like "Headline text - Source Name"
    if " - " in title:
        idx = title.rfind(" - ")
        return title[:idx].strip(), title[idx + 3:].strip()
    return title.strip(), ""


def fetch_news(h, days=1):
    query = ""
    for k in h["keywords"]:
        if query != "":
            query += " OR "
        query += '"' + k + '"'
    query += " when:" + str(days) + "d"

    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + "&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(url)

    res = []
    for e in feed.entries:
        title, source = split_source(e.get("title", ""))
        if title == "":
            continue
        res.append({
            "id": make_id(title),
            "symbol": h["symbol"],
            "title": title,
            "source": source,
            "link": e.get("link", ""),
            "published": e.get("published", ""),
        })
    return res


def load_sample_news(path="sample_news.json"):
    f = open(path, encoding="utf-8")
    data = json.load(f)
    f.close()
    res = []
    for n in data:
        n["id"] = make_id(n["title"])
        res.append(n)
    return res

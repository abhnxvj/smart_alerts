import os
import sys
import time
from dotenv import load_dotenv

import news
import store
import screen
import mailer

load_dotenv()

MIN_IMPACT = int(os.getenv("MIN_IMPACT", "6"))
ALERT_SCORE = float(os.getenv("ALERT_SCORE", "7"))
HIGH_IMPACT = int(os.getenv("HIGH_IMPACT", "9"))


def run(mock=False, sample=None, dry=False):
    holdings = news.load_portfolio()
    con = store.connect()

    if sample:
        all_news = news.load_sample_news(sample)

    alerts = []
    stats = {"fetched": 0, "new": 0, "passed_screen": 0, "material": 0}

    for h in holdings:
        if sample:
            items = []
            for n in all_news:
                if n["symbol"] == h["symbol"]:
                    items.append(n)
        else:
            items = news.fetch_news(h)
            time.sleep(1)
        stats["fetched"] += len(items)

        fresh = []
        for n in items:
            if not store.is_seen(con, n["id"]):
                fresh.append(n)
        if len(fresh) == 0:
            continue
        stats["new"] += len(fresh)
        fresh = fresh[:25]

        # step 1: cheap model screens every headline
        if mock:
            scores = screen.screen_mock(h, fresh)
        else:
            scores = screen.screen_gemini(h, fresh)

        for s in scores:
            n = fresh[s["i"]]
            store.mark_seen(con, n)
            if not s["relevant"] or s["impact"] < MIN_IMPACT:
                continue
            stats["passed_screen"] += 1

            # step 2: stronger model checks it against events we already track
            events = store.open_events(con, h["symbol"])
            if mock:
                r = screen.explain_mock(h, n, events, s["type"])
            else:
                r = screen.explain_openai(h, n, events)

            event_id = store.save_event(con, h["symbol"], r["event_id"], r["summary"], s["impact"], r["direction"])
            if not r["material_change"]:
                continue
            stats["material"] += 1

            # weight relative to an equal-weight portfolio, so 1.0 means average size
            score = s["impact"] * h["weight"] * len(holdings)
            if score < ALERT_SCORE and s["impact"] < HIGH_IMPACT:
                continue

            alerts.append({
                "symbol": h["symbol"], "weight": h["weight"], "impact": s["impact"], "score": score,
                "event_id": event_id, "title": n["title"], "source": n["source"], "link": n["link"],
                "what_changed": r["what_changed"], "why_it_matters": r["why_it_matters"],
                "summary": r["summary"], "direction": r["direction"],
            })

    # highest portfolio-weighted impact first
    for i in range(len(alerts)):
        for j in range(i + 1, len(alerts)):
            if alerts[j]["score"] > alerts[i]["score"]:
                alerts[i], alerts[j] = alerts[j], alerts[i]

    print("fetched:", stats["fetched"], "| new:", stats["new"], "| passed screen:", stats["passed_screen"],
          "| material:", stats["material"], "| alerts:", len(alerts))

    if len(alerts) == 0:
        return

    for a in alerts:
        print("  [" + a["symbol"] + "] score " + str(round(a["score"], 1)) + " - " + a["what_changed"])

    if dry:
        f = open("last_alert.html", "w", encoding="utf-8")
        f.write(mailer.build_html(alerts))
        f.close()
        print("dry run, email saved to last_alert.html")
    else:
        mailer.send_mail(alerts)
        print("email sent to", os.getenv("ALERT_TO"))

    for a in alerts:
        store.save_alert(con, a)


if __name__ == "__main__":
    args = sys.argv[1:]
    sample = None
    for a in args:
        if a.endswith(".json"):
            sample = a
    run(mock="--mock" in args, sample=sample, dry="--dry-run" in args)

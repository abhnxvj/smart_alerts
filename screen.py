import os
import json

SCREEN_PROMPT = """You screen stock market news for an Indian retail investor.
Company: {name} (NSE: {symbol})

For each headline decide:
- relevant: is it actually about this company (not just a passing mention or a market wrap)?
- impact: 0-10, how much it can change the company's fundamentals or stock price
  0-3 = noise (daily price moves, listicles, a single broker target, repeated old news)
  4-6 = worth knowing (small orders, minor management changes, sector news)
  7-8 = likely to move the stock (quarterly results surprise, big order win/loss, rating change, regulatory action)
  9-10 = major (fraud, large M&A, guidance cut, ban, key leader exit)
- type: one of earnings, deal, regulatory, legal, management, product, macro, other

Headlines:
{lines}

Return JSON only: {{"items": [{{"i": 0, "relevant": true, "impact": 5, "type": "earnings"}}]}}"""

EXPLAIN_PROMPT = """You write portfolio alerts for an Indian retail investor.
Holding: {name} (NSE: {symbol}), {weight}% of the portfolio.

New headline: {title}
Source: {source}

Events already being tracked for this holding in the last 7 days:
{events}

Tasks:
1. If the headline is about the same announcement, plan, deal or issue as a tracked event (even with different
   wording or numbers), set event_id to that id. Otherwise set event_id to null.
2. material_change = true only if the headline adds a NEW fact about the company's business:
   a new number, decision, order, deal, party, reversal or escalation.
   NOT material: the same announcement reported by another outlet, explainers ("what it means"),
   stock price moves, analyst comments on news already tracked, or small extra details of a tracked event.
3. summary: 1-2 lines, the full event so far including this headline.
4. what_changed: one plain news-style sentence under 20 words, starting with the company name.
   Example: "Maruti Suzuki raised prices on select models by up to 0.3%."
   Never start with "The new information" or "This headline".
5. direction for the holding: positive, negative, mixed or unclear.
6. why_it_matters: one short sentence on why this matters for someone holding {name}. No buy/sell advice.

Return JSON only with keys: event_id, material_change, summary, what_changed, direction, why_it_matters"""


def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def ask_openai(model, prompt):
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return clean_json(resp.choices[0].message.content)


def screen_openai(h, news):
    lines = ""
    for i in range(len(news)):
        lines += str(i) + ". " + news[i]["title"] + " (" + news[i]["source"] + ")\n"

    prompt = SCREEN_PROMPT.format(name=h["name"], symbol=h["symbol"], lines=lines)
    data = ask_openai(os.getenv("SCREEN_MODEL", "gpt-4o-mini"), prompt)
    return data["items"]


def explain_openai(h, n, events):
    ev = ""
    for e in events:
        ev += "id " + str(e["id"]) + ": " + e["summary"] + "\n"
    if ev == "":
        ev = "none"

    prompt = EXPLAIN_PROMPT.format(name=h["name"], symbol=h["symbol"], weight=round(h["weight"] * 100),
                                   title=n["title"], source=n["source"], events=ev)
    return ask_openai(os.getenv("EXPLAIN_MODEL", "gpt-4o"), prompt)


# offline versions so the pipeline can be tested without api keys
MOCK_WORDS = {
    "fraud": (10, "legal"), "probe": (8, "regulatory"), "penalty": (7, "regulatory"), "sebi": (7, "regulatory"),
    "acquire": (8, "deal"), "acquisition": (8, "deal"), "merger": (9, "deal"), "stake": (6, "deal"),
    "q2": (7, "earnings"), "q3": (7, "earnings"), "profit": (7, "earnings"), "results": (7, "earnings"),
    "guidance": (8, "earnings"), "resigns": (8, "management"), "ceo": (6, "management"),
    "order": (6, "deal"), "contract": (6, "deal"), "downgrade": (7, "other"), "upgrade": (6, "other"),
}


def screen_mock(h, news):
    items = []
    for i in range(len(news)):
        t = news[i]["title"].lower()
        impact = 2
        typ = "other"
        for w in MOCK_WORDS:
            if w in t and MOCK_WORDS[w][0] > impact:
                impact = MOCK_WORDS[w][0]
                typ = MOCK_WORDS[w][1]
        items.append({"i": i, "relevant": True, "impact": impact, "type": typ})
    return items


def explain_mock(h, n, events, typ):
    t = n["title"]
    for e in events:
        if e["summary"].startswith("[" + typ + "]"):
            # mock rule: material only if the headline has a number we haven't seen in this story
            new = False
            for word in t.replace(",", "").split():
                has_digit = False
                for ch in word:
                    if ch.isdigit():
                        has_digit = True
                if has_digit and word not in e["summary"].replace(",", ""):
                    new = True
            return {"event_id": e["id"], "material_change": new, "summary": e["summary"] + " | " + t,
                    "what_changed": t, "direction": "unclear", "why_it_matters": "Update on a tracked " + typ + " event."}
    return {"event_id": None, "material_change": True, "summary": "[" + typ + "] " + t,
            "what_changed": t, "direction": "unclear", "why_it_matters": "New " + typ + " event for " + h["name"] + "."}

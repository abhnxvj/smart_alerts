# Smart Alerts

Email alerts when news actually changes something about the stocks you hold.

Most portfolio apps either send nothing or send every headline. Smart Alerts reads the news for each holding, throws away the noise, keeps track of stories that are still developing, and only emails you when there is a new fact that matters, ranked by how much of your portfolio is exposed.

## How it works

```
Google News RSS (per holding)
        |
   dedupe (SQLite)
        |
Step 1: gpt-4o-mini screens every headline -> relevant? impact 0-10?
        |  (only impact >= MIN_IMPACT moves on)
Step 2: gpt-4o compares it with events already tracked for that stock
        -> same story or new event? any NEW fact? what changed? why it matters?
        |  (repeats of a known story are dropped)
Portfolio weighting: score = impact x (weight / equal weight)
        |  (alert if score >= ALERT_SCORE, or impact >= HIGH_IMPACT)
Email digest (Gmail), highest score first
```

Two models because most headlines are noise. A small, cheap model screens all of them in one batched call per stock, and the stronger model only sees the few that survive. Step 2 is what stops "Reliance stake buy: what we know" from alerting you again after you already got "Reliance to acquire stake for Rs 2,000 crore", while still alerting on "Reliance raises stake buy to Rs 3,500 crore".

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `OPENAI_API_KEY` from platform.openai.com
- `GMAIL_USER`: the Gmail account that sends the alerts
- `GMAIL_APP_PASSWORD`: an App Password for that account (Google Account > Security > 2-Step Verification > App passwords). Your normal Gmail password will not work.

Edit `portfolio.csv` with your holdings: NSE symbol, quantity and average buy price. Each stock's weight is worked out from qty x avg_price. `keywords` are the names the news uses for the company, separated by `;`. The sample file holds 30 large caps, 2-3 shares each, bought at the 23 Nov 2026 close.

## Run

```bash
python main.py                 # live news, real models, sends email
python main.py --dry-run       # same, but saves the email to last_alert.html instead of sending
python main.py --mock --dry-run sample_news.json            # offline test, no API keys needed
python main.py --mock --dry-run sample_news_followup.json   # run after the one above to see event tracking
```

## Deploy (GitHub Actions, free)

The repo has a workflow in `.github/workflows/alerts.yml` that runs every hour from 9:00 to 18:00 IST, Monday to Friday. No server needed. `alerts.db` is carried between runs with the Actions cache, so old headlines are not sent again.

1. Repo > Settings > Secrets and variables > Actions > New repository secret. Add:
   `OPENAI_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `ALERT_TO`
2. Actions tab > smart-alerts > Run workflow, to test it once.

GitHub pauses scheduled workflows on repos with no activity for 60 days. Push a commit or re-enable it from the Actions tab when that happens.

To run it on your own machine instead, add this with `crontab -e` (Mac/Linux):

```
0 9-18 * * 1-5 cd /path/to/smart-alerts && python3 main.py >> run.log 2>&1
```

On Windows, use Task Scheduler to run `python main.py` in this folder.

## Settings (.env)

| Setting | Default | Meaning |
|---|---|---|
| MIN_IMPACT | 6 | Headlines below this impact never reach step 2 |
| ALERT_SCORE | 7 | Minimum weighted score to send an alert |
| HIGH_IMPACT | 9 | Impact at or above this always alerts, even for small holdings |
| SCREEN_MODEL | gpt-4o-mini | Screening model (step 1) |
| EXPLAIN_MODEL | gpt-4o | Event tracking and explanation model (step 2) |

The weighted score is impact x (weight / equal weight). With 30 holdings, equal weight is about 3.3%. So an impact-7 story on a 5% holding scores 10.5 and alerts, while an impact-7 story on a 2% holding scores 4.2 and does not. Raise `ALERT_SCORE` if you get too many emails.

## Files

- `main.py` runs the pipeline
- `news.py` loads the portfolio and fetches Google News RSS
- `screen.py` has both model prompts, plus offline mock versions for testing
- `store.py` keeps seen headlines, tracked events and sent alerts in `alerts.db`
- `mailer.py` builds and sends the HTML email

## Limits

- Google News RSS gives headlines only, not full articles, so the models judge from the headline.
- The first run sees a day of backlog. Each stock is capped at 25 new headlines per run, and the rest are picked up in later runs.
- Impact scores come from the model, not from price data. They can be checked later by comparing alerts with next-day price moves.
- Not investment advice. Alerts never say buy or sell.

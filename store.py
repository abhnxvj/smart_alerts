import sqlite3
from datetime import datetime, timedelta


def connect(path="alerts.db"):
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("""create table if not exists seen (
        id text primary key, symbol text, title text, seen_at text)""")
    cur.execute("""create table if not exists events (
        id integer primary key autoincrement, symbol text, summary text,
        impact integer, direction text, created_at text, updated_at text)""")
    cur.execute("""create table if not exists alerts (
        id integer primary key autoincrement, symbol text, event_id integer,
        title text, what_changed text, score real, sent_at text)""")
    con.commit()
    return con


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_seen(con, news_id):
    cur = con.cursor()
    cur.execute("select 1 from seen where id = ?", (news_id,))
    return cur.fetchone() is not None


def mark_seen(con, n):
    con.execute("insert or ignore into seen values (?, ?, ?, ?)", (n["id"], n["symbol"], n["title"], now()))
    con.commit()


def open_events(con, symbol, days=7):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cur = con.cursor()
    cur.execute("select id, summary, impact, direction from events where symbol = ? and updated_at >= ? order by updated_at desc",
                (symbol, cutoff))
    res = []
    for row in cur.fetchall():
        res.append({"id": row[0], "summary": row[1], "impact": row[2], "direction": row[3]})
    return res


def save_event(con, symbol, event_id, summary, impact, direction):
    if event_id is None:
        cur = con.cursor()
        cur.execute("insert into events (symbol, summary, impact, direction, created_at, updated_at) values (?, ?, ?, ?, ?, ?)",
                    (symbol, summary, impact, direction, now(), now()))
        con.commit()
        return cur.lastrowid
    con.execute("update events set summary = ?, impact = ?, direction = ?, updated_at = ? where id = ?",
                (summary, impact, direction, now(), event_id))
    con.commit()
    return event_id


def save_alert(con, a):
    con.execute("insert into alerts (symbol, event_id, title, what_changed, score, sent_at) values (?, ?, ?, ?, ?, ?)",
                (a["symbol"], a["event_id"], a["title"], a["what_changed"], a["score"], now()))
    con.commit()

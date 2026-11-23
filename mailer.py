import os
import smtplib
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

COLORS = {"positive": "#1e8e3e", "negative": "#d93025", "mixed": "#e37400", "unclear": "#5f6368"}


def build_html(alerts):
    html = '<div style="font-family:Arial,sans-serif;max-width:640px">'
    html += '<h2 style="margin-bottom:4px">Smart Alerts</h2>'
    html += '<p style="color:#5f6368;margin-top:0">' + str(len(alerts)) + ' material update(s) on your holdings</p>'

    for a in alerts:
        color = COLORS.get(a["direction"], "#5f6368")
        html += '<div style="border-left:4px solid ' + color + ';padding:8px 12px;margin:14px 0;background:#f8f9fa">'
        html += '<b>' + a["symbol"] + '</b> &middot; ' + str(round(a["weight"] * 100)) + '% of portfolio'
        html += ' &middot; impact ' + str(a["impact"]) + '/10'
        html += ' &middot; <span style="color:' + color + '">' + escape(a["direction"]) + '</span><br>'
        html += '<p style="margin:6px 0"><b>What changed:</b> ' + escape(a["what_changed"]) + '</p>'
        html += '<p style="margin:6px 0"><b>Why it matters:</b> ' + escape(a["why_it_matters"]) + '</p>'
        html += '<p style="margin:6px 0;color:#5f6368"><b>Story so far:</b> ' + escape(a["summary"]) + '</p>'
        html += '<a href="' + escape(a["link"]) + '">' + escape(a["title"]) + '</a> <span style="color:#5f6368">(' + escape(a["source"]) + ')</span>'
        html += '</div>'

    html += '<p style="color:#9aa0a6;font-size:12px">Not investment advice. Sorted by portfolio-weighted impact.</p></div>'
    return html


def send_mail(alerts):
    user = os.getenv("GMAIL_USER")
    pwd = os.getenv("GMAIL_APP_PASSWORD")
    to = os.getenv("ALERT_TO", user)

    if len(alerts) == 1:
        subject = "Smart Alert: " + alerts[0]["symbol"] + " - " + alerts[0]["what_changed"][:60]
    else:
        names = []
        for a in alerts:
            if a["symbol"] not in names:
                names.append(a["symbol"])
        subject = "Smart Alerts: " + str(len(alerts)) + " updates (" + ", ".join(names) + ")"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.attach(MIMEText(build_html(alerts), "html"))

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(user, pwd)
    server.sendmail(user, [to], msg.as_string())
    server.quit()

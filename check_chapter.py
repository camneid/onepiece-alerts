#!/usr/bin/env python3
"""Check TCB Scans for a new One Piece chapter and notify via ntfy (push) + email.

Uses only the Python standard library, so there is nothing to install.
"""

import json
import os
import re
import smtplib
import sys
import time
import urllib.request
from email.message import EmailMessage
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

# If TCB Scans ever changes its domain, this is the only line you need to edit.
PAGE_URL = "https://tcbonepiecechapters.com/mangas/5/one-piece"

STATE_FILE = Path(__file__).with_name("last_chapter.txt")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Matches links like /chapters/8011/one-piece-chapter-1197
# and decimal chapters like /chapters/3818/one-piece-chapter-1053-4-review-1688718749
LINK_RE = re.compile(
    r"""<a\b[^>]*?href=["']([^"']*?/chapters/\d+/one-piece-chapter-(\d+)(?:-(\d+))?[^"']*)["'][^>]*>(.*?)</a>""",
    re.IGNORECASE | re.DOTALL,
)


def fmt(number):
    """1197.0 -> '1197', 1053.4 -> '1053.4'"""
    return str(int(number)) if number == int(number) else str(number)


def fetch(url, attempts=3):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:  # network hiccup, 403, etc.
            last_error = exc
            print(f"Fetch attempt {attempt}/{attempts} failed: {exc}", file=sys.stderr)
            if attempt < attempts:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def parse_chapters(html):
    """Return {chapter_number: (title, absolute_url)} for every chapter link found."""
    chapters = {}
    for href, whole, decimal, inner in LINK_RE.findall(html):
        number = float(f"{whole}.{decimal}") if decimal else float(whole)
        title = " ".join(unescape(re.sub(r"<[^>]+>", " ", inner)).split())
        title = title or f"One Piece Chapter {fmt(number)}"
        chapters[number] = (title, urljoin(PAGE_URL, href))
    return chapters


def read_state():
    try:
        return float(STATE_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def write_state(number):
    STATE_FILE.write_text(fmt(number) + "\n")


def send_push(title, message, link):
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        raise RuntimeError("NTFY_TOPIC secret is not set")
    payload = {
        "topic": topic,
        "title": title,
        "message": message,
        "click": link,
        "tags": ["tada"],
    }
    req = urllib.request.Request(
        "https://ntfy.sh/",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


def send_email(subject, body):
    sender = os.environ.get("EMAIL_ADDRESS", "").strip()
    password = os.environ.get("EMAIL_APP_PASSWORD", "").replace(" ", "")
    recipient = os.environ.get("EMAIL_TO", "").strip() or sender
    if not (sender and password):
        raise RuntimeError("EMAIL_ADDRESS / EMAIL_APP_PASSWORD secrets are not set")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(sender, password)
        server.send_message(msg)


def notify(title, link):
    """Send push + email. Returns (succeeded, failed) lists of channel names."""
    succeeded, failed = [], []
    body = f"{title}\n\nRead it here: {link}"
    for name, action in (
        ("push", lambda: send_push(title, "A new chapter just dropped on TCB Scans.", link)),
        ("email", lambda: send_email(title, body)),
    ):
        try:
            action()
            succeeded.append(name)
            print(f"Sent {name} notification")
        except Exception as exc:
            failed.append(name)
            print(f"ERROR sending {name}: {exc}", file=sys.stderr)
    return succeeded, failed


def main():
    force_test = os.environ.get("FORCE_TEST", "").lower() == "true"

    chapters = parse_chapters(fetch(PAGE_URL))
    if not chapters:
        print(
            "ERROR: found no chapter links. The site layout may have changed "
            "or the request was blocked.",
            file=sys.stderr,
        )
        return 1

    latest = max(chapters)
    title, link = chapters[latest]
    last_seen = read_state()
    print(f"Latest on site: {fmt(latest)} | last notified: {fmt(last_seen) if last_seen is not None else 'none'}")

    if force_test:
        _, failed = notify(f"[TEST] {title}", link)
        return 1 if failed else 0

    if last_seen is None:
        write_state(latest)
        print(f"First run: saved chapter {fmt(latest)} as the starting point (no notification).")
        return 0

    if latest <= last_seen:
        print("No new chapter.")
        return 0

    succeeded, failed = notify(title, link)
    if succeeded:
        # Save state if at least one channel worked so we never spam you repeatedly.
        write_state(latest)
    # A non-zero exit makes GitHub flag the run as failed (and email you about it).
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

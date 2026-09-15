import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# Azur Lane EN Twitter/X account through RSSHub
FEED_URL = "https://rsshub.yfi.moe/twitter/user/AzurLane_EN/excludeReplies=1&excludeRetweets=1"
STATE_FILE = Path("last_seen.json")
WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]


def download_feed():
    req = urllib.request.Request(
        FEED_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def get_posts():
    root = ET.fromstring(download_feed())
    posts = []

    for item in root.findall(".//item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        guid = item.findtext("guid", link).strip()

        if link:
            posts.append({
                "id": guid or link,
                "title": title,
                "link": link
            })

    return posts


def send_to_discord(post):
    message = {
        "content": f"**Azur Lane EN**\n{post['title']}\n{post['link']}"
    }

    data = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "AzurLane-News-Bot/1.0"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        response.read()


def main():
    posts = get_posts()

    if not posts:
        raise RuntimeError("The RSS feed returned no posts.")

    # First run: remember the newest post without flooding Discord.
    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps({"last_seen": posts[0]["id"]}, indent=2)
        )
        print("First run initialized. No old posts sent.")
        return

    state = json.loads(STATE_FILE.read_text())
    last_seen = state.get("last_seen")

    new_posts = []

    for post in posts:
        if post["id"] == last_seen:
            break
        new_posts.append(post)

    # Send oldest first if several appeared between checks.
    for post in reversed(new_posts):
        send_to_discord(post)
        print("Sent:", post["link"])

    STATE_FILE.write_text(
        json.dumps({"last_seen": posts[0]["id"]}, indent=2)
    )

    print(f"Finished. {len(new_posts)} new post(s).")


if __name__ == "__main__":
    main()

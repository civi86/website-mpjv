#!/usr/bin/env python3
"""
Hakee uusimmat Instagram-postaukset julkisilta tileiltä.
Tallentaa kuvat images/instagram/-kansioon ja päivittää instagram.json:in.
"""

import os
import json
import instaloader

# ---------- ASETUKSET ----------
ACCOUNTS = ["mpjv02", "iotadra"]
POSTS_PER_ACCOUNT = 6
OUTPUT_DIR = "images/instagram"
OUTPUT_FILE = "instagram.json"
# -------------------------------


def fetch_account_posts(loader, username, count):
    """Hakee käyttäjän uusimmat postaukset."""
    print(f"📸 Haetaan @{username}...")

    try:
        profile = instaloader.Profile.from_username(loader.context, username)
    except Exception as e:
        print(f"   ❌ Profiilia ei löytynyt: {e}")
        return []

    posts = []
    try:
        for i, post in enumerate(profile.get_posts()):
            if i >= count:
                break

            # Kuvan URL — käytetään suurinta
            image_url = post.url

            # Kuvateksti (ensimmäinen rivi)
            caption = ""
            if post.caption:
                caption = post.caption.split("\n")[0][:100]

            posts.append({
                "shortcode": post.shortcode,
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "image": image_url,
                "caption": caption,
                "date": post.date_utc.strftime("%Y-%m-%d"),
            })

            print(f"   ✓ {post.shortcode} ({post.date_utc.strftime('%Y-%m-%d')})")

    except Exception as e:
        print(f"   ⚠️  Virhe haettaessa: {e}")

    return posts


def download_image(url, filepath):
    """Lataa kuvan paikallisesti."""
    import urllib.request

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            with open(filepath, "wb") as f:
                f.write(response.read())
        return True
    except Exception as e:
        print(f"   ❌ Kuvan lataus epäonnistui: {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Luo Instaloader ilman kirjautumista
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        quiet=True,
    )

    all_posts = {}

    for username in ACCOUNTS:
        posts = fetch_account_posts(loader, username, POSTS_PER_ACCOUNT)

        # Lataa kuvat paikallisesti
        for post in posts:
            filename = f"{username}_{post['shortcode']}.jpg"
            filepath = os.path.join(OUTPUT_DIR, filename)

            if not os.path.exists(filepath):
                download_image(post["image"], filepath)

            # Korvaa URL paikallisella polulla
            if os.path.exists(filepath):
                post["image"] = filepath.replace("\\", "/")

        all_posts[username] = posts

    # Tallenna JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    total = sum(len(posts) for posts in all_posts.values())
    print(f"\n✅ Tallennettu {total} postausta → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
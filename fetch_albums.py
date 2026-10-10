#!/usr/bin/env python3
"""
Hakee MpjV:n albumit Spotifysta ja Bandcampista.
Lataa kansikuvat paikallisesti images/covers/-kansioon.
Tallentaa tuloksen albums.json-tiedostoon.
"""

import os
import json
import asyncio
import hashlib
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from bandcamp_async_api import BandcampAPIClient

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_ARTIST_ID = os.getenv("SPOTIFY_ARTIST_ID")
BANDCAMP_ARTIST = os.getenv("BANDCAMP_ARTIST")
BANDCAMP_SUBDOMAIN = "mpjv"

OUTPUT_FILE = "albums.json"
COVERS_DIR = "images/covers"


# ---------- APUFUNKTIOT ----------
def parse_bandcamp_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%d %b %Y %H:%M:%S GMT")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(date_str)


def bandcamp_cover_url(art_id):
    if not art_id:
        return ""
    return f"https://f4.bcbits.com/img/a{art_id}_10.jpg"


def bandcamp_item_url(item_type, item_id):
    if not item_id:
        return ""
    path = "track" if item_type == "track" else "album"
    return f"https://{BANDCAMP_SUBDOMAIN}.bandcamp.com/{path}/{item_id}"


def spotify_largest_image(images):
    if not images:
        return ""
    largest = max(images, key=lambda x: x.get("width", 0) or 0)
    return largest.get("url", "")


def spotify_upgrade_cover(url):
    if not url:
        return ""
    return (url
            .replace("ab67616d0000b273", "ab67616d00001e02")
            .replace("ab67616d00004851", "ab67616d00001e02"))


def download_cover(url, title):
    """
    Lataa kansikuvan paikallisesti images/covers/-kansioon.
    Palauttaa paikallisen polun (esim. "images/covers/abc123.jpg").
    """
    if not url:
        return ""

    os.makedirs(COVERS_DIR, exist_ok=True)

    # Luo uniikki tiedostonimi URL:n perusteella
    ext = ".jpg"
    hash_part = hashlib.md5(url.encode()).hexdigest()[:12]
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
    filename = f"{safe_title}_{hash_part}{ext}"
    filepath = os.path.join(COVERS_DIR, filename)

    # Ohita jos tiedosto on jo olemassa
    if os.path.exists(filepath):
        return filepath.replace("\\", "/")

    # Lataa kuva
    try:
        # Lähetä Referer-otsikko — Bandcamp vaatii sen
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://bandcamp.com/",
                "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            with open(filepath, "wb") as f:
                f.write(response.read())

        print(f"   ⬇  {filename}")
        return filepath.replace("\\", "/")

    except Exception as e:
        print(f"   ❌ Lataus epäonnistui: {title} ({e})")
        return url  # Fallback: käytä alkuperäistä URL:ia


# ---------- SPOTIFY ----------
def fetch_spotify_albums():
    auth = SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
    )
    sp = spotipy.Spotify(auth_manager=auth)

    albums = []
    offset = 0
    limit = 10

    while True:
        results = sp.artist_albums(
            SPOTIFY_ARTIST_ID,
            album_type="album,single",
            limit=limit,
            offset=offset,
        )
        items = results.get("items", [])
        if not items:
            break

        for a in items:
            albums.append({
                "title": a["name"],
                "artist": "MpjV",
                "release_date": a.get("release_date", ""),
                "cover": spotify_upgrade_cover(
                    spotify_largest_image(a.get("images", []))
                ),
                "spotify_url": a["external_urls"]["spotify"],
                "platform": "spotify",
            })

        offset += limit

    return albums


# ---------- BANDCAMP ----------
async def fetch_bandcamp_albums():
    async with BandcampAPIClient() as client:
        artist = await client.get_artist(int(BANDCAMP_ARTIST))
        discography = await client.get_artist_discography(artist.id)

    albums = []
    for item in discography:
        albums.append({
            "title": item.get("title", ""),
            "artist": "MpjV",
            "release_date": parse_bandcamp_date(item.get("release_date", "")),
            "cover": bandcamp_cover_url(item.get("art_id")),
            "bandcamp_url": bandcamp_item_url(
                item.get("item_type", "album"),
                item.get("item_id")
            ),
            "platform": "bandcamp",
        })
    return albums


# ---------- YHDISTÄ ----------
def merge_albums(spotify_list, bandcamp_list):
    def normalize(title):
        return (title.lower().strip()
                .replace("(remastered", "")
                .replace("(original game soundtrack)", "")
                .replace("(deluxe edition)", "")
                .replace("  ", " ")
                .strip())

    merged = {}

    for a in spotify_list + bandcamp_list:
        key = normalize(a["title"])
        if key not in merged:
            merged[key] = {
                "title": a["title"],
                "artist": a["artist"],
                "release_date": a["release_date"],
                "cover": a["cover"],
                "spotify_url": "",
                "bandcamp_url": "",
            }
        if a["platform"] == "spotify" and not merged[key]["spotify_url"]:
            merged[key]["spotify_url"] = a["spotify_url"]
        if a["platform"] == "bandcamp" and not merged[key]["bandcamp_url"]:
            merged[key]["bandcamp_url"] = a["bandcamp_url"]
        if a["cover"] and not merged[key]["cover"]:
            merged[key]["cover"] = a["cover"]
        if a["release_date"] and not merged[key]["release_date"]:
            merged[key]["release_date"] = a["release_date"]

    result = list(merged.values())
    result.sort(key=lambda x: x.get("release_date", ""), reverse=True)
    return result


# ---------- MAIN ----------
def main():
    print("🎵 Haetaan Spotify...")
    spotify = fetch_spotify_albums()
    print(f"   → {len(spotify)} albumia")

    print("🎵 Haetaan Bandcamp...")
    bandcamp = asyncio.run(fetch_bandcamp_albums())
    print(f"   → {len(bandcamp)} albumia")

    print("🔀 Yhdistetään...")
    merged = merge_albums(spotify, bandcamp)

    print(f"📥 Ladataan kansikuvat {COVERS_DIR}/...")
    for album in merged:
        local_path = download_cover(album["cover"], album["title"])
        album["cover"] = local_path

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✅ Tallennettu {len(merged)} albumia → {OUTPUT_FILE}")

    missing = [a["title"] for a in merged if not a.get("cover")]
    if missing:
        print(f"⚠️  Puuttuvat kansikuvat: {len(missing)}")
        for title in missing:
            print(f"   - {title}")


if __name__ == "__main__":
    main()
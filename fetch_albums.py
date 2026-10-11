#!/usr/bin/env python3
"""
Hakee MpjV:n ja Iota Dran albumit ja singlet Spotifysta ja Bandcampista.
Tallentaa erikseen albums.json ja tracks.json — molemmat sisältävät artist-kentän.
Lataa kansikuvat paikallisesti images/covers/-kansioon.

Käyttää bandcamp_urls.json-tiedostoa ohittamaan virheelliset slugit
(esim. Frostmoor → /track/frostmoor-2, koska /track/frostmoor on jo varattu).
"""

import os
import re
import sys
import json
import time
import asyncio
import hashlib
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from bandcamp_async_api import BandcampAPIClient


# ============================================
# POLKUAPURI — toimii sekä .py:nä että .exe:nä
# ============================================
def get_base_dir():
    """Palauttaa kansion, jossa .exe sijaitsee (tai skripti, jos ajetaan .py:nä)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()

# Lue .env-tiedosto .exe:n (tai skriptin) vierestä
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


# Artistit
ARTISTS = [
    {
        "name": "MpjV",
        "spotify_id": "3YCp3jx8nfeUxvCn4zKsaE",
        "bandcamp_id": "2099574454",
        "bandcamp_subdomain": "mpjv",
    },
    {
        "name": "Iota Dra",
        "spotify_id": "51FlxB6ndzPum6t1wBbyJC",
        "bandcamp_id": "976907511",
        "bandcamp_subdomain": "iotadra",
    },
]

ALBUMS_FILE = "albums.json"
TRACKS_FILE = "tracks.json"
COVERS_DIR = "images/covers"
OVERRIDES_FILE = "bandcamp_urls.json"


# ============================================
# KOMENTOKEHOTTEEN APUFUNKTIOT
# ============================================
def log(msg, symbol="›"):
    """Tulostaa viestin sisennyksellä ja symbolilla."""
    print(f"  {symbol} {msg}", flush=True)


def log_step(step_num, total, msg):
    """Tulostaa vaiheen 'X/Y' -muodossa."""
    print(f"\n[{step_num}/{total}] {msg}", flush=True)


def log_ok(msg):
    print(f"  ✓ {msg}", flush=True)


def log_warn(msg):
    print(f"  ⚠ {msg}", flush=True)


def log_err(msg):
    print(f"  ✗ {msg}", flush=True)


def print_banner():
    print()
    print("╔══════════════════════════════════════════╗")
    print("║   MpjV — Bandcamp & Spotify Päivitys     ║")
    print("║   Hakee albumit ja singlet               ║")
    print("╚══════════════════════════════════════════╝")
    print()


# ============================================
# APUFUNKTIOT
# ============================================
def parse_bandcamp_date(date_str):
    """Muuntaa '07 Oct 2026 00:00:00 GMT' → '2026-10-07'."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%d %b %Y %H:%M:%S GMT")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(date_str)


def slugify(title):
    """Muuntaa 'Four-channel XMs' → 'four-channel-xms'."""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def bandcamp_cover_url(art_id):
    """Rakentaa Bandcampin kansikuvan URL:n — _10 = 1200×1200."""
    if not art_id:
        return ""
    return f"https://f4.bcbits.com/img/a{art_id}_10.jpg"


def load_bandcamp_overrides():
    """Lataa käsin määritellyt Bandcamp-URLit."""
    overrides_path = os.path.join(BASE_DIR, OVERRIDES_FILE)
    if not os.path.exists(overrides_path):
        return {}
    try:
        with open(overrides_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


BANDCAMP_OVERRIDES = load_bandcamp_overrides()


def bandcamp_item_url(item_type, item_id, title, subdomain, artist_name=""):
    """
    Rakentaa Bandcamp-linkin.
    1. Käyttää overridea jos löytyy (bandcamp_urls.json)
    2. Slug otsikosta
    3. Fallback: numeerinen item_id
    """
    # 1. Tarkista override
    if artist_name and artist_name in BANDCAMP_OVERRIDES:
        artist_overrides = BANDCAMP_OVERRIDES[artist_name]
        if title in artist_overrides:
            return artist_overrides[title]

    # 2. Slug otsikosta
    path = "track" if item_type == "track" else "album"
    if title:
        slug = slugify(title)
        if slug:
            return f"https://{subdomain}.bandcamp.com/{path}/{slug}"

    # 3. Fallback: item_id
    if not item_id:
        return ""

    return f"https://{subdomain}.bandcamp.com/{path}/{item_id}"


def spotify_largest_image(images):
    """Valitsee Spotifyn kuvataulukosta suurimman."""
    if not images:
        return ""
    largest = max(images, key=lambda x: x.get("width", 0) or 0)
    return largest.get("url", "")


def spotify_upgrade_cover(url):
    """Pakottaa Spotify-kuvan 640×640 -kokoon."""
    if not url:
        return ""
    return (url
            .replace("ab67616d0000b273", "ab67616d00001e02")
            .replace("ab67616d00004851", "ab67616d00001e02"))


def download_cover(url, title):
    """Lataa kansikuvan paikallisesti. Ohittaa jos jo olemassa."""
    if not url:
        return ""

    if url.startswith("images/"):
        return url

    covers_dir = os.path.join(BASE_DIR, COVERS_DIR)
    os.makedirs(covers_dir, exist_ok=True)

    ext = ".jpg"
    hash_part = hashlib.md5(url.encode()).hexdigest()[:12]
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)
    filename = f"{safe_title}_{hash_part}{ext}"
    filepath = os.path.join(covers_dir, filename)

    if os.path.exists(filepath):
        log(f"↺ {filename} (jo olemassa)", "·")
        # Palauta suhteellinen polku sivustoa varten
        return f"{COVERS_DIR}/{filename}"

    try:
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
        log(f"⬇ {filename}", "·")
        return f"{COVERS_DIR}/{filename}"
    except Exception as e:
        log_err(f"Lataus epäonnistui: {title} ({e})")
        return url


def load_previous(file):
    """Lataa aiemman JSON-tiedoston — fallbackia varten."""
    path = os.path.join(BASE_DIR, file)
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ============================================
# SPOTIFY
# ============================================
def fetch_spotify(artist_name, artist_id, album_type):
    """Hakee Spotifysta joko albumit tai singlet tietylle artistille."""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID tai SPOTIFY_CLIENT_SECRET puuttuu. "
            f"Tarkista .env-tiedosto: {ENV_PATH}"
        )

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
            artist_id,
            album_type=album_type,
            limit=limit,
            offset=offset,
        )
        items = results.get("items", [])
        if not items:
            break

        for a in items:
            albums.append({
                "title": a["name"],
                "artist": artist_name,
                "release_date": a.get("release_date", ""),
                "cover": spotify_upgrade_cover(
                    spotify_largest_image(a.get("images", []))
                ),
                "spotify_url": a["external_urls"]["spotify"],
                "bandcamp_url": "",
                "platform": "spotify",
            })

        offset += limit

    return albums


# ============================================
# BANDCAMP
# ============================================
async def fetch_bandcamp(artist_name, bandcamp_id, subdomain, item_type):
    """Hakee Bandcampista joko albumit (album) tai trackit (track)."""
    async with BandcampAPIClient() as client:
        artist = await client.get_artist(int(bandcamp_id))
        discography = await client.get_artist_discography(artist.id)

    albums = []
    for item in discography:
        if item.get("item_type") != item_type:
            continue

        albums.append({
            "title": item.get("title", ""),
            "artist": artist_name,
            "release_date": parse_bandcamp_date(item.get("release_date", "")),
            "cover": bandcamp_cover_url(item.get("art_id")),
            "spotify_url": "",
            "bandcamp_url": bandcamp_item_url(
                item.get("item_type", "album"),
                item.get("item_id"),
                item.get("title", ""),
                subdomain,
                artist_name
            ),
            "platform": "bandcamp",
        })
    return albums


# ============================================
# YHDISTÄ
# ============================================
def normalize(title):
    return (title.lower().strip()
            .replace("(remastered", "")
            .replace("(original game soundtrack)", "")
            .replace("(deluxe edition)", "")
            .replace("  ", " ")
            .strip())


def merge_releases(spotify_list, bandcamp_list):
    """Yhdistää julkaisut artisti + normalisoitu nimi -avaimella."""
    merged = {}

    for a in spotify_list + bandcamp_list:
        key = f"{a['artist']}::{normalize(a['title'])}"
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


def fallback_from_previous(previous, artist_name):
    """Käyttää aiempaa dataa jos Bandcamp-haku epäonnistui tietylle artistille."""
    items = []
    for a in previous:
        if a.get("bandcamp_url") and a.get("artist") == artist_name:
            items.append({
                "title": a["title"],
                "artist": a["artist"],
                "release_date": a["release_date"],
                "cover": a["cover"],
                "spotify_url": "",
                "bandcamp_url": a["bandcamp_url"],
                "platform": "bandcamp",
            })
    return items


# ============================================
# PROCESS
# ============================================
def process(kind, spotify_type, bandcamp_type, output_file, step_num, step_total):
    """Hakee ja tallentaa joko albumit tai singlet molemmilta artisteilta."""
    all_releases = []
    output_path = os.path.join(BASE_DIR, output_file)

    for artist in ARTISTS:
        # Spotify
        log_step(step_num, step_total, f"{kind.capitalize()} — {artist['name']} (Spotify)")
        try:
            spotify = fetch_spotify(artist["name"], artist["spotify_id"], spotify_type)
            log_ok(f"Spotify: {len(spotify)} {kind}")
        except Exception as e:
            log_err(f"Spotify epäonnistui: {e}")
            spotify = []

        # Bandcamp
        log(f"Bandcamp: {artist['name']}...", "›")
        try:
            bandcamp = asyncio.run(
                fetch_bandcamp(
                    artist["name"],
                    artist["bandcamp_id"],
                    artist["bandcamp_subdomain"],
                    bandcamp_type,
                )
            )
            log_ok(f"Bandcamp: {len(bandcamp)} {kind}")
        except Exception as e:
            log_warn(f"Bandcamp epäonnistui: {e}")
            previous = load_previous(output_file)
            bandcamp = fallback_from_previous(previous, artist["name"])
            log(f"Aiemmasta datasta: {len(bandcamp)} {kind}", "↺")

        # Yhdistä
        log("Yhdistetään...", "🔀")
        merged = merge_releases(spotify, bandcamp)
        log_ok(f"Yhdistetty: {len(merged)} {kind}")
        all_releases.extend(merged)

    # Lajittele
    all_releases.sort(key=lambda x: x.get("release_date", ""), reverse=True)

    # Lataa kansikuvat
    print(f"\n📥 Ladataan kansikuvat {COVERS_DIR}/...", flush=True)
    for item in all_releases:
        local_path = download_cover(item["cover"], item["title"])
        item["cover"] = local_path

    # Tallenna
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_releases, f, ensure_ascii=False, indent=2)

    # Yhteenveto
    mpjv_count = sum(1 for r in all_releases if r["artist"] == "MpjV")
    iota_count = sum(1 for r in all_releases if r["artist"] == "Iota Dra")
    log_ok(f"Tallennettu {len(all_releases)} {kind} → {output_file}")
    log(f"MpjV: {mpjv_count}, Iota Dra: {iota_count}", "·")

    return len(all_releases)


# ============================================
# MAIN
# ============================================
def main():
    start_time = time.time()
    print_banner()

    # Tarkista .env ja Spotifyn avaimet
    if not os.path.exists(ENV_PATH):
        print(f"⚠️  .env-tiedostoa ei löytynyt: {ENV_PATH}")
        print("    Spotify-haut ohitetaan. Käytetään vain Bandcampia.")
        print()
    elif not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print(f"⚠️  SPOTIFY_CLIENT_ID tai SPOTIFY_CLIENT_SECRET puuttuu!")
        print(f"    Tarkista tiedosto: {ENV_PATH}")
        print("    Spotify-haut ohitetaan. Käytetään vain Bandcampia.")
        print()

    total_albums = 0
    total_tracks = 0

    # Vaihe 1: Albumit
    try:
        total_albums = process(
            "albumia", "album", "album", ALBUMS_FILE,
            step_num=1, step_total=2
        )
    except Exception as e:
        log_err(f"Albumeiden käsittely epäonnistui: {e}")

    # Vaihe 2: Singlet
    try:
        total_tracks = process(
            "singleä", "single", "track", TRACKS_FILE,
            step_num=2, step_total=2
        )
    except Exception as e:
        log_err(f"Singlejen käsittely epäonnistui: {e}")

    # Loppuyhteenveto
    elapsed = time.time() - start_time

    print()
    print("╔══════════════════════════════════════════╗")
    if total_albums or total_tracks:
        print("║   ✓ PÄIVITYS VALMIS                      ║")
    else:
        print("║   ⚠ PÄIVITYS EPÄONNISTUI                 ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  Albumeja: {total_albums}")
    print(f"  Singlejä: {total_tracks}")
    print(f"  Kesto: {elapsed:.1f} s")
    print(f"  Kansio: {BASE_DIR}")
    print()

    return 0 if (total_albums or total_tracks) else 1


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\n\n  ⚠ Keskeytetty käyttäjän toimesta.\n")
        exit_code = 130
    except Exception as e:
        print(f"\n\n  ✗ Odottamaton virhe: {e}\n")
        exit_code = 1

    # Pysäytä konsoli, jos ajetaan .exe:nä kaksoisklikkaamalla
    if getattr(sys, 'frozen', False) and "--no-pause" not in sys.argv:
        input("  Paina Enter sulkeaksesi...")

    sys.exit(exit_code)
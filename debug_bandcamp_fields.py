#!/usr/bin/env python3
"""Tulostaa Bandcamp-API:n palauttamat kentät."""

import asyncio
import os
import json
from dotenv import load_dotenv
from bandcamp_async_api import BandcampAPIClient

load_dotenv()
BANDCAMP_ARTIST = os.getenv("BANDCAMP_ARTIST")


async def main():
    async with BandcampAPIClient() as client:
        artist = await client.get_artist(int(BANDCAMP_ARTIST))
        discography = await client.get_artist_discography(artist.id)

    print(f"Albumeita: {len(discography)}")
    print()
    print("=== ENSIMMÄISEN ALBUMIN KAIKKI KENTÄT ===")
    print(json.dumps(discography[0], indent=2, default=str))
    print()
    print("=== AVAIMET ===")
    print(list(discography[0].keys()))


if __name__ == "__main__":
    asyncio.run(main())
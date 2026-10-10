#!/usr/bin/env python3
"""Debug: tulostaa Bandcamp-diskografian rakenteen."""

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

    print("MÄÄRÄ:", len(discography))
    print("TYYPPI:", type(discography[0]))
    print()
    print("=== ENSIMMÄINEN ALBUMI ===")
    print(json.dumps(discography[0], indent=2, default=str))
    print()
    print("=== KAIKKI AVAIMET ===")
    print(list(discography[0].keys()))


if __name__ == "__main__":
    asyncio.run(main())
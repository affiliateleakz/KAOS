"""Build a read-only, memory-mapped country index from public DB-IP Lite data.
No visitor addresses are sent to the upstream. Run offline when updating the release.
"""

import csv
import io
import ipaddress
import json
from pathlib import Path
import struct
import tempfile
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/api/analytics_data"
BASE = "https://raw.githubusercontent.com/sapics/ip-location-db/"
MAGIC = b"KAOSGEO1"


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        "https://api.github.com/repos/sapics/ip-location-db/commits?path=dbip-country&per_page=1",
        headers={"User-Agent": "KAOS-country-data-builder"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        commit = json.load(response)[0]
    revision = commit["sha"]
    counts = []
    with tempfile.TemporaryFile() as data:
        data.write(b"\0" * 24)
        for version in (4, 6):
            count = 0
            last = -1
            width = 4 if version == 4 else 16
            url = BASE + revision + f"/dbip-country/dbip-country-ipv{version}.csv"
            with urllib.request.urlopen(url, timeout=90) as response:
                for start, end, country in csv.reader(
                    io.TextIOWrapper(response, encoding="utf-8")
                ):
                    first = ipaddress.ip_address(start)
                    final = ipaddress.ip_address(end)
                    if (
                        first.version != version
                        or final.version != version
                        or int(first) <= last
                        or int(final) < int(first)
                    ):
                        raise ValueError("Invalid or overlapping source range")
                    if (
                        len(country) != 2
                        or not country.isascii()
                        or not country.isupper()
                    ):
                        raise ValueError("Invalid country")
                    data.write(first.packed + final.packed + country.encode("ascii"))
                    last = int(final)
                    count += 1
            counts.append(count)
        data.seek(0)
        data.write(MAGIC + struct.pack(">QQ", *counts))
        data.seek(0)
        output = OUT / "geo_country.bin"
        output.write_bytes(data.read())
    with urllib.request.urlopen(
        BASE + revision + "/dbip-country/DBIP-LICENSE", timeout=30
    ) as response:
        (OUT / "DBIP-LICENSE.txt").write_bytes(response.read())
    metadata = {
        "source": "DB-IP Lite via sapics/ip-location-db",
        "sourceUrl": "https://db-ip.com/",
        "upstreamRevision": revision,
        "upstreamUpdatedAt": commit["commit"]["author"]["date"],
        "builtAt": datetime.now(timezone.utc).isoformat(),
        "license": "CC BY 4.0",
        "attribution": "IP Geolocation by DB-IP",
        "ranges": counts,
        "bytes": output.stat().st_size,
    }
    (OUT / "country_source.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    build()

"""Country-only lookup using a compact local DB-IP Lite index; no network or raw-IP storage."""

import ipaddress
import json
import mmap
import os
from pathlib import Path
import struct
from functools import lru_cache

ROOT = Path(__file__).parent / "analytics_data"


@lru_cache(maxsize=1)
def _database():
    path = ROOT / "geo_country.bin"
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        data = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
    if len(data) < 24 or data[:8] != b"KAOSGEO1":
        data.close()
        return None
    ipv4, ipv6 = struct.unpack(">QQ", data[8:24])
    if len(data) != 24 + ipv4 * 10 + ipv6 * 34:
        data.close()
        return None
    return data, ipv4, ipv6


def country(address):
    try:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            return "ZZ"
        database = _database()
        if not database:
            return "ZZ"
        data, ipv4, ipv6 = database
        width, count, base = (
            (4, ipv4, 24) if ip.version == 4 else (16, ipv6, 24 + ipv4 * 10)
        )
        stride = 2 * width + 2
        key = ip.packed
        left, right = 0, count
        while left < right:
            middle = (left + right) // 2
            offset = base + middle * stride
            if data[offset : offset + width] <= key:
                left = middle + 1
            else:
                right = middle
        if left == 0:
            return "ZZ"
        offset = base + (left - 1) * stride
        return (
            data[offset + width * 2 : offset + stride].decode("ascii")
            if key <= data[offset + width : offset + width * 2]
            else "ZZ"
        )
    except (ValueError, TypeError, OSError, struct.error):
        return "ZZ"


def client_address(request):
    """Honor forwarding only from explicitly configured proxy CIDRs, right to left."""
    host = request.client.host if request and request.client else ""
    try:
        peer = ipaddress.ip_address(host)
        networks = [
            ipaddress.ip_network(c.strip())
            for c in os.getenv("KAOS_ANALYTICS_TRUSTED_PROXIES", "").split(",")
            if c.strip()
        ]
        trusted = lambda value: any(value in network for network in networks)
        if not trusted(peer):
            return str(peer)
        chain = request.headers.get("x-forwarded-for", "").split(",")
        if len(chain) > 16:
            return str(peer)
        for item in reversed(chain):
            current = ipaddress.ip_address(item.strip())
            if not trusted(current):
                return str(current)
        return str(peer)
    except ValueError:
        return host


def source_info():
    try:
        return json.loads((ROOT / "country_source.json").read_text())
    except (OSError, ValueError):
        return {
            "source": "Country data not installed",
            "sourceUrl": "https://db-ip.com/",
        }

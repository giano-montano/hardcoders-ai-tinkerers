"""Bounded official-source reads with private disk cache; no model calls."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://ms-opm.minsa.gob.pe/msopmcovid"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/131.0.0.0 Safari/537.36"),
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://opm-digemid.minsa.gob.pe",
    "Referer": "https://opm-digemid.minsa.gob.pe/",
}


class Client:
    def __init__(self, root, ttl=900, timeout=15, retries=2):
        self.root = root / "ingest-cache"
        self.ttl, self.timeout, self.retries = ttl, timeout, retries
        self.requests = self.hits = 0
        self.last_request = 0.0

    def post(self, route, query):
        body = json.dumps({"filtro": query}, sort_keys=True, separators=(",", ":")).encode()
        key = hashlib.sha256(route.encode() + body).hexdigest()
        path = self.root / (key + ".json")
        try:
            cached = json.loads(path.read_text())
            if self.ttl > 0 and 0 <= time.time() - cached["at"] < self.ttl:
                self.hits += 1
                return cached["response"], cached["at"]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        for attempt in range(self.retries + 1):
            time.sleep(max(0, 0.4 - (time.monotonic() - self.last_request)))
            self.requests += 1
            self.last_request = time.monotonic()
            request = urllib.request.Request(BASE + "/" + route, data=body, headers=HEADERS)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    # Decimal input strings preserve money without binary float conversion.
                    data = json.load(response, parse_float=str)
                if not isinstance(data, dict) or data.get("codigo") != "00":
                    raise ValueError("DIGEMID returned an invalid or unsuccessful response")
                stamp = time.time()
                self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
                temp = path.with_suffix(f".{os.getpid()}.tmp")
                with open(temp, "w", encoding="utf-8", opener=lambda p, f: os.open(p, f, 0o600)) as output:
                    json.dump({"at": stamp, "response": data}, output, ensure_ascii=False)
                os.replace(temp, path)
                return data, stamp
            except urllib.error.HTTPError as exc:
                code = exc.code
                exc.close()
                if code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise ValueError(f"DIGEMID HTTP {code}") from None
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == self.retries:
                    raise ValueError("DIGEMID network timeout or connection failure") from None
            if attempt < self.retries:
                time.sleep(2 ** attempt)
        raise ValueError("DIGEMID request failed")

import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from medisaving.ingest.client import Client


class ClientTests(unittest.TestCase):
    def test_cache_reuses_exact_query_and_keeps_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.urlopen") as urlopen:
            urlopen.return_value = io.BytesIO(b'{"codigo":"00","data":[{"precio2":1.23}]}')
            first = Client(Path(tmp))
            response, stamp = first.post("test", {"x": 1})
            second = Client(Path(tmp))
            cached, cached_stamp = second.post("test", {"x": 1})
            self.assertEqual((response, stamp), (cached, cached_stamp))
            self.assertEqual(cached["data"][0]["precio2"], "1.23")
            self.assertEqual(second.requests, 0)
            self.assertEqual(second.hits, 1)

    def test_fresh_does_not_reuse_cache(self):
        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.urlopen", side_effect=lambda *a, **kw: io.BytesIO(b'{"codigo":"00","data":[]}')) as call:
            Client(Path(tmp)).post("test", {})
            client = Client(Path(tmp), ttl=0)
            client.post("test", {})
            self.assertEqual(call.call_count, 2)

    def test_forbidden_not_retried_and_transient_retry_bounded(self):
        with tempfile.TemporaryDirectory() as tmp, patch("time.sleep"), patch("urllib.request.urlopen", side_effect=HTTPError("x", 403, "", {}, None)) as call:
            with self.assertRaisesRegex(ValueError, "403"):
                Client(Path(tmp)).post("test", {})
            self.assertEqual(call.call_count, 1)
        with tempfile.TemporaryDirectory() as tmp, patch("time.sleep"), patch("urllib.request.urlopen", side_effect=URLError("network")) as call:
            with self.assertRaisesRegex(ValueError, "network"):
                Client(Path(tmp)).post("test", {})
            self.assertEqual(call.call_count, 3)

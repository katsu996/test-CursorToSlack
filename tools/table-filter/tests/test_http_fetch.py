from __future__ import annotations

import unittest
from unittest import mock

from http_fetch import fetch_bytes


class TestHttpFetch(unittest.TestCase):
    @mock.patch("http_fetch.urllib.request.urlopen")
    @mock.patch("http_fetch.time.sleep", autospec=True)
    def test_retries_then_success(self, _sleep: mock.MagicMock, urlopen: mock.MagicMock) -> None:
        resp = mock.Mock()
        resp.read.return_value = b'{"ok":true}'
        ctx = mock.Mock()
        ctx.__enter__ = mock.Mock(return_value=resp)
        ctx.__exit__ = mock.Mock(return_value=False)
        urlopen.side_effect = [TimeoutError("a"), TimeoutError("b"), ctx]
        out = fetch_bytes("https://example.invalid/test.json", retries=3, backoff_seconds=0.01)
        self.assertEqual(out, b'{"ok":true}')
        self.assertEqual(urlopen.call_count, 3)


if __name__ == "__main__":
    unittest.main()

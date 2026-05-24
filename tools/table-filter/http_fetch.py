"""HTTP 取得（リトライ・タイムアウト・ログ付き）。標準ライブラリのみ。"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request

DEFAULT_USER_AGENT = "beatoraja-table-filter/1.0 (GitHub Actions; +https://github.com)"


def fetch_bytes(
    url: str,
    *,
    timeout: float = 120.0,
    retries: int = 3,
    backoff_seconds: float = 2.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> bytes:
    """
    指定 URL を GET して本文バイト列を返す。
    失敗時は指数バックオフで最大 retries 回まで再試行する。
    """
    last_err: BaseException | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (TimeoutError, OSError, urllib.error.HTTPError, urllib.error.URLError) as e:
            last_err = e
            if attempt >= retries:
                break
            wait = backoff_seconds ** (attempt - 1)
            print(
                f"警告: URL 取得失敗（{attempt}/{retries}）: {url}\n"
                f"  種類: {type(e).__name__} 内容: {e}\n"
                f"  {wait:.1f} 秒待って再試行します。",
                file=sys.stderr,
            )
            time.sleep(wait)
    assert last_err is not None
    print(
        f"エラー: URL 取得に {retries} 回失敗しました: {url}\n"
        f"  最終例外: {type(last_err).__name__}: {last_err}",
        file=sys.stderr,
    )
    raise last_err

import re
from typing import Any, Dict, Optional

import requests


class SafeRequestsWrapper:
    def __init__(self, headers: Optional[Dict[str, str]] = None, timeout: int = 60):
        self._session = requests.Session()
        self._base_headers = headers or {}
        self._timeout = timeout

    @staticmethod
    def _sanitize_url(url: str) -> str:
        # Extract the first real URL if extra prose or code fences are present
        if not isinstance(url, str):
            return url
        match = re.search(r"https?://[^\s`'\"]+", url)
        if match:
            return match.group(0)
        return url.strip().strip('`').splitlines()[0].strip()

    def _merge_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        merged.update(self._session.headers)
        merged.update(self._base_headers)
        if headers:
            merged.update(headers)
        return merged

    def request(self, method: str, url: str, **kwargs: Any):
        clean_url = self._sanitize_url(url)
        headers = self._merge_headers(kwargs.pop("headers", None))
        timeout = kwargs.pop("timeout", self._timeout)
        return self._session.request(method=method, url=clean_url, headers=headers, timeout=timeout, **kwargs)

    def get(self, url: str, **kwargs: Any):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any):
        return self.request("POST", url, **kwargs)

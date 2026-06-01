import httpx
from typing import List
from .base_provider import BaseProvider

FREE_BASE = "https://api-free.deepl.com/v2"
PRO_BASE  = "https://api.deepl.com/v2"


class DeepLProvider(BaseProvider):
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = FREE_BASE if api_key.endswith(":fx") else PRO_BASE

    def _headers(self):
        return {"Authorization": f"DeepL-Auth-Key {self.api_key}"}

    def translate(self, texts: List[str]) -> List[str]:
        if not texts:
            return []
        r = httpx.post(
            f"{self.base_url}/translate",
            headers=self._headers(),
            json={"text": texts, "target_lang": "EN"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return [t["text"] for t in r.json()["translations"]]

    def test_connection(self) -> dict:
        try:
            r = httpx.get(f"{self.base_url}/usage", headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            d = r.json()
            used, limit = d.get("character_count", 0), d.get("character_limit", 0)
            return {"ok": True, "message": "Connected",
                    "quota": f"{limit - used:,} / {limit:,} chars remaining"}
        except httpx.HTTPStatusError as e:
            return {"ok": False, "message": f"HTTP {e.response.status_code}", "quota": None}
        except Exception as e:
            return {"ok": False, "message": str(e), "quota": None}

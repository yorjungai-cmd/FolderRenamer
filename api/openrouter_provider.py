import httpx
from typing import List
from .base_provider import BaseProvider

BASE_URL = "https://openrouter.ai/api/v1"
SYSTEM_PROMPT = (
    "You are a filename translator. Translate Japanese text segments to English. "
    "Preserve spacing and structure. Return only the translated text, "
    "one line per input, same order."
)


class OpenRouterProvider(BaseProvider):
    def __init__(self, api_key: str, model: str, timeout: int = 30):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def translate(self, texts: List[str]) -> List[str]:
        if not texts:
            return []
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
        r = httpx.post(
            f"{BASE_URL}/chat/completions",
            headers=self._headers(),
            json={"model": self.model,
                  "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": numbered}]},
            timeout=self.timeout,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        lines = [ln.lstrip("0123456789. ").strip()
                 for ln in content.strip().splitlines() if ln.strip()]
        while len(lines) < len(texts):
            lines.append(texts[len(lines)])
        return lines[:len(texts)]

    def list_models(self) -> List[str]:
        r = httpx.get(f"{BASE_URL}/models", headers=self._headers(), timeout=self.timeout)
        r.raise_for_status()
        return sorted(m["id"] for m in r.json().get("data", []))

    def test_connection(self) -> dict:
        try:
            models = self.list_models()
            return {"ok": True, "message": f"Connected — {len(models)} models available", "quota": None}
        except httpx.HTTPStatusError as e:
            return {"ok": False, "message": f"HTTP {e.response.status_code}", "quota": None}
        except Exception as e:
            return {"ok": False, "message": str(e), "quota": None}

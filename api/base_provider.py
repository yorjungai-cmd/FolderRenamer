from abc import ABC, abstractmethod
from typing import List


class BaseProvider(ABC):
    @abstractmethod
    def translate(self, texts: List[str]) -> List[str]: ...

    @abstractmethod
    def test_connection(self) -> dict:
        """Returns {'ok': bool, 'message': str, 'quota': str | None}"""
        ...

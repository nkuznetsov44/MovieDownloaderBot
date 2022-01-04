from typing import Optional, TypeVar, Generic
from abc import ABC, abstractmethod


T = TypeVar('T')


class IParsedMessage(Generic[T]):
    def __init__(self, original_text: str, data: T) -> None:
        self.original_text = original_text
        self.data = data


class IMessageParser(ABC, Generic[T]):
    @abstractmethod
    def parse(self, message_text: str) -> Optional[IParsedMessage[T]]:
        """Returnes parsed object or None if parsing failed."""

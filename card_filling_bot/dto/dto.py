from typing import Optional
from dataclasses import dataclass


@dataclass
class FillDto:
    id: Optional[int]
    amount: str
    description: Optional[str]
    category_name: Optional[str]

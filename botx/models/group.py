from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Group:
    name: str
    id: int

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Group:
    name: str
    id: int

    def __str__(self):
        return f"{self.name}({self.id})"

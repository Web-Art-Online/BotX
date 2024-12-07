from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Group:
    name: str
    id: int

    def __str__(self):
        return f"{self.name}({self.id})"

    def __eq__(self, value):
        return isinstance(value, Group) and self.id == value.id

    def __hash__(self):
        return hash(self.id)

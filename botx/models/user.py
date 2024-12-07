from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    nickname: str
    user_id: int

    def __str__(self):
        return f"{self.nickname}({self.user_id})"

    def __eq__(self, value):
        return isinstance(value, User) and self.user_id == value.user_id

    def __hash__(self):
        return hash(self.user_id)

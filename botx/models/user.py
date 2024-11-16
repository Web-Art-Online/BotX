from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    nickname: str
    user_id: int

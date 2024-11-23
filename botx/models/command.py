from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Command:
    names: list[str]

    func: Callable

    private: bool
    group: bool
    admin: bool

    help_msg: str

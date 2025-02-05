from dataclasses import dataclass
from typing import Callable


@dataclass
class Command:
    names: list[str]

    func: Callable

    cmd_type: type
    admin: bool
    help_msg: str
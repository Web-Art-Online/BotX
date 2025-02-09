from dataclasses import dataclass
from typing import Callable

from .message import Message, GroupMessage

@dataclass
class Command:
    names: list[str]

    func: Callable

    cmd_type: type
    admin: bool
    help_msg: str
    targets: list[str | int]
    
    def is_target(self, msg: Message):
        if not self.targets:
            return True
        if isinstance(msg, GroupMessage):
            is_target = any(map(lambda t: t == f"g{msg.group_id}" or t == msg.group_id, self.targets))
        else:
            is_target = any(map(lambda t: t == f"p{msg.sender.user_id}" or t == msg.sender.user_id, self.targets))
        return is_target
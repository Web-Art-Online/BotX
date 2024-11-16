from dataclasses import dataclass
from dataclasses_json import dataclass_json
import inspect


@dataclass(frozen=True, slots=True)
class Notice:
    self_id: int
    time: int
    notice_type = "notice"


@dataclass_json
@dataclass(frozen=True, slots=True)
class Recall(Notice):
    user_id: int
    message_id: int


@dataclass_json
@dataclass(frozen=True, slots=True)
class PrivateRecall(Recall):
    notice_type = "friend_recall"


@dataclass_json
@dataclass(frozen=True, slots=True)
class GroupRecall(Recall):
    notice_type = "group_recall"

    group_id: int
    operator_id: int


notices = [
    clazz
    for _, clazz in globals().items()
    if inspect.isclass(clazz) and clazz.__module__ == __name__
]

print(notices)

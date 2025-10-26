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


@dataclass_json
@dataclass(frozen=True, slots=True)
class FriendAdd(Notice):
    notice_type = "friend_add"

    user_id: int


@dataclass_json
@dataclass(frozen=True, slots=True)
class GroupIncrease(Notice):
    notice_type = "group_increase"

    sub_type: str
    """ approve, invite 分别表示管理员已同意入群, 管理员邀请入群 """
    group_id: int
    operator_id: int
    user_id: int


@dataclass_json
@dataclass(frozen=True, slots=True)
class GroupDecrease(Notice):
    notice_type = "group_decrease"

    sub_type: str
    """ leave, kick, kick_me 分别表示主动退群, 成员被踢, 登录号被踢 """
    group_id: int
    operator_id: int
    user_id: int


@dataclass_json
@dataclass(frozen=True, slots=True)
class EmojiLike(Notice):
    notice_type = "group_msg_emoji_like"

    user_id: int
    group_id: int
    likes: list["EmojiLike.Likes"]

    @dataclass_json
    @dataclass
    class Likes:
        emoji_id: int
        count: int


notices = [
    clazz
    for _, clazz in globals().items()
    if inspect.isclass(clazz) and clazz.__module__ == __name__
]

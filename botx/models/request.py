from dataclasses import dataclass
from dataclasses_json import dataclass_json
import inspect


@dataclass_json
@dataclass(frozen=True, slots=True)
class Request:
    self_id: int
    time: int
    request_type = "request"


@dataclass_json
@dataclass(frozen=True, slots=True)
class FriendRequest(Request):
    request_type = "friend"

    user_id: int
    comment: str
    flag: str

    async def result(self, approve: bool, remark: str = None):
        from botx.bot import get_bot

        await get_bot(self.self_id).call_api(
            "set_friend_add_request",
            {
                "flag": self.flag,
                "approve": approve,
                "remark": remark,
            },
        )


@dataclass_json
@dataclass(frozen=True, slots=True)
class GroupRequest(Request):
    request_type = "group"

    sub_type: str
    """ add, invite 分别表示加群请求, 邀请登录号入群 """
    group_id: int
    user_id: int
    comment: str
    flag: str

    async def result(self, approve: bool, reason: str = None):
        from botx.bot import get_bot

        await get_bot(self.self_id).call_api(
            "set_group_add_request",
            {
                "flag": self.flag,
                "sub_type": self.sub_type,
                "approve": approve,
                "reason": reason,
            },
        )


requests = [
    clazz
    for _, clazz in globals().items()
    if inspect.isclass(clazz) and clazz.__module__ == __name__
]

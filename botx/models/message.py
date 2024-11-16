from dataclasses import dataclass
from dataclasses_json import dataclass_json

from botx.models.user import User


@dataclass_json
@dataclass(frozen=True, slots=True)
class Message:
    self_id: int
    time: int

    message_id: int
    sender: User

    message: dict | list
    raw_message: str

    async def reply(self, msg: str):
        pass


@dataclass_json
@dataclass(frozen=True, slots=True)
class PrivateMessage(Message):

    async def reply(self, msg: str) -> int | None:
        from botx.bot import get_bot

        return await get_bot(self.self_id).send_private(
            user=self.sender, msg=f"[CQ:reply,id={self.message_id}]{msg}"
        )


@dataclass_json
@dataclass(frozen=True, slots=True)
class GroupMessage(Message):
    group_id: int

    async def reply(self, msg: str) -> int | None:
        from botx.bot import get_bot

        return await get_bot(self.self_id).send_group(
            group=self.group_id, msg=f"[CQ:reply,id={self.message_id}]{msg}"
        )

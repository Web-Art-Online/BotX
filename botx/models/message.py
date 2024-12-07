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

    def __eq__(self, value):
        return (
            isinstance(value, Message)
            and self.message_id == value.message_id
            and self.sender == value.sender
            and self.self_id == value.self_id
        )

    def __hash__(self):
        return hash((self.message_id, self.sender, self.self_id))


@dataclass_json
@dataclass(frozen=True, slots=True)
class PrivateMessage(Message):

    async def reply(self, msg: str) -> int | None:
        from botx.bot import get_bot

        return await get_bot(self.self_id).send_private(
            user=self.sender, msg=f"[CQ:reply,id={self.message_id}]{msg}"
        )

    def __eq__(self, value):
        return (
            isinstance(value, PrivateMessage)
            and self.message_id == value.message_id
            and self.sender == value.sender
            and self.self_id == value.self_id
        )

    def __hash__(self):
        return hash((self.message_id, self.sender, self.self_id, 0))


@dataclass_json
@dataclass(frozen=True, slots=True)
class GroupMessage(Message):
    group_id: int

    async def reply(self, msg: str) -> int | None:
        from botx.bot import get_bot

        return await get_bot(self.self_id).send_group(
            group=self.group_id, msg=f"[CQ:reply,id={self.message_id}]{msg}"
        )

    def __eq__(self, value):
        return (
            isinstance(value, GroupMessage)
            and self.message_id == value.message_id
            and self.sender == value.sender
            and self.self_id == value.self_id
            and self.group_id == value.group_id
        )

    def __hash__(self):
        return hash((self.message_id, self.sender, self.self_id, self.group_id))

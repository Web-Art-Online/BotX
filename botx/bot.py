import asyncio
from dataclasses import fields
import inspect
import json
import logging
from typing import Callable, Type
import uuid
import websockets

import botx.logging
from botx.models import *
from botx.models.notice import notices
from botx.models.request import requests

_instances: dict[int, "Bot"] = {}


def get_bot(id: int) -> "Bot":
    return _instances.get(id)


class Bot:
    ws_uri: str
    cmd_prefix: list[str]
    me: User
    msg_cd: int
    log_level: str
    __running: bool = False
    __queue: asyncio.Queue
    __futures: dict[str, asyncio.Future]
    __commands: list[Command]
    __cmd_names: list[str]
    __notice_handlers: dict[Type[Notice], list[Callable]]
    __message_handlers: dict[Type[Message], list[Callable]]
    __request_handlers: dict[Type[Request], list[Callable]]
    __online: bool

    def __init__(self, ws_uri: str, cmd_prefix: list[str] = ["#"], msg_cd: float = 0.1, log_level = "INFO"):
        self.ws_uri = ws_uri

        self.cmd_prefix = cmd_prefix
        self.me = None
        self.__queue = asyncio.Queue()
        self.__futures = {}
        self.__commands = []
        self.__cmd_names = []
        self.__notice_handlers = {}
        self.__message_handlers = {}
        self.__request_handlers = {}
        self.__online = True
        self.msg_cd = msg_cd
        self.log_level = log_level
        
        @self.on_cmd("帮助", help_msg="给你看帮助的")
        async def help(msg: Message):
            await msg.reply(f"✨指令列表✨\n" + "\n".join(map(lambda c: f"{",".join(c.names)}: {c.help_msg}", self.__commands)))
    

    async def start(self):
        if self.__running == True:
            raise RuntimeError("该 Bot 实例已经被启动了!")
        self.__running = True
        self.getLogger().info("开始启动...")

        async def sender(ws):
            while True:
                data = await self.__queue.get()
                await ws.send(json.dumps(data))
                await asyncio.sleep(self.msg_cd)

        async def receiver(ws):
            while True:
                data: dict = json.loads(await ws.recv())
                self.getLogger().debug(data)
                if "echo" in data:
                    future = self.__futures.get(data["echo"])
                    if future == None:
                        self.getLogger().warning(
                            f"Onebot 发送了了无效的 echo: {data["echo"]}"
                        )
                        continue
                    future.set_result(data)
                    self.__futures.pop(data["echo"])
                else:
                    match (data["post_type"]):
                        case "message":
                            msg: Message
                            if data["message_type"] == "private":
                                msg = PrivateMessage.from_dict(data)
                            else:
                                msg = GroupMessage.from_dict(data)
                            asyncio.create_task(self.__handle_message(msg))
                        case "meta_event":
                            if data["meta_event_type"] == "heartbeat":
                                if data["status"]["online"] != self.__online:
                                    self.__online = data["status"]["online"]
                                    self.getLogger().info(
                                        f"当前在线状态改变: {"在线" if  self.__online else "离线"}"
                                    )
                            elif data["sub_type"] == "connect":
                                id = data["self_id"]
                                _instances[id] = self

                                def callback(f: asyncio.Future):
                                    nickname = f.result()["data"]["nickname"]
                                    self.me = User(nickname=nickname, user_id=id)
                                    self.getLogger().info(
                                        f"当前机器人账号: {nickname}({id})"
                                    )

                                (await self.__send("get_login_info")).add_done_callback(
                                    callback
                                )
                        case "message_sent":
                            pass
                        case "notice":
                            for clazz in notices:
                                if clazz.notice_type == data["notice_type"]:
                                    for base in clazz.__bases__ + (clazz,):
                                        for h in self.__notice_handlers.get(base, []):
                                            if inspect.iscoroutinefunction(h):
                                                asyncio.create_task(
                                                    h(clazz.from_dict(data))
                                                )
                                            else:
                                                asyncio.create_task(asyncio.to_thread(h, clazz.from_dict(data)))
                        case "request":
                            for clazz in requests:
                                if clazz.request_type == data["request_type"]:
                                    for base in clazz.__bases__ + (clazz,):
                                        for h in self.__request_handlers.get(base, []):
                                            if inspect.iscoroutinefunction(h):
                                                asyncio.create_task(
                                                    h(clazz.from_dict(data))
                                                )
                                            else:
                                                asyncio.create_task(asyncio.to_thread(h, clazz.from_dict(data)))
                        case _:
                            self.getLogger().warning("Onebot 上报了未知事件.")

        async for ws in websockets.connect(uri=self.ws_uri):
            self.getLogger().info(f"连接至 Onebot: {self.ws_uri}")
            try:
                await asyncio.gather(sender(ws), receiver(ws))
            except websockets.ConnectionClosed:
                self.getLogger().error("与 Onebot 的 Websocket 连接断开")
                self.getLogger().warning("5s后将尝试重新连接...")
                await asyncio.sleep(5)
                self.getLogger().warning("尝试重新连接...")

    async def __send(self, action: str, params: dict | None = None) -> asyncio.Future:
        echo = uuid.uuid4().hex
        self.__futures[echo] = asyncio.Future()
        await self.__queue.put({"action": action, "params": params, "echo": echo})
        return self.__futures[echo]

    async def call_api(self, action: str, params: dict | None = None) -> dict:
        return await (await self.__send(action=action, params=params))

    async def __handle_message(self, msg: Message):
        parts = msg.raw_message.split(" ")
        if msg.raw_message[0] in self.cmd_prefix:
            # 是指令
            flag = False
            for cmd in self.__commands:
                if parts[0][1:] in cmd.names and (
                    (isinstance(msg, GroupMessage) and cmd.group)
                    or (isinstance(msg, PrivateMessage) and cmd.private)
                ):
                    flag = True
                    self.getLogger().debug(f"执行指令 {msg.raw_message}")
                    params = {}
                    for k, v in cmd.func.__annotations__.items():
                        if issubclass(v, Message):
                            params[k] = msg
                    if inspect.iscoroutinefunction(cmd.func):
                        asyncio.create_task(cmd.func(**params))
                    else:
                        asyncio.create_task(asyncio.to_thread(cmd.func, **params))
            if not flag:
                await msg.reply(f"未知指令. 请发送 {self.cmd_prefix[0]}帮助 看看怎么使用.")
        else:
            await asyncio.gather(
                *map(
                    lambda h: h(msg),
                    self.__message_handlers.get(Message, [])
                    + self.__message_handlers.get(type(msg), []),
                ),
                return_exceptions=True
            )
        await self.call_api(
            action="mark_msg_as_read", params={"message_id": msg.message_id}
        )

    def on_cmd(
        self,
        name: str | list[str],
        admin: bool = False,
        help_msg: str = "开发者很懒, 没有添加描述哦~"
    ):
        if not help_msg:
            raise ValueError("帮助文本不能为 None")
        if not name:
            raise ValueError("指令名不能为 None")
        name = [name] if isinstance(name, str) else name

        def f(func: Callable):
            if len(func.__annotations__) != 1:
                raise ValueError("处理函数必须只有一个参数")
            msg_type = list(func.__annotations__.values())[0]

            if any(map(lambda n: n in self.__cmd_names, name)):
                raise ValueError("指令名重复")
            self.__cmd_names.append(name)
            self.__commands.append(
                Command(
                    names=name,
                    func=func,
                    private=msg_type == PrivateMessage or msg_type == Message,
                    group=msg_type == GroupMessage or msg_type == Message,
                    admin=admin,
                    help_msg=help_msg
                )
            )
            self.getLogger().debug(
                f'加载指令: {name} "{func.__code__.co_filename}", line {func.__code__.co_firstlineno + 1}'
            )

        return f

    def on_notice(self):
        def f(func: Callable):
            if len(func.__annotations__) != 1:
                raise ValueError("处理函数必须只有一个参数")
            notice_type = list(func.__annotations__.values())[0]
            if not issubclass(notice_type, Notice):
                raise ValueError(f"参数必须是 Notice 的子类, 实际是{notice_type}")
            handlers = self.__notice_handlers.get(notice_type, [])
            handlers.append(func)
            self.__notice_handlers[notice_type] = handlers

        return f

    def on_msg(self):
        def f(func: Callable):
            if len(func.__annotations__) != 1:
                raise ValueError("处理函数必须只有一个参数")
            msg_type = list(func.__annotations__.values())[0]
            if not issubclass(msg_type, Message):
                raise ValueError(f"参数必须是 Message 的子类, 实际是{msg_type}")
            handlers = self.__message_handlers.get(msg_type, [])
            handlers.append(func)
            self.__message_handlers[msg_type] = handlers

        return f
    
    def on_request(self):
        def f(func: Callable):
            if len(func.__annotations__) != 1:
                raise ValueError("处理函数必须只有一个参数")
            request_type = list(func.__annotations__.values())[0]
            if not issubclass(request_type, Request):
                raise ValueError(f"参数必须是 Request 的子类, 实际是{request_type}")
            handlers = self.__request_handlers.get(request_type, [])
            handlers.append(func)
            self.__request_handlers[request_type] = handlers
            
        return f

    async def send_private(
        self, user: User | int, msg: str | dict, auto_escape: bool = False
    ) -> int | None:
        resp = await self.call_api(
            "send_private_msg",
            {
                "user_id": user.user_id if isinstance(user, User) else user,
                "message": msg,
                "auto_escape": auto_escape,
            },
        )
        return resp["data"]["message_id"] if resp["status"] == "ok" else None

    async def send_group(
        self, group: int, msg: str | dict, auto_escape: bool = False
    ) -> int | None:
        resp = await self.call_api(
            "send_group_msg",
            {
                "group_id": group,
                "message": msg,
                "auto_escape": auto_escape,
            },
        )

        return resp["data"]["message_id"] if resp["status"] == "ok" else None

    async def get_msg(self, id: int) -> Message:
        resp = await self.call_api("get_msg", {"message_id": id})
        if resp["data"]["message_type"] == "private":
            return PrivateMessage.from_dict(resp["data"])
        else:
            return GroupMessage.from_dict(resp["data"])

    def getLogger(self) -> logging.Logger:
        return botx.logging.getLogger(name="Core" if self.me == None else self.me.user_id, level=self.log_level)

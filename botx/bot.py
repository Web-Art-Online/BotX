import asyncio
import inspect
import json
import logging
import sys
from typing import Callable, Type
import uuid
import websockets

import botx.logging
from botx.models import *
from botx.models.notice import notices
from botx.models.request import requests
from botx.qzone import Qzone

_instances: dict[int, "Bot"] = {}


def get_bot(id: int) -> "Bot":
    return _instances.get(id)


class Bot:
    ws_uri: str
    __token: str
    
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
    __error_handlers: list[Callable]
    __online: bool
    __tasks: dict[str, dict]

    def __init__(self, ws_uri: str, *, token: str | None = None, cmd_prefix: list[str] = ["#"], msg_cd: float = 0.1, log_level = "INFO"):
        self.ws_uri = ws_uri
        self.__token = token

        self.cmd_prefix = cmd_prefix
        self.me = None
        self.__queue = asyncio.Queue()
        self.__futures = {}
        self.__commands = []
        self.__cmd_names = []
        self.__notice_handlers = {}
        self.__message_handlers = {}
        self.__request_handlers = {}
        self.__error_handlers = []
        self.__online = True
        self.__tasks = {}
        self.msg_cd = msg_cd
        self.log_level = log_level
        
        @self.on_cmd("帮助", help_msg="给你看帮助的")
        async def help(msg: Message):
            await msg.reply(f"✨指令列表✨\n\n" + "\n\n".join(map(lambda c: f"#{", #".join(c.names)}: {c.help_msg}", 
                                                        filter(lambda c: isinstance(msg, c.cmd_type), self.__commands))))
    

    async def start(self):
        if self.__running == True:
            raise RuntimeError("该 Bot 实例已经被启动了!")
        self.__running = True
        self.getLogger().info("开始启动...")
        
        def error(loop: asyncio.AbstractEventLoop, context: dict):
            self.getLogger().error(context)
            for h in self.__error_handlers:
                if inspect.iscoroutinefunction(h):
                    loop.create_task(h(context, self.__tasks[context["future"].get_name()]))
                else:
                    h(context, self.__tasks[context["future"].get_name()])
        asyncio.get_running_loop().set_exception_handler(error)

        async def sender(ws):
            while True:
                data = await self.__queue.get()
                await ws.send(json.dumps(data))
                await asyncio.sleep(self.msg_cd)

        async def event(data):
            match (data["post_type"]):
                case "message":
                    msg: Message
                    if data["message_type"] == "private":
                        msg = PrivateMessage.from_dict(data)
                    else:
                        msg = GroupMessage.from_dict(data)
                    parts = msg.raw_message.split(" ")
                    # 如果用户没有添加指令就不要执行了
                    if len(self.__commands) > 1 and msg.raw_message[0] in self.cmd_prefix:
                        # 是指令
                        flag = False
                        for cmd in self.__commands:
                            if parts[0][1:] in cmd.names and isinstance(msg, cmd.cmd_type):
                                flag = True
                                self.getLogger().debug(f"执行指令 {msg.raw_message}")
                                params = {}
                                for k, v in cmd.func.__annotations__.items():
                                    if issubclass(v, Message):
                                        params[k] = msg
                                if inspect.iscoroutinefunction(cmd.func):
                                    task = asyncio.create_task(cmd.func(**params))
                                else:
                                    task = asyncio.create_task(asyncio.to_thread(cmd.func, **params))
                                self.__tasks[task.get_name()] = data
                        if not flag:
                            await msg.reply(f"未知指令. 请发送 {self.cmd_prefix[0]}帮助 看看怎么使用.")
                    else:
                        for h in self.__message_handlers.get(Message, []) + self.__message_handlers.get(type(msg), []):
                            if inspect.iscoroutinefunction(h):
                                task = asyncio.create_task(h(msg))
                            else:
                                task = asyncio.create_task(asyncio.to_thread(h, msg))
                            self.__tasks[task.get_name()] = data
                    await self.call_api(
                        action="mark_msg_as_read", params={"message_id": msg.message_id}
                    )
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
                                        task = asyncio.create_task(
                                            h(clazz.from_dict(data))
                                        )
                                    else:
                                        task = asyncio.create_task(asyncio.to_thread(h, clazz.from_dict(data)))
                                    self.__tasks[task.get_name()] = data
                case "request":
                    for clazz in requests:
                        if clazz.request_type == data["request_type"]:
                            for base in clazz.__bases__ + (clazz,):
                                for h in self.__request_handlers.get(base, []):
                                    if inspect.iscoroutinefunction(h):
                                        task = asyncio.create_task(
                                            h(clazz.from_dict(data))
                                        )
                                    else:
                                        task = asyncio.create_task(asyncio.to_thread(h, clazz.from_dict(data)))
                                    self.__tasks[task.get_name()] = data
                case _:
                    self.getLogger().warning("Onebot 上报了未知事件.")


        async def receiver(ws):
            # 不要在 receiver 里面调用 call_api()
            while True:
                data: dict = json.loads(await ws.recv())
                self.getLogger().debug(data)
                if data["retcode"] == 1403:
                    self.getLogger().fatal("Access Token 错误")
                    sys.exit(-1)
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
                    asyncio.create_task(event(data))
            
        async for ws in websockets.connect(uri=self.ws_uri, additional_headers={"Authorization": f"Bearer {self.__token}"}):
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
                raise ValueError("处理函数必须只有1个参数")
            msg_type = list(func.__annotations__.values())[0]

            if any(map(lambda n: n in self.__cmd_names, name)):
                raise ValueError("指令名重复")
            self.__cmd_names.append(name)
            self.__commands.append(
                Command(
                    names=name,
                    func=func,
                    cmd_type=msg_type,
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
                raise ValueError("处理函数必须只有1个参数")
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
                raise ValueError("处理函数必须只有1个参数")
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
                raise ValueError("处理函数必须只有1个参数")
            request_type = list(func.__annotations__.values())[0]
            if not issubclass(request_type, Request):
                raise ValueError(f"参数必须是 Request 的子类, 实际是{request_type}")
            handlers = self.__request_handlers.get(request_type, [])
            handlers.append(func)
            self.__request_handlers[request_type] = handlers
            
        return f

    """ 第一个参数为 Eventloop 的 Context, 第二个参数为 Onebot 发送的数据 """
    def on_error(self):
        def f(func: Callable):
            if len(inspect.signature(func).parameters) != 2:
                raise ValueError("处理函数必须有2个参数")
            self.__error_handlers.append(func)
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

    async def get_qzone(self) -> Qzone:
        cookies = dict(
                c.split("=")
                for c in 
                (await self.call_api("get_cookies", {"domain": "user.qzone.qq.com"}))["data"]["cookies"]
                .replace(" ", "")
                .split(";")
            )
        return Qzone(uin=self.me.user_id, cookies=cookies)

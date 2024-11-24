import asyncio
import base64
import threading

from botx import Bot, QzoneImage, Qzone
from botx.models import *

bot = Bot("ws://localhost:3001", log_level="DEBUG")


def read_image(path: str) -> bytes:
    with open(path, mode="br") as f:
        return base64.b64encode(f.read())


@bot.on_cmd(["1", "2"], help_msg="123456")
async def f(msg: Message):
    print(threading.current_thread().name)
    print(await msg.reply("111"))
    q: Qzone = await bot.get_qzone()
    image = await q.upload_image(read_image("./tests/misaka.jpg"))
    print(await q.publish("misaka", [image]))


@bot.on_cmd("3")
async def f(msg: PrivateMessage):
    print(111)
    raise RuntimeError(111)


@bot.on_error()
async def e(c, d):
    print(c)
    print(d)


@bot.on_notice()
async def f(recall: PrivateRecall):
    await bot.send_private(
        user=recall.user_id, msg=f"[CQ:reply,id={recall.message_id}]撤回了啥"
    )
    raise RuntimeError()


@bot.on_request()
async def f(r: GroupRequest):
    await r.result(approve=False, reason="33333")


@bot.on_notice()
async def f(n: GroupIncrease):
    print(n.sub_type)


@bot.on_msg()
async def f(msg: Message):
    print(msg.message_id)


@bot.on_msg()
async def f(msg: PrivateMessage):
    print(msg.time)


async def main():
    await bot.start()


asyncio.run(main())

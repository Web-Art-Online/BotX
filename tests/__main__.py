import asyncio
import threading

from botx import Bot
from botx.models import *

bot = Bot("ws://localhost:3001", log_level="DEBUG")


@bot.on_cmd(["1", "2"])
async def f(msg: Message):
    print(threading.current_thread().name)
    print(await msg.reply("111"))
    raise RuntimeError("test")


@bot.on_notice()
async def f(recall: PrivateRecall):
    await bot.send_private(
        user=recall.user_id, msg=f"[CQ:reply,id={recall.message_id}]撤回了啥"
    )


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
    await asyncio.gather(bot.start())


asyncio.run(main())

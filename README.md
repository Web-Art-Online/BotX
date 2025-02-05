# BotX
> 基于 OneBot 11 标准实现的异步 Python 机器人框架

## 使用

> [!NOTE]  
你需要先学习 Python 的 `asyncio` 再来使用本库

在你的虚拟环境中安装

`$ pip install git+https://github.com/Web-Art-Online/BotX`

```python
import asyncio

from botx import Bot
from botx.models import Message, PrivateMessage, FriendRequest, GroupRecall

bot = Bot("ws://localhost:3001")

@bot.on_msg()
async def echo(msg: PrivateMessage):
    await msg.reply(msg.raw_message)

@bot.on_cmd("hi", help_msg="你好")
async def hi(msg: Message):
    await msg.reply("hi")

@bot.on_request()
async def friend(req: FriendRequest):
    await req.result(True)

@bot.on_notice()
async def recall(notice: GroupRecall):
    pass

asyncio.run(bot.start())
```
> [!IMPORTANT]  
> 这些装饰器所装饰的函数都必须是 `async` 的

## 开发进度
### 已支持的 Notice
* Recall (PrivateRecall, GroupRecall)
* FriendAdd
* GroupIncrease
* GroupDecrease
### 已支持的 Request (go-cqhttp的已全部支持)
* FriendRequest
* GroupRequest

## 免责声明
本项目为开源软件，遵循 LGPL v2 许可证发布。使用者可以自由地下载、修改和分发本项目的代码，但必须遵守以下条款：

* 禁止非法用途
本项目仅可用于合法用途。禁止将本项目用于任何违反法律法规的行为，包括但不限于:
    * 侵犯他人知识产权；
    * 传播恶意软件或病毒；
    * 进行网络攻击或其他非法活动。

* 作者免责  
本项目的作者和贡献者不对使用者的行为负责。使用者因使用、修改或分发本项目而产生的任何后果（包括但不限于法律纠纷、经济损失等），均由使用者自行承担，与作者和贡献者无关。

* 无担保声明  
本项目按“原样”提供，不提供任何形式的明示或暗示担保，包括但不限于对适用性、特定用途适用性、无病毒或无错误的担保。使用者需自行承担使用本项目的一切风险。

* 遵守当地法律  
使用者在下载、使用或分发本项目时，必须遵守所在国家或地区的法律法规。如果本项目的任何部分违反当地法律，使用者应立即停止使用。
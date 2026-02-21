import base64
import hashlib
import json
import os
import time
from wsgiref import headers

from httpx import AsyncClient


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

CHUNK_SIZE = 2 << 19


class Guild:
    uin: str
    cookies: dict
    client: AsyncClient

    def __init__(self, uin: str, cookies: dict):
        self.uin = uin
        self.cookies = cookies
        self.client = AsyncClient(
            base_url="https://pd.qq.com",
            cookies=cookies,
            headers={
                "Referer": "https://pd.qq.com/",
                "Origin": "https://pd.qq.com",
                "User-Agent": UA,
                "x-oidb": '{"uint32_service_type":10}',
                "x-qq-client-appid": "537246381",
                # "businuess_type": "1",
                # "agent_type": "34",
                # "appid": "1002",
            },
            timeout=60,
        )

    async def _apply_upload(self, sha1: str, size: int):
        resp = await self.client.post(
            "/proxy/domain/richmedia.qq.com/ApplySliceUpload",
            params={"bkn": self.get_bkn()},
            json={
                "appid": 1002,
                "agent_type": 34,
                "business_type": 1,
                "size": size,
                "is_origin": True,
                "is_try_full_upload": False,
                "sha1": sha1,
            },
        )
        return resp.json()["ukey"]

    async def _upload_slice(self, ukey: str, index: int, file_path: str) -> str | None:
        file_size = os.path.getsize(file_path)
        chuck_count = file_size // CHUNK_SIZE + (
            0 if file_size % CHUNK_SIZE == 0 else 1
        )
        with open(file_path, "rb") as f:
            f.seek(index * CHUNK_SIZE)
            data = f.read(CHUNK_SIZE)
        headers = self.client.headers.copy()
        headers.update(
            {
                "x-richmedia-range-start": str(index * CHUNK_SIZE),
                "x-richmedia-range-end": str(
                    min((index + 1) * CHUNK_SIZE - 1, file_size)
                ),
                "x-richmedia-ukey": ukey,
                "content-type": "application/octet-stream",
            }
        )
        if index == 0:
            headers["x-richmedia-cumulatesha1"] = json.dumps(
                ["1111111111111111111111111111111111111111"] * chuck_count
            )

        if (index + 1) * CHUNK_SIZE >= os.path.getsize(file_path):
            headers["x-richmedia-is-last-slice"] = "1"

        resp = await self.client.post(
            "/proxy/domain/richmedia.qq.com/UploadSliceData",
            params={"bkn": self.get_bkn(), "ukey": ukey[:12], "index": index},
            content=data,
            headers=headers,
        )
        # print(resp.request.headers)

        if resp.status_code != 200 or resp.json()["retcode"] != 0:
            raise Exception(f"Upload slice failed: {resp.text}")
        print(resp.text)
        return resp.json().get("extend_info")

    async def upload_image(self, file_path):
        sha1 = get_cumulative_sha1(file_path, os.path.getsize(file_path))
        file_size = os.path.getsize(file_path)
        ukey = await self._apply_upload(sha1, size=file_size)
        s = None
        for i in range(
            file_size // CHUNK_SIZE + (0 if file_size % CHUNK_SIZE == 0 else 1)
        ):
            s = await self._upload_slice(ukey, i, file_path)
        if s == None:
            raise RuntimeError("Upload slice failed")
        j = json.loads(base64.b64decode(s))
        return j["img_infos"][1]["img_url"]

    async def publish(
        self, text: str, guild_id: str, channel_id: str, images: list[str] = []
    ) -> str:
        image_list = []
        for i, img_url in enumerate(images):
            image_list.append(
                {
                    "display_index": i,
                    "url": img_url,
                    "picId": str(i),
                    "taskId": str(i),
                }
            )
        resp = await self.client.post(
            "/qunng/guild/gotrpc/auth/trpc.qchannel.commwriter.ComWriter/PublishFeed",
            params={"bkn": self.get_bkn()},
            json={
                "jsonFeed": json.dumps(
                    {
                        "channelInfo": {
                            "sign": {
                                "guild_id": guild_id,
                                "channel_id": channel_id,
                            }
                        },
                        "contents": {
                            "contents": [{"type": 1, "text_content": {"text": text}}]
                        },
                        "images": image_list,
                        "title": {},
                        "feedType": 1,
                    }
                ),
                "client_content": {
                    "clientImageContents": image_list,
                    "clientVideoContents": [],
                },
            },
        )
        return resp.json()["data"]["feed"]["id"]

    # 实则和 Qzone 的 g_tk 一样
    def get_bkn(self) -> str:
        p_skey = self.cookies["p_skey"]
        hash_val = 5381
        for i in range(len(p_skey)):
            hash_val += (hash_val << 5) + ord(p_skey[i])
        return str(hash_val & 2147483647)


def get_cumulative_sha1(file_path: str, end: int) -> str:
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        sha1.update(f.read(end))
    return sha1.hexdigest()

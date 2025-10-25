import json
import math
import time
import base64
import hashlib
import os
import random

from httpx import AsyncClient

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class QzoneImage:
    pic_bo: str
    richval: str

    def __init__(self, pic_bo: str, richval: str):
        self.pic_bo = pic_bo
        self.richval = richval


class NormalImage(QzoneImage):

    @classmethod
    def parse(cls, resp: dict):
        pic_bo = resp["data"]["url"].split("&bo=")[1]

        richval = ",{},{},{},{},{},{},,{},{}".format(
            resp["data"]["albumid"],
            resp["data"]["lloc"],
            resp["data"]["sloc"],
            resp["data"]["type"],
            resp["data"]["height"],
            resp["data"]["width"],
            resp["data"]["height"],
            resp["data"]["width"],
        )
        return cls(pic_bo=pic_bo, richval=richval)


class RawImage(QzoneImage):

    @classmethod
    def parse(cls, data: dict, album_id: str):
        pic_bo = data["url"].split("&bo=")[1]
        richval = "{},{},{},{},{},{},{},,{},{}".format(
            data["owner"],
            album_id,
            data["lloc"],
            data["sloc"],
            data["phototype"],
            data["height"],
            data["width"],
            data["height"],
            data["width"],
        )
        return cls(pic_bo=pic_bo, richval=richval)


class Qzone:
    uin: str
    cookies: dict
    client: AsyncClient

    def __init__(self, uin: str, cookies: dict):
        self.uin = uin
        self.cookies = cookies
        self.client = AsyncClient(
            cookies=cookies,
            headers={
                "Referer": "https://user.qzone.qq.com/",
                "Origin": "https://user.qzone.qq.com",
                "User-Agent": UA,
            },
            timeout=60,
        )

    async def upload_image(self, data: bytes) -> QzoneImage:
        resp = await self.client.post(
            "https://up.qzone.qq.com/cgi-bin/upload/cgi_upload_image",
            params={"g_tk": self.get_g_tk(), "uin": self.uin},
            data={
                "filename": "filename",
                "zzpanelkey": "",
                "uploadtype": "1",
                "albumtype": "7",
                "exttype": "0",
                "skey": self.cookies["skey"],
                "zzpaneluin": self.uin,
                "p_uin": self.uin,
                "uin": self.uin,
                "p_skey": self.cookies["p_skey"],
                "output_type": "json",
                "qzonetoken": "",
                "refer": "shuoshuo",
                "charset": "utf-8",
                "output_charset": "utf-8",
                "upload_hd": "1",
                "hd_width": "2048",
                "hd_height": "10000",
                "hd_quality": "96",
                "backUrls": "http://upbak.photo.qzone.qq.com/cgi-bin/upload/cgi_upload_image,"
                "http://119.147.64.75/cgi-bin/upload/cgi_upload_image",
                "url": f"https://up.qzone.qq.com/cgi-bin/upload/cgi_upload_image?g_tk={self.get_g_tk()}",
                "base64": "1",
                "picfile": base64.b64encode(data).decode(),
            },
        )
        if resp.status_code == 200:
            r = json.loads(resp.text[resp.text.find("{") : resp.text.rfind("}") + 1])
            if r.get("ret") != 0:
                raise RuntimeError(f"上传图片失败[{resp.status_code}]:{resp.text}")
            return NormalImage.parse(r)
        else:
            raise RuntimeError(f"上传图片失败[{resp.status_code}]:{resp.text}")

    async def publish(self, text: str, images: list[QzoneImage] = []) -> str:
        if not text and not images:
            return ""
        pic_bos = []
        richvals = []
        for image in images:
            pic_bos.append(image.pic_bo)
            richvals.append(image.richval)

        resp = await self.client.post(
            url="https://user.qzone.qq.com/proxy/domain/taotao.qzone.qq.com/cgi-bin/emotion_cgi_publish_v6",
            params={
                "g_tk": self.get_g_tk(),
                "uin": self.uin,
            },
            data={
                "syn_tweet_verson": "1",
                "paramstr": "1",
                "who": "1",
                "con": text,
                "feedversion": "1",
                "ver": "1",
                "ugc_right": "1",
                "to_sign": "0",
                "hostuin": self.uin,
                "code_version": "1",
                "format": "json",
                "qzreferrer": f"https://user.qzone.qq.com/{self.uin}",
                "pic_bo": ",".join(pic_bos) if len(images) != 0 else None,
                "richtype": "1" if len(images) != 0 else None,
                "richval": "\t".join(richvals) if len(images) != 0 else None,
            },
            headers={
                "User-Agent": UA,
                "Referer": f"https://user.qzone.qq.com/{self.uin}",
                "Origin": "https://user.qzone.qq.com",
            },
        )
        if resp.status_code == 200:
            return resp.json()["tid"]
        else:
            raise RuntimeError(resp.text)

    def get_g_tk(self) -> str:
        p_skey = self.cookies["p_skey"]
        hash_val = 5381
        for i in range(len(p_skey)):
            hash_val += (hash_val << 5) + ord(p_skey[i])
        return str(hash_val & 2147483647)

    async def _get_session(
        self,
        file_path: str,
        album_id: str,
        name: str,
        total: int,
        index: int,
        iBatchID: int,
    ) -> str:
        file_md5 = get_md5(file_path)

        p = {
            "control_req": [
                {
                    "uin": self.uin,
                    "token": {
                        "type": 4,
                        "data": self.cookies["p_skey"],
                        "appid": 5,
                    },
                    "appid": "pic_qzone",
                    "checksum": file_md5,
                    "check_type": 0,
                    "file_len": get_len(file_path),
                    "env": {"refer": "qzone", "deviceInfo": "h5"},
                    "model": 0,
                    "biz_req": {
                        "sPicTitle": name,
                        "sPicDesc": "",
                        "sAlbumID": album_id,
                        "iAlbumTypeID": 0,
                        "iBitmap": 0,
                        "iUploadType": 3,  # 原图
                        "iUpPicType": 0 if total == 1 else 1,
                        "iBatchID": iBatchID,
                        "sPicPath": "",
                        "iPicWidth": 0,
                        "iPicHight": 0,
                        "iWaterType": 0,
                        "iDistinctUse": 0,
                        "iNeedFeeds": 1,
                        "iUploadTime": int(time.time()),
                        "mutliPicInfo": {
                            "iBatUploadNum": total,
                            "iCurUpload": index,
                            "iSuccNum": index,
                            "iFailNum": 0,
                        },
                    },
                    "session": "",
                    "asy_upload": 0,
                    "cmd": "FileUpload",
                }
            ]
        }
        resp = await self.client.post(
            f"https://h5.qzone.qq.com/webapp/json/sliceUpload/FileBatchControl/{file_md5}",
            params={"g_tk": self.get_g_tk()},
            json=p,
        )
        return resp.json()["data"]["session"]

    async def get_album(self, name) -> str | None:
        resp = await self.client.get(
            "https://user.qzone.qq.com/proxy/domain/photo.qzone.qq.com/fcgi-bin/fcg_list_album_v3",
            params={
                "g_tk": self.get_g_tk(),
                "hostUin": self.uin,
                "uin": self.uin,
                "inCharset": "utf-8",
                "outCharset": "utf-8",
            },
        )
        d = json.loads(resp.text[resp.text.find("{") : resp.text.rfind("}") + 1])
        for album in d["data"]["albumListModeSort"]:
            if album["name"] == name:
                return album["id"]
        return None

    async def _get_image(self, album_id: str, name: str) -> RawImage | None:
        resp = await self.client.get(
            "https://h5.qzone.qq.com/proxy/domain/photo.qzone.qq.com/fcgi-bin/cgi_list_photo",
            params={
                "g_tk": self.get_g_tk(),
                "hostUin": self.uin,
                "uin": self.uin,
                "inCharset": "utf-8",
                "outCharset": "utf-8",
                "topicId": album_id,
                "pageStart": 0,
                "pageNum": 500,
            },
        )

        data = json.loads(resp.text[resp.text.find("{") : resp.text.rfind("}") + 1])
        for p in data["data"]["photoList"]:
            print(p["name"])
            print(name)
            if p["name"] == name:
                return RawImage.parse(p, album_id=album_id)
        return None

    async def _upload_raw_image(self, file_path: str, session: str):
        slice_size = 16384

        total_size = get_len(file_path)
        with open(file_path, "rb") as f:
            # 计算总片数
            total_slices = math.ceil(total_size / slice_size)

            # 循环读取并上传每片
            for seq in range(0, total_slices):
                offset = seq * slice_size
                data = base64.b64encode(f.read(slice_size)).decode("utf-8")
                end = min(offset + slice_size, total_size)
                await self.client.post(
                    "https://h5.qzone.qq.com/webapp/json/sliceUpload/FileUpload",
                    params={
                        "type": "json",
                        "total": total_size,
                        "seq": seq,
                        "retry": 0,
                        "offset": offset,
                        "end": end,
                        "g_tk": self.get_g_tk(),
                    },
                    json={
                        "appid": "pic_qzone",
                        "biz_req": {"iUploadType": 3},
                        "iUploadType": 3,
                        "check_type": 0,
                        "checksum": "",
                        "cmd": "FileUpload",
                        "data": data,
                        "end": end,
                        "offset": offset,
                        "retry": 0,
                        "seq": seq,
                        "session": session,
                        "slice_size": slice_size,
                        "uin": str(self.uin),
                    },
                )

    async def upload_raw_image(
        self, album_name: str, file_path: list[str]
    ) -> list[str]:
        album_id = await self.get_album(album_name)
        if album_id == None:
            raise RuntimeError(f"相册 {album_name} 不存在")

        names = []
        iBatchID = int(time.time() * 1e6)
        for i, file in enumerate(file_path):
            name = base64.b64encode(random.randbytes(16)).decode("utf-8")
            names.append(name)
            session = await self._get_session(
                file_path=file,
                album_id=album_id,
                name=name,
                index=i,
                total=len(file_path),
                iBatchID=iBatchID,
            )
            print(session)
            await self._upload_raw_image(file_path=file, session=session)
        return names


def get_len(file_path: str):
    return os.path.getsize(file_path)


def get_md5(file_path: str):
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(16384), b""):
            md5.update(chunk)
    return md5.hexdigest()

import json
import math
import time
import base64
import hashlib
import os

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
    def parse(cls, data: dict):
        pic_bo = data["url"].split("&bo=")[1]
        richval = "{},{},{},{},{},{},{},,{},{}".format(
            data["uin"],
            data["albumId"],
            data["lloc"],
            data["sloc"],
            data["photoType"],
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

    async def _get_session(self, file_path: str, album_id: str):
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
                        "sPicTitle": "image",
                        "sPicDesc": "",
                        "sAlbumID": album_id,
                        "iAlbumTypeID": 0,
                        "iBitmap": 0,
                        "iUploadType": 3,  # 原图
                        "iUpPicType": 0,
                        "iBatchID": int(time.time() * 1e6),
                        "sPicPath": "",
                        "iPicWidth": 0,
                        "iPicHight": 0,
                        "iWaterType": 0,
                        "iDistinctUse": 0,
                        "iNeedFeeds": 1,
                        "iUploadTime": int(time.time()),
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

    async def _get_default_album(self):
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
        return d["data"]["albumListModeSort"][-1]["id"]

    async def _get_last_image(self) -> RawImage:
        resp = await self.client.get(
            "https://mobile.qzone.qq.com/ic2/cgi-bin/feeds/feeds2_html_picfeed_qqtab",
            params={
                "uin": self.uin,
                "refer": "recently",
                "fuin": self.uin,
                "g_tk": self.get_g_tk(),
            },  # uin=858479588&refer=recently&fuin=858479588&g_tk=1918342241
        )
        text = resp.text.replace(" ", "")[10:-16] + "]}}"
        data = json.loads(text)
        return RawImage.parse(data["data"]["photos"][0])

    async def upload_raw_image(self, file_path: str) -> RawImage:
        album = await self._get_default_album()
        session = await self._get_session(file_path=file_path, album_id=album)
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
                resp = await self.client.post(
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
        return await self._get_last_image()


def get_len(file_path: str):
    return os.path.getsize(file_path)


def get_md5(file_path: str):
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(16384), b""):
            md5.update(chunk)
    return md5.hexdigest()

import os.path

import requests
import ujson as json

from nonebot import logger

from hoshino.config.priconne import arena
from os.path import join, dirname

_curpath = join(dirname(__file__), "buffer/pcrd")
os.makedirs(_curpath, exist_ok=True)
pcrd_wasm_path = join(_curpath, "pcrd.wasm")
wasm_dll = join(_curpath, "WebAssembly.dll")
pcrd_wrapper_dll = join(_curpath, "Pcrd.dll")
go_wasm_wrapper_dll = join(_curpath, "GoWasmWrapper.dll")

import pythonnet
pythonnet.load("coreclr")
import clr

def _update_version() -> bool:
    result1 = _checkout_file(pcrd_wasm_path, arena.WASM_URL, header={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66",
        "Referer": "https://pcrdfans.com/",
        "Origin": "https://pcrdfans.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Authorization": "",
    })
    result2 = _checkout_dll(wasm_dll)
    result3 = _checkout_dll(pcrd_wrapper_dll)
    result4 = _checkout_dll(go_wasm_wrapper_dll)
    return result1 or result2 or result3 or result4


def _checkout_dll(path: str) -> bool:
    filename = os.path.basename(path)
    return _checkout_file(path, f"{arena.WRAPPER_URL}/{filename}", header={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66",
    })


def _checkout_file(path: str, url: str, header: dict = None) -> bool:
    filename = os.path.basename(path)
    if header is None:
        header = {}
    if os.path.exists(f"{path}.etag") and os.path.exists(path):
        try:
            with open(f"{path}.etag", 'r') as f:
                header['If-None-Match'] = f.read().strip()
        except Exception as err:
            logger.warn(f"获取已缓存的 {filename} 的 etag 失败: {err}")

    try:
        from hoshino.config.priconne import arena
        response = requests.get(url, headers=header)
        if response.status_code == 304:
            logger.debug(f"{filename} 无更新")
            return False
        if response.status_code != 200:
            raise Exception(f"无法下载 {filename}！")
        logger.info(f"正在更新 {filename}...")
        with open(path, 'wb') as f:
            f.write(response.content)
        etag = response.headers['ETag']
        if etag:
            with open(f"{path}.etag", 'wb') as f:
                f.write(etag.encode('utf8'))
        logger.info(f"{filename} 下载成功")
        return True
    except Exception as err:
        logger.error(f"{filename} 更新失败: {err}")
        return False


_update_version()
clr.AddReference(wasm_dll)
clr.AddReference(go_wasm_wrapper_dll)
clr.AddReference(pcrd_wrapper_dll)


from Pcrd import PcrdWrapper
_wasm = PcrdWrapper(pcrd_wasm_path)


def gen_nonce() -> str:
    return str(_wasm.GenNonce())


def create_sign(payload: dict) -> str:
    if _update_version():
        _wasm.ReloadWasm()
    raw_json = json.dumps(payload, ensure_ascii=False)
    return str(_wasm.CreateSign(raw_json, payload['nonce']))

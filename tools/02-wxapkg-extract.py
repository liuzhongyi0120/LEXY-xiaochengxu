#!/usr/bin/env python3
"""
wxapkg 解包器 —— 解析包头 / 索引段 / 数据段，并剥离防解包填充

包体结构（解密后）
------------------
偏移 0    : 0xBE            魔数头
偏移 1-4  : uint32 BE       info1
偏移 5-8  : uint32 BE       indexlen
偏移 9-12 : uint32 BE       bodylen
偏移 13   : 0xED            魔数尾
偏移 14   : uint32 BE       文件数 N
随后 N 项 : [namelen:u32][name:bytes][offset:u32][size:u32]

三个坑（实测）
--------------
1. 索引段 namelen 存在 ±1 偏差（实测某包第 24 项 L=38 实际为 39）。
   本实现用 (L, L±1, L±2) 候选 + 偏移/长度合法性校验来容错。

2. 每个文件数据前有 1–2 字节「防解包」垃圾字节
   （JSON 如 `L{`、HTML 如 `}\\t<`），需按扩展名定位真实起点后剥离。

3. 索引里的 size 普遍**少算 1 字节**：文件真实末字节落在下一条目的起始偏移上
   （实测 /app-config.json off=32553 size=91648，根对象结束的 `}` 恰在 32553+91648）。
   因此读取时需多借 1 字节，否则所有 JSON 都会缺最后一个 `}`。

用法
----
python 02-wxapkg-extract.py --pkg __APP__.wxapkg --appid wx1234567890abcdef --out ./out
"""
import argparse
import json
import os
import re
import struct

from Crypto.Cipher import AES
from Crypto.Hash import SHA1
from Crypto.Protocol.KDF import PBKDF2

MAGIC = b"V1MMWX"
SALT = b"saltiest"
IV = b"the iv: 16 bytes"
HEAD_LEN = 1024

# 文本文件尾部可能残留的填充/占位字节
TAIL_TRIM = b"\x00"


# --- 解密 -------------------------------------------------------------------
def decrypt(data: bytes, appid: str) -> bytes:
    if data[:6] != MAGIC:
        return data
    body = data[6:]
    key = PBKDF2(appid.encode("utf-8"), SALT, 32, count=1000, hmac_hash_module=SHA1)
    head = AES.new(key, AES.MODE_CBC, IV).decrypt(body[:HEAD_LEN])
    x = ord(appid[-2]) if len(appid) >= 2 else 0x66
    return head + bytes(b ^ x for b in body[HEAD_LEN:])


# --- 索引解析 ---------------------------------------------------------------
def _u32(b: bytes, p: int) -> int:
    return struct.unpack(">I", b[p:p + 4])[0]


def parse_index(buf: bytes):
    """返回 (info1, [(name, offset, size), ...])"""
    if not buf or buf[0] != 0xBE:
        raise ValueError("bad magic：不是有效的 wxapkg（可能未解密）")
    info1 = _u32(buf, 1)
    total = len(buf)
    pos = 14
    count = _u32(buf, pos)
    pos += 4

    entries = []
    for _ in range(count):
        L = _u32(buf, pos)
        chosen = None
        # namelen 可能 ±1 偏差，逐个候选校验偏移合法性
        for cand in (L, L + 1, L - 1, L + 2, L - 2):
            if cand <= 0 or pos + 4 + cand + 8 > total:
                continue
            off = _u32(buf, pos + 4 + cand)
            size = _u32(buf, pos + 4 + cand + 4)
            if 0 <= off <= total and 0 < size <= total:
                chosen = cand
                break
        if chosen is None:
            break  # 索引段结束
        name = re.sub(r"[\x00-\x1f]", "", buf[pos + 4:pos + 4 + chosen].decode("utf-8", "replace"))
        off = _u32(buf, pos + 4 + chosen)
        size = _u32(buf, pos + 4 + chosen + 4)
        entries.append((name, off, size))
        pos += 4 + chosen + 8
    return info1, entries


# --- 填充剥离 ---------------------------------------------------------------
def json_span(text: str, start: int):
    """从 start 处做括号配对，返回完整 JSON 子串（同时支持 {} 与 []）"""
    pairs = {"}": "{", "]": "["}
    stack = []
    in_str = esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            stack.append(c)
        elif c in "}]":
            if not stack or stack.pop() != pairs[c]:
                return None
            if not stack:
                return text[start:i + 1]
    return None


_JS_HEADS = (b"define(", b"var ", b"function", b"!function", b"export ", b"const ", b"let ")


def strip_padding(name: str, data: bytes):
    """剥离头部 1–2 字节防解包填充，返回 (clean_bytes, parsed_json_or_None)"""
    if name.endswith(".json"):
        text = data.decode("utf-8", "replace")
        for i in range(min(9, len(text))):
            if text[i] in "{[":
                span = json_span(text, i)
                if span:
                    out = span.encode("utf-8")
                    try:
                        return out, json.loads(span)
                    except Exception:  # noqa: BLE001
                        return out, None
        return data, None

    if name.endswith((".html", ".wxml")):
        i = data.find(b"<")
        if 0 <= i <= 9:
            data = data[i:]
        return data.rstrip(TAIL_TRIM), None

    if name.endswith(".js"):
        for pat in _JS_HEADS:
            i = data.find(pat)
            if 0 <= i <= 9:
                data = data[i:]
                break
        return data.rstrip(TAIL_TRIM), None

    if name.endswith((".wxss", ".css", ".wxs")):
        return data.lstrip(b"\x00\t ").rstrip(TAIL_TRIM), None

    return data, None


# --- 主流程 -----------------------------------------------------------------
def extract(appid: str, pkg_path: str, outdir: str, quiet: bool = False):
    buf = decrypt(open(pkg_path, "rb").read(), appid)
    info1, entries = parse_index(buf)
    os.makedirs(outdir, exist_ok=True)

    listing = []
    for name, off, size in entries:
        # 多借 1 字节：索引 size 少算 1，真实末字节位于下一条目起始处
        blob = buf[off:min(len(buf), off + size + 1)]
        cblob, obj = strip_padding(name, blob)
        dst = os.path.join(outdir, name.lstrip("/").replace("/", os.sep))
        os.makedirs(os.path.dirname(dst) or outdir, exist_ok=True)
        with open(dst, "wb") as f:
            f.write(cblob)
        listing.append({"name": name, "packed": size, "unpacked": len(cblob), "json": obj})

    if not quiet:
        print(f"{os.path.basename(pkg_path):<30} files={len(entries)}")
    return info1, entries, listing


def main():
    ap = argparse.ArgumentParser(description="wxapkg 解包器（微信 4.0 V1MMWX）")
    ap.add_argument("--pkg", required=True, help="wxapkg 文件路径")
    ap.add_argument("--appid", required=True, help="该包所属小程序 AppID（解密所需）")
    ap.add_argument("--out", required=True, help="输出目录")
    args = ap.parse_args()

    _info1, entries, listing = extract(args.appid, args.pkg, args.out)
    print(f"\n解出 {len(entries)} 个文件 -> {args.out}")
    n_json = sum(1 for x in listing if x["name"].endswith(".json"))
    ok_json = sum(1 for x in listing if x["name"].endswith(".json") and x["json"] is not None)
    print(f"JSON 文件 {n_json} 个，成功解析 {ok_json} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

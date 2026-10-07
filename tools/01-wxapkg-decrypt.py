#!/usr/bin/env python3
"""
wxapkg 解密与关键词扫描 —— 微信 4.0 小程序包（V1MMWX）

用法
----
# 扫描微信小程序缓存目录，找出包含关键词的 appid（用于定位目标小程序）
python 01-wxapkg-decrypt.py scan   --root "<微信缓存>/applet/packages" --keyword 莱克

# 解密单个 wxapkg 到 stdout 或文件
python 01-wxapkg-decrypt.py decrypt --pkg a.wxapkg --appid wx1234567890abcdef -o out.bin

依赖: pycryptodome  (pip install pycryptodome)
"""
import argparse
import json
import os
import sys

from Crypto.Cipher import AES
from Crypto.Hash import SHA1
from Crypto.Protocol.KDF import PBKDF2

# --- V1MMWX 加密格式常量 ----------------------------------------------------
MAGIC = b"V1MMWX"
SALT = b"saltiest"
IV = b"the iv: 16 bytes"
HEAD_LEN = 1024  # 前 1024 字节走 AES-CBC，其余走 XOR


def derive_aes_key(appid: str) -> bytes:
    """AES 密钥：PBKDF2(appid, salt, 32, count=1000, SHA1)"""
    return PBKDF2(appid.encode("utf-8"), SALT, 32, count=1000, hmac_hash_module=SHA1)


def xor_key(appid: str) -> int:
    """XOR 密钥：appid 倒数第 2 个字符的码点；appid 不足 2 位用 0x66"""
    return ord(appid[-2]) if len(appid) >= 2 else 0x66


def decrypt(data: bytes, appid: str) -> bytes:
    """解密 wxapkg 数据；非 V1MMWX 头则原样返回（明文包）"""
    if data[:6] != MAGIC:
        return data
    body = data[6:]
    head = AES.new(derive_aes_key(appid), AES.MODE_CBC, IV).decrypt(body[:HEAD_LEN])
    x = xor_key(appid)
    tail = bytes(b ^ x for b in body[HEAD_LEN:])
    return head + tail


# --- CLI --------------------------------------------------------------------
def iter_packages(root: str):
    """遍历 <root>/<appid>/<version>/*.wxapkg"""
    for appid in sorted(os.listdir(root)):
        d = os.path.join(root, appid)
        if not os.path.isdir(d):
            continue
        for ver in sorted(os.listdir(d)):
            vd = os.path.join(d, ver)
            if not os.path.isdir(vd):
                continue
            for fn in sorted(os.listdir(vd)):
                if fn.endswith(".wxapkg"):
                    yield appid, os.path.join(vd, fn)


def cmd_scan(args):
    root = os.path.expanduser(args.root)
    kws = [k.encode("utf-8") for k in args.keyword]
    total = 0
    matched = {}
    for appid, path in iter_packages(root):
        total += 1
        try:
            buf = decrypt(open(path, "rb").read(), appid)
        except Exception as e:  # noqa: BLE001
            print(f"  ! decrypt failed: {appid} {path}: {e}", file=sys.stderr)
            continue
        for kw in kws:
            if kw in buf:
                matched.setdefault(appid, []).append({"pkg": path, "keyword": kw.decode()})
                print(f"*** MATCH  {appid}  {os.path.basename(path)}  <- {kw.decode()}")
                break

    print(f"\n扫描包体 {total} 个，命中 appid {len(matched)} 个")
    for appid, hits in matched.items():
        print(f"  {appid}  ({len(hits)} 个包体)")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(matched, f, ensure_ascii=False, indent=2)
        print(f"saved -> {args.json_out}")
    return 0


def cmd_decrypt(args):
    buf = decrypt(open(args.pkg, "rb").read(), args.appid)
    if args.out:
        with open(args.out, "wb") as f:
            f.write(buf)
        print(f"decrypted {len(buf)} bytes -> {args.out}")
    else:
        sys.stdout.buffer.write(buf)
    return 0


def main():
    ap = argparse.ArgumentParser(description="wxapkg 解密与关键词扫描（微信 4.0 V1MMWX）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="扫描缓存目录，按关键词定位小程序")
    s.add_argument("--root", required=True,
                   help="packages 根目录，如 %%APPDATA%%/Tencent/xwechat/radium/users/<uid>/applet/packages")
    s.add_argument("--keyword", nargs="+", required=True, help="关键词，可多个")
    s.add_argument("--json-out", help="命中结果写入 JSON")
    s.set_defaults(func=cmd_scan)

    d = sub.add_parser("decrypt", help="解密单个 wxapkg")
    d.add_argument("--pkg", required=True)
    d.add_argument("--appid", required=True)
    d.add_argument("-o", "--out", help="输出文件；省略则写 stdout")
    d.set_defaults(func=cmd_decrypt)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

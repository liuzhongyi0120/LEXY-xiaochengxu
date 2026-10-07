#!/usr/bin/env python3
"""
批量解包某小程序的全部分包，并导出：
  - 完整 app-config.json（用花括号配对提取，规避嵌套 subPackages 截断）
  - 各包体文件/组件/图片统计（package-stats.json）

用法
----
python 03-extract-app.py \
  --root "<微信缓存>/applet/packages/wx6bc687ff89875e20" \
  --appid wx6bc687ff89875e20 \
  --out  ./extracted

微信 4.0 缓存结构: applet/packages/<appid>/<version>/*.wxapkg
"""
import argparse
import importlib.util
import json
import os


def _load_extractor():
    """模块文件名以数字开头，不能直接 import，用 importlib 按路径加载"""
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "wxapkg_extract", os.path.join(here, "02-wxapkg-extract.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WX = _load_extractor()

IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp")


def find_packages(root: str):
    """在 <root> 或 <root>/<version> 下找 .wxapkg"""
    hits = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if fn.endswith(".wxapkg"):
                hits.append(os.path.join(dirpath, fn))
    return sorted(hits)


def extract_app_config(pkg_path: str, appid: str):
    """
    从主包中提取 app-config.json。

    注意：不能用「在整包文本里搜 '{"entryPagePath"'」的标记法
    —— 实测该包 app-config 的首键是 subPackages，entryPagePath 在后面。
    正确做法是从索引段定位 app-config.json 条目，再按括号配对取精确内容。
    """
    buf = WX.decrypt(open(pkg_path, "rb").read(), appid)
    _info1, entries = WX.parse_index(buf)
    for name, off, size in entries:
        if name.endswith("app-config.json"):
            blob = buf[off:min(len(buf), off + size + 1)]  # 多借 1 字节见 02 脚本说明
            _clean, obj = WX.strip_padding(name, blob)
            return obj
    return None


def main():
    ap = argparse.ArgumentParser(description="批量解包小程序全部分包 + 导出 app-config")
    ap.add_argument("--root", required=True, help="小程序包目录（含 <version>/*.wxapkg）")
    ap.add_argument("--appid", required=True, help="小程序 AppID")
    ap.add_argument("--out", required=True, help="输出目录")
    args = ap.parse_args()

    pkgs = find_packages(args.root)
    if not pkgs:
        print("未找到任何 .wxapkg，请检查 --root")
        return 1
    print(f"发现 {len(pkgs)} 个包体\n")

    stats = []
    total_files = 0
    cfg = None

    for path in pkgs:
        name = os.path.splitext(os.path.basename(path))[0]
        outdir = os.path.join(args.out, name)
        try:
            _i, entries, listing = WX.extract(args.appid, path, outdir)
        except Exception as e:  # noqa: BLE001
            print(f"  ! {name}: {e}")
            continue

        comps = sum(1 for x in listing if "/components/" in x["name"] or x["name"].startswith("components/"))
        imgs = sum(1 for x in listing if x["name"].lower().endswith(IMG_EXT))
        titled = []
        for x in listing:
            obj = x.get("json")
            if isinstance(obj, dict):
                t = obj.get("navigationBarTitleText")
                if t:
                    titled.append({"page": x["name"][:-5], "title": t})

        total_files += len(entries)
        stats.append({"pkg": name, "files": len(entries), "components": comps,
                      "images": imgs, "titled_pages": titled})

        if cfg is None:
            cfg = extract_app_config(path, args.appid)

    print(f"\n共解出 {total_files} 个文件")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "package-stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"saved -> {os.path.join(args.out, 'package-stats.json')}")

    if cfg:
        with open(os.path.join(args.out, "app-config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        pages = len(cfg.get("pages") or [])
        subs = cfg.get("subPackages") or cfg.get("subpackages") or []
        sub_pages = sum(len(s.get("pages") or []) for s in subs)
        print(f"saved -> {os.path.join(args.out, 'app-config.json')}")
        print(f"  页面 {pages} + 分包页 {sub_pages} = {pages + sub_pages}")
        print(f"  分包 {len(subs)} 个 | entryPagePath={cfg.get('entryPagePath')}")
    else:
        print("! app-config 提取失败")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

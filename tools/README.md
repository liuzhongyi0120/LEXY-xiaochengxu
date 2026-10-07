# tools —— 小程序包拆解脚本

三个脚本，按顺序使用即可完成「定位 → 解密 → 解包 → 导出配置」全流程。

## 依赖

```bash
pip install pycryptodome
```

Python 3.8+。

---

## 01-wxapkg-decrypt.py —— 解密与关键词扫描

微信 4.0 的小程序包是 `V1MMWX` 加密格式：文件头 6 字节魔数，前 1024 字节走 AES-CBC（密钥由 AppID 经 PBKDF2 派生），其后全部 XOR（密钥 = AppID 倒数第 2 个字符的码点）。

**用途一：在缓存里按关键词把目标小程序捞出来**

```bash
python 01-wxapkg-decrypt.py scan \
  --root "$APPDATA/Tencent/xwechat/radium/users/<uid>/applet/packages" \
  --keyword 莱克 LEXY \
  --json-out matched.json
```

会自动遍历 `<root>/<appid>/<version>/*.wxapkg`，解密后做明文关键词匹配，输出命中的 AppID。**加密包里直接 grep 是搜不到的，必须先解密。**

**用途二：解出单个包体**

```bash
python 01-wxapkg-decrypt.py decrypt --pkg __APP__.wxapkg --appid wx6bc687ff89875e20 -o raw.bin
```

---

## 02-wxapkg-extract.py —— 解包器

```bash
python 02-wxapkg-extract.py --pkg __APP__.wxapkg --appid wx6bc687ff89875e20 --out ./out
```

解析结构：

| 偏移 | 内容 |
|---|---|
| 0 | `0xBE` 魔数头 |
| 1–4 | `info1`（uint32 BE） |
| 5–8 | `indexlen` |
| 9–12 | `bodylen` |
| 13 | `0xED` 魔数尾 |
| 14 | 文件数 N |
| 之后 | N × `[namelen][name][offset][size]` |

### 三个必须处理的坑

1. **`namelen` 有 ±1 偏差。** 实测某包第 24 项 `L=38` 实际是 39。脚本用 `(L, L±1, L±2)` 候选 + 偏移合法性校验逐个尝试。

2. **每个文件数据前有 1–2 字节防解包垃圾。**
   - JSON：`L{"subPackages"...` / 常见 `\xaf{"entryPagePath"...`
   - HTML：`}\t<sty...`
   - JS：`define(` / `var ` / `function` 之前插垃圾

   脚本按扩展名定位真实起点，JSON 用括号配对取精确区间。

3. **索引里的 `size` 普遍少算 1 字节。** 实测 `/app-config.json` `off=32553 size=91648`，而根对象结束的 `}` 恰在 `32553+91648` —— 也就是落在下一条目的起始偏移上。**不多借 1 字节读取，所有 JSON 都会缺最后一个 `}` 而解析失败。** 脚本对每条目读取 `size+1` 字节。

---

## 03-extract-app.py —— 批量解包 + 导出配置

```bash
python 03-extract-app.py \
  --root "$APPDATA/Tencent/xwechat/radium/users/<uid>/applet/packages/wx6bc687ff89875e20" \
  --appid wx6bc687ff89875e20 \
  --out ./extracted
```

一次做完：

- 解出该小程序全部包体（本项目为 22 个 → 3,899 个文件）
- 导出 `app-config.json`（完整：452 页 / 82 分包 / tabBar / plugins / ext）
- 导出 `package-stats.json`（各包体文件数 / 组件数 / 图片数）

### 为什么 app-config 不能"搜关键词"

网上常见做法是在解密后的全文里搜 `{"entryPagePath"` 然后做花括号配对。**这个包上会失效**——它的 `app-config.json` 首键是 `subPackages`，`entryPagePath` 出现在中间，全文搜索直接返回 -1。

正确做法：**从索引段按文件名定位 `app-config.json` 条目**，取出该条目的字节区间再做括号配对。

---

## 已知走不通的路

- **CDP 调试端口**：PC 微信 4.0 的小程序容器默认不开放远程调试端口，扫遍 `WeChatAppEx.exe` 的监听端口无响应。
- **MMKV 本地存储**：`applet/local/<appid>/usrmmkvstorage*/` 是加密的，读不出装修配置。
- **静态读 WXML**：所有页面模板编译后都是 `<page></page>` 空壳，真实模板在运行时 `$gwx` 函数表里。

## 能走通的一条小路

**运行日志是明文的。** `applet/local/<appid>/usr/miniprogramLog/log*` 里记录了真实的页面路由（`page xxx onLoad have been invoked`），可以统计出这个店实际在用哪些页面——本项目据此发现 452 页里真实只走了 11 页。

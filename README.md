# LEXY莱克 微信小程序 · 框架拆解与复刻

> 对「LEXY莱克」微信小程序（AppID `wx6bc687ff89875e20`）的框架结构逆向拆解、前端展示层还原与复刻实施方案。

---

## 一句话结论

**LEXY莱克小程序不是自研小程序，而是有赞微商城（Youzan WSC）SaaS 模板实例。**

包里一共 452 个页面，但真实使用只走了 11 个，高频核心链路只有 4 条。所以复刻的正确姿势是**在有赞商家后台做店铺装修**，而不是从零自研 452 个页面。

---

## 一、身份确认

| 项 | 值 |
|---|---|
| 小程序名称 | LEXY莱克 |
| AppID | `wx6bc687ff89875e20` |
| 店铺名 | LEXY莱克官方旗舰店 |
| 门店 kdt_id | `45818390` |
| 总部 / 根 kdt_id | `44375018` |
| H5 主机 shopId | `46010558` |
| 模板版本 userVersion | `3.179.7.101` |
| 入口路径 | `pages/home/dashboard/index?shopAutoEnter=1&kdt_id=45818390` |

**连锁结构**：`chainOnlineShopMode=2`、`isBranchChainStore=1`、门店角色 `shopRole=2`、`rootKdtId=parentKdtId=hqKdtId=44375018`。

> 小程序包是**总部 + 门店一套包**，靠 URL 参数 `kdt_id` 运行时切店。包内默认写死的 `kdtId=44375018` 是总部 ID，不是"别人的店"。

**身份识别方法**：用户给的 `#小程序://` 协议链接浏览器不可达。通过微信 `net/kvcomm/*.statistic` 找到该链接的点击时间戳（`1791335173393` ≈ 2026-10-07 09:06），用时间戳反查 `applet/icon/*.ico`，命中 LEXY莱克红黑标准 Logo。

已排除的同机干扰项：`wx5b3992fb2164b748`（碧云泉 bewinch）、`wxb183e95bd61b62cb`（小莱到家，售后服务）。

---

## 二、框架归属证据

| 证据 | 观测值 |
|---|---|
| 代码关键词 `kdt` | 5182 次 |
| 代码关键词 `youzan` | 553 次 |
| 代码关键词 `有赞` | 58 次 |
| 接口域名 | `h5.youzan.com`、`cashier.youzan.com`、`trade.youzan.com`、`uic.youzan.com`、`passport.youzan.com`、`store.youzan.com`、`img01.yzcdn.cn`、`b.yzcdn.cn` |
| 店铺 H5 域名 | `shop255245.youzan.com` |

**结论**：有赞微商城（WSC）小程序模板，非自研代码。

---

## 三、包体规模

| 项 | 值 |
|---|---|
| wxapkg 文件数 | 22（1 主包 + 21 分包包体） |
| 解出文件总数 | 3,899 |
| 主包文件数 | 461 |
| 页面总数 | 452（主包 41 + 分包 403 + 插件 4 + 其它 4） |
| subPackages 数 | 82（其中 1 个独立分包 `packages/common/blank-page`） |
| 自定义组件文件 | 1,292 |
| 图片资源 | 6 |
| 最大分包 | `goods-minor` 564 文件、`goods-core` 400、`trade-buy` 300 |

**插件**：

```json
{
  "yzVideoPlugin":      { "provider": "wx9e5eba73bf23a27a", "version": "1.4.3" },
  "live-player-plugin": { "provider": "wx2b03c6e691cd7370", "version": "1.3.2" }
}
```

`wx2b03c6e691cd7370` 是微信视频号直播官方插件——支撑"直播带货链路"的关键能力。

---

## 四、前端展示层结构

### 4.1 底部导航（TabBar）

`app-config.json` 里是 3 项，但 `custom-tab-bar-v2` 组件实际引用的是 `shop-nav-weapp/rt/ShopNavWeapp` —— **底部导航本身也是一个装修扩展，tab 项由服务端下发**。配置文件里的 3 项只是元数据和降级配置。

| # | text | pagePath | 说明 |
|---|---|---|---|
| 1 | 首页 | `pages/home/dashboard/index` | 空壳页，全靠服务端装修 |
| 2 | 购物车 | `pages/goods/cart/index` | 交易闭环 |
| 3 | 我的 | `pages-retail/usercenter/dashboard-v2/index` | 零售连锁版个人中心 |

真实 tab 页是 `pages/home/tab/one|two|three`。

样式（真实值）：`custom:true`、选中 `#FF4444`、未选中 `#606060`、背景 `#FCFCFC`、`borderStyle:white`。

> 6 个 tabBar 图标（3 tab × 普通/选中）以 base64 内嵌在 `app-config.json` 中，已导出到 `assets/tabbar/`，**可直接复用**。

### 4.2 首页是"微页面"——完全空壳

首页模板编译后字面上就是：

```html
<page></page>
```

**一个字都没有。** 整个首页 100% 由服务端下发的装修配置在运行时渲染。逆向 `appservice.app.js` 后确认的结构：

```
currentPageConfig.containers[]        ← 容器（可嵌套）
   └─ contents[]                      ← 模块/组件
        moduleId · name · stage(normal | defer | post)
```

运行时按 `stage` **分阶段渲染**（先出首屏，defer/post 的模块后加载）。装修接口走 `/wscdeco/*` 与 `wsc-tee-decorate/*`（top-nav、floating-nav、live-pop、navigation-bar、theme-color、goods-prefetch 等）。

### 4.3 页池层 —— 452 页按需加载

452 个页面的构成：

| 归属 | 页数 |
|---|---|
| 分包页 `packages/*` | 403 |
| **主包页 `pages/*`** | **41** |
| 插件页 `__plugin__/*` | 4 |
| 其它 | 4 |

**主包 41 页就是真正的"一级展示层"**，其余 403 页按分包懒加载：

```
pages/account/login            pages/home/dashboard          pages/salesman/salesman-center
pages/bear                     pages/home/feature            pages/salesman/tutorial
pages/common/blank-page        pages/home/tab/one|two|three  pages/shop/shopnote/list
pages/common/dmc-blank-page    pages/membercard/{active,detail,level,list,result,setting}
pages/common/webview-page      pages/order/share             pages/trade/buy
pages/common/webview-expires   pages/paidcontent/{column,content,list,live,pay}
pages/goods/{all,cart,detail,group,search,seckill}
pages/pay/unicashier           pages/ump/{fission,integral-store,pintuan}
pages/usercenter/dashboard     pages/usercenter/promotion/promotion_detail
```

按二级目录看全量页面的分布（前 12）：

| 族群 | 页数 | 族群 | 页数 |
|---|---|---|---|
| `ump` 营销 | 47 | `retail` 零售门店 | 22 |
| `shop` 店铺 | 29 | `paidcontent` 内容付费 | 19 |
| `trade` 交易 | 23 | `goods` 商品 | 17 |
| `groupbuying` 拼团 | 23 | `salesman` / `guide` 分销导购 | 15 + 15 |

**预下载规则**（`preloadRule`）是「页面 → 分包」映射，例如进 `pages/goods/cart/index` 预下载 `packages/trade`、进 `pages/goods/seckill/index` 预下载 `packages/trade-buy`、进 `pages/common/blank-page/index` 预下载 `packages/goods-core`+`goods-main`+`goods`。

### 4.4 页面标题映射（复刻可直接复用）

`app-config.json` 的 `page` 字段是 452 页的逐页 window 配置：

- **233 页有 `navigationBarTitleText`**（另一半为空，标题由前端组件自行渲染）
- **59 页使用 `navigationStyle: custom`**（自绘导航栏）

已导出为 `data/05-page-title-map.json`，是复刻时最直接的页面命名参考。

### 4.5 真实使用频率 —— 452 页只用 11 页

从小程序**明文运行日志**（5 个月）统计真实路由：

高频 4 个：首页 → `pages/home/tab/three` → 专题页 `feature` → 商品详情。

**96% 的页面从未被走过。** 这对复刻是重大利好：核心只需复刻 4–5 条链路。

---

## 五、品牌视觉（可直接使用的真实色板）

来自有赞店铺接口 `themeColors`，共 **49 色**，与小程序 tabBar 的 `selectedColor` 完全一致——证明小程序与 H5 共用同一套装修主题。

| 语义 | 值 |
|---|---|
| 主色 `general` / `main-bg` | `#FF4444` |
| 图标 / 价格 `icon` / `price` | `#FC0000` |
| 标签文字 `tag-text` | `#CF0000` |
| 标签背景 `tag-bg` | `#FFF2F2` |
| 渐变起 `start-bg` | `#FF8544` |
| 渐变止 `end-bg` | `#FF2E2E` |
| 主文字 `main-text` | `#ffffff` |
| 副背景 `vice-bg` | `#555555` |
| 正文主 `neutral-text-main` | `#323233` |
| 正文辅助 `neutral-text-prompt` | `#969799` |
| 分割线 `neutral-line-main` | `#dcdee0` |
| 页面底 `neutral-bg-main` | `#f2f3f5` |

完整 49 色见 `data/02-frontend-real-config.json`。

**H5 底部导航 4 项**：店铺主页 / 个人中心 / 线下门店 / 店铺信息。
**浮动导航**：`floatingMode=2`，折叠 + 展开两套图标。

---

## 六、目录结构

```
.
├── README.md
├── docs/                                   # PRD 交付物
│   ├── LEXY莱克微信小程序框架拆解与复刻PRD.docx    # 正式交付（Word）
│   ├── LEXY莱克微信小程序PRD.html                # 同版网页版
│   └── LEXY莱克微信小程序PRD.md                  # Markdown 源
├── data/                                   # 结构化分析数据
│   ├── 01-miniprogram-app-config.json      # 小程序完整 app-config（452 页 / 82 分包 / tabBar / plugins / ext）
│   ├── 02-frontend-real-config.json        # 前端展示层真实配置（身份 / 49 色板 / 导航）
│   ├── 03-package-stats.json               # 22 个包体的文件 / 组件 / 图片统计
│   ├── 04-research-snapshot.md             # 逆向证据快照（一手证据汇总）
│   └── 05-page-title-map.json              # 452 页的标题 / 导航样式映射（复刻命名参考）
├── assets/
│   ├── app-icon-256.png                    # 小程序图标
│   └── tabbar/                             # 6 个真实 TabBar 图标（普通/选中）
├── raw-responses/                          # 有赞接口原始响应（证据留档）
└── tools/                                  # 拆解分析脚本，见 tools/README.md
```

---

## 七、PRD 文档结构

| 章节 | 内容 |
|---|---|
| 一 | 文档说明与数据来源 |
| 二 | 产品概述 |
| 三 | 技术架构拆解 |
| 四 | 信息架构（页面地图） |
| 五 | 核心业务流程 |
| 六 | 功能需求清单（复刻范围） |
| 七 | 非功能需求 |
| 八 | **复刻实施路径（决策重点）** |
| 九 | 待补齐信息清单（需真机截图核对） |
| 十 | 风险与提示 |

**复刻路径建议（第八章）**：主推**路径 B —— 直接沿用有赞 SaaS 开店铺设**，而非从零自研 452 个页面；文档内给出分阶段交付计划。

---

## 八、诚实边界

编译包只是**代码层**，以下内容全部由有赞服务端按 kdtId 动态下发，静态包中**不存在**：

- ❌ 品牌文案、栏目配置、商品数据、banner 素材
- ❌ 首页实际的栏目顺序与组件配置
- ❌ 营销活动配置

另外，所有页面模板编译后均为 `<page></page>` 空壳，真实 WXML 在 `$gwx` 函数表内，静态不可读。452 个页面中 **219 页的 `navigationBarTitleText` 为空**（标题由前端组件自行渲染），另有 59 页使用 `navigationStyle: custom`。

因此 **PRD 第九章列出 7 项待补清单**，视觉层需以真机逐页截图核对。本 PRD 给出的是**框架骨架 + 能力清单**。

> ⚠️ 需要复核：PRD 早稿中有两处口径偏保守——「页面标题绝大多数为空」与「主包页面族群分布」，本 README 已按修正后的解包结果更新（`size` 少算 1 字节的坑曾导致 JSON 缺尾字节）。PRD 正文如需与 README 完全对齐，建议重新生成一版。

---

## 九、分析方法

1. **定位包体**：扫描本机微信小程序缓存目录 `AppData/Roaming/Tencent/xwechat/radium/users/<uid>/applet/packages/`。
2. **解密 wxapkg**：微信 4.0 的 `V1MMWX` 加密格式——文件头 6 字节标识，前 1024 字节 AES-CBC（key 由 AppID 经 PBKDF2 派生），其余 XOR（key = appid 倒数第 2 字符码点）。见 `tools/01-wxapkg-decrypt.py`。
3. **解包**：解析 14 字节包头 + 索引段 + 数据段。三个坑：
   - 索引段 `namelen` 存在 ±1 偏差 → 多候选 + 合法性校验容错；
   - 每个文件数据前有 1–2 字节防解包垃圾字节 → 按扩展名定位真实起点剥离；
   - 索引 `size` 普遍**少算 1 字节**（文件真实末字节落在下一条目起始处）→ 读取需多借 1 字节，否则所有 JSON 都缺最后一个 `}`。

   见 `tools/02-wxapkg-extract.py`。
4. **批量还原与配置提取**：一次解完某小程序的全部 22 个包体，并从索引段定位 `app-config.json` 条目后做括号配对解析（不能用「全文搜关键词」的标记法——该配置首键是 `subPackages` 而非 `entryPagePath`）。见 `tools/03-extract-app.py`。
5. **还原展示层**：通过 `kdt_id` 打通有赞公开接口（店铺页 / 装修接口 / 导航接口）获取真实配置。
6. **真实使用频率**：读小程序明文运行日志 `applet/local/<appid>/usr/miniprogramLog/log*` 的页面路由记录。

> 注：小程序本地 MMKV 存储是**加密的**，PC 微信 4.0 的小程序容器**默认不开放 CDP 调试端口**，这两条路走不通。

---

## 十、免责声明

本项目为**品牌方自用的技术拆解与复刻调研**，内容涉及：

- 本机微信客户端缓存的小程序编译包（品牌方自有小程序的本地缓存）
- 有赞平台面向公网提供的公开接口响应

所有店铺 ID、色板、导航配置均为运营配置数据。仓库**不含**有赞 SaaS 框架的反编译源码，也不含任何用户个人信息或交易数据。

相关商标、品牌名归其权利人所有。

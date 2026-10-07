# 研究快照：LEXY莱克 微信小程序 逆向拆解证据

> 来源：本机微信 4.0 小程序包缓存（PC 端），非公开网络资料。
> 路径：`C:\Users\8274282\AppData\Roaming\Tencent\xwechat\radium\users\1bea3cd437592e430de5cf1b1c7144c7\applet\packages\wx6bc687ff89875e20\61\`
> 解密方式：V1MMWX 头（AES-CBC 前 1024 字节 + 其余 XOR），密钥由 AppID 经 PBKDF2 派生。

## 一、身份确认
- AppID：`wx6bc687ff89875e20`
- 图标（icon/wx6bc687ff89875e20.ico，256x256）＝ LEXY莱克 红黑标准 Logo → 身份确认
- 本机缓存时间：图标与 storage 于 2026-10-07 09:06 更新（与用户分享链接点击时间吻合）
- 同机其它莱克系小程序（已排除）：`wx5b3992fb2164b748`=碧云泉 bewinch；`wxb183e95bd61b62cb`=小莱到家（售后服务）

## 二、框架归属（一手证据）
- 代码中出现 `youzan` 553 次、`kdt` 5182 次、`有赞` 58 次
- 接口域名：h5.youzan.com / cashier.youzan.com / trade.youzan.com / uic.youzan.com / passport.youzan.com / store.youzan.com / img01.yzcdn.cn / b.yzcdn.cn
- 店铺 H5 域名：`https://shop255245.youzan.com/v2`
- 结论：**有赞微商城（Youzan WSC）小程序模板实例**，非自研代码

## 三、ext 配置（app-config.json 原文片段）
```
"ext":{"appId":"wx6bc687ff89875e20","userVersion":"3.179.7.101","isChainStore":true,
"kdtId":44375018,"hasAsyncVideoPlugin":true,"tabBar":{},"bizExt":{},"chainStore":true,
"domainCustomConfig":{},"env":"prd","shopAppType":3,"themeType":3,"transactionWeappFlag":false}
```

## 四、插件
```
"plugins":{
 "yzVideoPlugin":{"provider":"wx9e5eba73bf23a27a","version":"1.4.3","subpackage":"__APP__"},
 "live-player-plugin":{"export":"seckill.js","provider":"wx2b03c6e691cd7370","version":"1.3.2","subpackage":"__APP__"}}
```
- `wx2b03c6e691cd7370` = 微信视频号直播插件（页面 `__plugin__/wx2b03c6e691cd7370/pages/live-player-plugin`）

## 五、全局配置
- entryPagePath: `pages/home/dashboard/index.html`
- tabBar: `{"custom":true,"color":"#606060","selectedColor":"#FF4444","backgroundColor":"#FCFCFC","borderStyle":"white"}`
  - list：首页 `pages/home/dashboard/index`、购物车 `pages/goods/cart/index`、我的 `pages-retail/usercenter/dashboard-v2/index`
- window: `navigationBarBackgroundColor #ffffff`、`onReachBottomDistance 400`、首页 `navigationStyle:custom` + `enablePullDownRefresh:true`
- permission: `scope.userLocation`（"你的位置信息将用于获取当前位置相对于门店的距离"）
- networkTimeout.request: 10000
- preloadRule 预下载：packages/retail-shelf、packages/shop-select、packages/async-retail、packages/usercenter
- 含 `requiredPrivateInfos`、`__usePrivacyCheck__`

## 六、包体规模
| 项 | 值 |
|---|---|
| wxapkg 文件数 | 22（1 主包 + 21 分包包体） |
| 解出文件总数 | 3,899 |
| 主包文件数 | 461 |
| 页面总数（app-config pages） | 452 |
| subPackages 数 | 82（其中 1 个独立分包 pages/common/blank-page） |
| 最大分包 | goods-minor 564 文件、goods-core 400 文件、trade-buy 300 文件 |

## 七、分包清单（82 个 root）
packages/{vote, home, scan-code-buy, order, order-native, pay, assets, common, statcenter, showcase-template, ump, card, pre-card, point, new-punch, shop, shop-select, paidcontent, edu, paid, trade-pay, trade-buy, trade, user, salesman, channel, guide, groupbuying, collage, feature-video, group-center, member-benefit, evaluation, message, account, takeaway-search, benefit-card, independent/goods, pointstore, async-video, business-card, levelcenter, member-code, zan-web-view, short-video, weapp-live, tech-support, weass, wxvideo, trade-cart, retail/buy, retail/paid, retail/scan-page, retail/membercenter, retail/shop-list, retail/chat, retail/dashboard, retail/extra, retail/order-pool, retail/order, retail/usercenter, usercenter, goods-list, ext-marketing-page, hotel, retail-shelf, retailb, trade-buy-subpage, gift, goods, async-minor, async-main, async-usecenter, async-feature-ext, async-retail, async-core, async-tee, goods-main, goods-minor, goods-core, third-yun} + pages/common/blank-page

## 八、能力推断依据（页面路由 → 功能）
- 营销：packages/ump/{seckill?→goods/seckill, pintuan/detail, pintuan/playing-instruction, collage/groupon/detail, collage/groupon/join-groups, collage/lottery/detail, helpcut, bargain-purchase, integral-store, sign-in, carve-coupon, coupon-pack/fetch, split-coupon-friend, meet-reduce-goods, second-half-discount, periodbuy-list, blind-box/auth, new-lottery, welike, wine-tasting, booking, presents, handsel-expand, in-sourcing-fission, share-benefit, apps/{cards,crazy,shake,zodiac}}
- 会员：membercard/{list,detail,active,setting,level,result}、card/{all,list,detail,active,setting,level,result}、pre-card/{buy-center,order-buy,exchange,recharge,record,...}、benefit-card/*、levelcenter/{free,plus,pay,benefit,offline-recruit}、point/home、pointstore/*、user/{coupon,integral,task-center,membercenter/setting,cashback}
- 分销导购：salesman/{promote,salesman-center,tutorial,invite,rank,report,task-award,task-detail,business-card,external-card,zone/*}、channel/{agent,indentor}、guide/{promote,zone/material,front-guide,pages/*}
- 交易：trade/{buy,order/*,refund/list,batch-refund,cert/verify-ticket,order-detail,order-search}、trade-buy/order/{address-*,contact,self-fetch-address*,buy}、pay/unicashier、order-native/*
- 零售门店：retail/{buy,paid,scan-page,membercenter,shop-list,chat,dashboard,extra/*,order-pool,order,usercenter}、shop/{chain-store/*,multi-store/*,info,physical-store,levelcenter}、shop-select/chain-store/*、retail-shelf/*、retailb/*
- 内容：short-video、wxvideo/{fastbuy,cps/*,weshop,media-list,validate}、weapp-live/{room,authorize,common}、paidcontent/*、edu/*、new-punch/*、shop/shopnote/*、evaluation/*
- 消息客服：message/{satisfaction,contact,subscribe,wxkf}

## 九、局限说明（诚实边界）
- 编译包中**不含**品牌文案、栏目配置、商品数据、banner 素材 —— 全部由有赞服务端按 kdtId 下发
- 页面 `navigationBarTitleText` 绝大多数为空（首页 navigationStyle=custom，标题由前端组件渲染）
- 因此：视觉层、栏目结构、营销活动配置需以**真机逐页截图**为准，本 PRD 给出的是"框架骨架 + 能力清单"

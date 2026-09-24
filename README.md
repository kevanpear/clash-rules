# clash-rules

自维护的 Clash / mihomo 规则集（替代之前托管在网盘、靠直连下载的方案）。
规则内容与 [`kevanpear/sing-box-rules`](https://github.com/kevanpear/sing-box-rules)
一致，但这里从源码到产物都是 Clash 的写法。

## 一键复制：完整规则配置

**只想要一份能直接跑的整份配置？** 打开 **[`example/clash.yaml`](example/clash.yaml)**，
点右上角复制按钮拿走整份模板——只需填入自己的节点、改掉面板密码即可（节点用
`include-all` 自动纳入策略组，加几个都不必动配置）。已含性能/嗅探/持久化等推荐项，
适配 mihomo ≥ 1.18.9。

想自己拼、只取规则部分？用下面这两段：直接抄进你的 Clash / mihomo 配置即可（代码块右上角有复制按钮）。
把第一段并入 `rule-providers:`、第二段并入 `rules:`——**如果你的配置已经有这两个顶层键，
只复制其下的条目，别把 `rule-providers:` / `rules:` 这行也粘进去，否则会出现重复顶层键**。

前提：`proxy: PROXY` 里的 `PROXY` 换成你自己已有的**代理组名**（下载规则集要经它出墙）；
`rules` 里的 `PROXY` / `DIRECT` / `REJECT` 也换成你的策略组名。规则集按 `interval: 86400`
每天自动更新，push 新规则后客户端自动拉到，无需手动操作。

<details open>
<summary><b>① rule-providers（18 个规则集）</b></summary>

```yaml
rule-providers:
  # ===== 拦截：广告 / 追踪 / 遥测（命中即断）=====
  reject: { type: http, behavior: domain, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/rules/geosite_reject.yaml", path: ./ruleset/geosite_reject.yaml }
  win_spy: { type: http, behavior: domain, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/rules/geosite_win_spy.yaml", path: ./ruleset/geosite_win_spy.yaml }  # Windows 遥测；想保功能可改 DIRECT
  # ===== 走代理：AI / 流媒体 / 音乐（精确服务，压过直连大盘）=====
  openai: { type: http, behavior: classical, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/source/geosite_openai.yaml", path: ./ruleset/geosite_openai.yaml }  # 含 keyword/regex，用 source
  claude: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_claude.mrs", path: ./ruleset/geosite_claude.mrs }
  google: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_google.mrs", path: ./ruleset/geosite_google.mrs }
  gemini: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_google-gemini.mrs", path: ./ruleset/geosite_google-gemini.mrs }
  youtube: { type: http, behavior: classical, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/source/geosite_youtube.yaml", path: ./ruleset/geosite_youtube.yaml }  # 含 keyword，用 source
  spotify: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_spotify.mrs", path: ./ruleset/geosite_spotify.mrs }
  tiktok: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_tiktok.mrs", path: ./ruleset/geosite_tiktok.mrs }
  netflix: { type: http, behavior: classical, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/source/geosite_netflix.yaml", path: ./ruleset/geosite_netflix.yaml }  # 含 regex，用 source
  disney: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_disney.mrs", path: ./ruleset/geosite_disney.mrs }
  primevideo: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_primevideo.mrs", path: ./ruleset/geosite_primevideo.mrs }
  hbo: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_hbo.mrs", path: ./ruleset/geosite_hbo.mrs }
  playstation: { type: http, behavior: domain, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_playstation.mrs", path: ./ruleset/geosite_playstation.mrs }
  # ===== 直连：国内白名单 / Windows 更新 =====
  win_update: { type: http, behavior: domain, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/rules/geosite_win_update.yaml", path: ./ruleset/geosite_win_update.yaml }
  cn_direct: { type: http, behavior: classical, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/source/geosite_direct.yaml", path: ./ruleset/geosite_direct.yaml }  # 9.5 万条，用 source 保 regex；求快可换 mrs/geosite_direct.mrs + behavior: domain, format: mrs
  # ===== 走代理：GFWList 大盘（放直连之后，不压任何直连列表）=====
  gfw_proxy: { type: http, behavior: classical, format: yaml, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/source/geosite_proxy.yaml", path: ./ruleset/geosite_proxy.yaml }  # 含 regex，用 source
  # ===== 直连：中国大陆 IP 段（唯一 IP 规则，必须排在所有域名规则之后）=====
  cn_ip: { type: http, behavior: ipcidr, format: mrs, interval: 86400, proxy: PROXY, url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geoip_cn.mrs", path: ./ruleset/geoip_cn.mrs }
```

</details>

<details open>
<summary><b>② rules（顺序即优先级，别打乱）</b></summary>

```yaml
rules:
  # ----- 拦截：广告 / 追踪 / 遥测（命中即断）-----
  - RULE-SET,reject,REJECT
  - RULE-SET,win_spy,REJECT        # Windows 遥测；想保功能可改 DIRECT
  # ----- 走代理：AI / 流媒体 / 音乐（精确服务，压过直连大盘）-----
  - RULE-SET,openai,PROXY
  - RULE-SET,claude,PROXY
  - RULE-SET,google,PROXY
  - RULE-SET,gemini,PROXY
  - RULE-SET,youtube,PROXY
  - RULE-SET,spotify,PROXY
  - RULE-SET,tiktok,PROXY
  - RULE-SET,netflix,PROXY
  - RULE-SET,disney,PROXY
  - RULE-SET,primevideo,PROXY
  - RULE-SET,hbo,PROXY
  - RULE-SET,playstation,PROXY
  # ----- 直连：国内白名单 / Windows 更新 -----
  - RULE-SET,win_update,DIRECT
  - RULE-SET,cn_direct,DIRECT
  # ----- 走代理：GFWList 大盘（放直连之后，不压任何直连列表）-----
  - RULE-SET,gfw_proxy,PROXY
  # ----- 直连：中国大陆 IP 段（必须排在所有域名规则之后）-----
  - RULE-SET,cn_ip,DIRECT          # 可写成 RULE-SET,cn_ip,DIRECT,no-resolve 免额外 DNS 解析
  - MATCH,PROXY
```

</details>

顺序有讲究，别随手调换：**拦截**最先 → **精确代理服务**（压过直连大盘，这样 `itunes.apple.com`
这类被有意归到 openai 的域名才走代理）→ **直连大盘** → **GFWList 代理大盘**（放在直连之后，
避免它把该直连的 `windowsupdate.com` 之类误拉去代理）→ **IP 规则**（`geoip_cn` 只能匹配以
IP 直连的流量，必须垫在所有域名规则之后）→ 兜底 `MATCH`。想只保留部分服务，删掉不需要的
`rule-providers` 条目和对应的 `RULE-SET` 行即可（成对删）。

上面这段已覆盖全部对外服务集。仓库里还有 `geosite_claude_dns` / `geosite_claude_warp` 两个
Claude 子集，是给「解锁 DNS + WARP 兜底」这种进阶分流单独调度用的（域名已含在 `claude` 里），
一般不需要，故未列入；需要时按同样写法把 `mrs/geosite_claude_dns.mrs`、
`mrs/geosite_claude_warp.mrs` 挂上即可。

下面「[客户端引用方式](#客户端引用方式)」一节讲的是**三种格式怎么选、为什么这么挂**，
想了解取舍再看；只想跑起来，上面两段就够了。

## 结构

| 目录 | 内容 | 说明 |
|------|------|------|
| `source/*.yaml` | 规则**源码**，classical 写法 | **要改规则只改这里**；它本身就是合法规则集，可直接引用 |
| `rules/*.yaml` | `behavior: domain` / `ipcidr` | CI 从 source 编译，勿手改 |
| `mrs/*.mrs` | mihomo 二进制规则集 | CI 从 `rules/` 编译，勿手改 |
| `scripts/ruleset.py` | 源文件的读写与规范化 | 被其它脚本 import |
| `scripts/build_clash.py` | source → `rules/` + `mrs/` | 唯一的编译入口，也是语法检查器 |
| `scripts/validate.py` | 用真实 mihomo 加载全部规则集 | 光校验 YAML 语法证明不了 mihomo 认得 |
| `scripts/check_conflicts.py` | 冲突检查 | `geosite_direct` 与代理类规则集的同域名重叠 |
| `scripts/update_proxy_from_gfwlist.py` | GFWList 转换 | Base64 AutoProxy → `geosite_proxy.yaml`，并剔除 direct 重叠 |
| `scripts/update_geoip_cn.py` | 中国大陆 IP 段同步 | 生成 `geoip_cn.yaml`，内置 5% 变动阈值 |

源码长这样，一行一条 Clash 规则：

```yaml
# source/geosite_openai.yaml
payload:
  - 'DOMAIN,ios.chat.openai.com'
  - 'DOMAIN-SUFFIX,chatgpt.com'
  - 'DOMAIN-KEYWORD,openai'
  - 'DOMAIN-REGEX,^chatgpt-async-webps-prod-\S+-\d+\.webpubsub\.azure\.com$'
```

支持 `DOMAIN` / `DOMAIN-SUFFIX` / `DOMAIN-KEYWORD` / `DOMAIN-REGEX` / `IP-CIDR`
/ `IP-CIDR6` 六种。**引号可有可无、单双引号皆可、行内 `#` 注释会被忽略**——
手写时不必迁就格式，CI 会把入库形态统一回排序去重的样子。写错类型或写坏 CIDR
会在编译时报出文件名和行号。

## 三种格式怎么选

同一个规则集有三份形态，**任选一份引用，别同时挂**。

| 引用什么 | behavior / format | 表达能力 | 适用 |
|---|---|---|---|
| `mrs/<name>.mrs` | `domain` / `ipcidr` + `mrs` | 精确 + 后缀，**不含** keyword / regex | **首选**。mihomo ≥ 1.18.9，体积最小、加载最快 |
| `rules/<name>.yaml` | `domain` / `ipcidr` + `yaml` | 同上 | 客户端不支持 mrs 时 |
| `source/<name>.yaml` | `classical` + `yaml` | **全量无损** | 需要 keyword / regex 时。`DOMAIN-REGEX` 只有 mihomo 支持 |

只有 5 个规则集含 domain 行为表达不了的条目，用 mrs / rules 会**少匹配**这些：

| 规则集 | 被跳过的条目 |
|--------|--------------|
| `geosite_proxy` | 151 条 `DOMAIN-REGEX` |
| `geosite_direct` | 40 条 `DOMAIN-REGEX` |
| `geosite_netflix` | 4 条 `DOMAIN-REGEX` |
| `geosite_openai` | 1 条 `DOMAIN-KEYWORD`、1 条 `DOMAIN-REGEX` |
| `geosite_youtube` | 1 条 `DOMAIN-KEYWORD` |

跳过多少条，每个 `rules/*.yaml` 的文件头注释里也写着。这些 regex 覆盖的是
`javdb99.com`、`apiproxy-device-prod-nlb-*.amazonaws.com`、`ntp1.aliyun.com`
这类动态域名——在意的话，**这几个集单独引用 `source/`，其余仍用 `mrs/`**，
混用没问题。

代价是启动变慢：`geosite_direct` 的 9.5 万条 classical 规则要解析几秒，
而同一份 mrs 是毫秒级。

## 客户端引用方式

本仓库为 public，mihomo 可直接拉 raw（免鉴权）：

```yaml
rule-providers:
  openai:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_openai.mrs"
    path: ./ruleset/geosite_openai.mrs
    interval: 86400
    proxy: PROXY          # 经代理出口下载，绕开 GFW 对 raw.githubusercontent.com 的干扰

  # 需要 keyword / regex 的集直接引用源码（它本身就是 classical 规则集）
  netflix:
    type: http
    behavior: classical
    format: yaml
    url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/source/geosite_netflix.yaml"
    path: ./ruleset/geosite_netflix.yaml
    interval: 86400
    proxy: PROXY

  cn_direct:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geosite_direct.mrs"
    path: ./ruleset/geosite_direct.mrs
    interval: 86400
    proxy: PROXY

  cn_ip:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/kevanpear/clash-rules/master/mrs/geoip_cn.mrs"
    path: ./ruleset/geoip_cn.mrs
    interval: 86400
    proxy: PROXY

rules:
  - RULE-SET,openai,PROXY
  - RULE-SET,netflix,PROXY
  - RULE-SET,cn_direct,DIRECT
  - RULE-SET,cn_ip,DIRECT        # IP 规则放在所有域名规则之后
  - MATCH,PROXY
```

要点：

- `proxy: PROXY` 指向一个已有的代理组名。**不写这行**，规则集更新会走直连，
  在墙内多半拉不到——这正是原来放网盘的理由，现在换成经代理拉 GitHub。
- `interval: 86400` 即一天一刷。push 新规则后客户端自动更新，无需手动操作。
- IP 规则集（`geoip_cn`）必须排在域名规则之后、`MATCH` 之前。想避免为未命中的
  域名额外做一次 DNS 解析，可以写 `RULE-SET,cn_ip,DIRECT,no-resolve`，
  代价是只有本来就以 IP 发起的连接才会命中。

### geoip_cn 为什么必要

其余规则集全是域名匹配。但**不带域名、直接以 IP 发起的连接**（游戏、P2P、
部分 App 的直连 API）匹配不到任何域名规则，会一路落到 `MATCH`。若 `MATCH`
是代理，国内 IP 的流量就绕道境外——只服务本机时不明显，一旦用作**全网透明
代理（旁路由）**就会被放大。

## 如何维护规则

1. 编辑 `source/<name>.yaml`，增删规则行。
2. `git commit && git push`。
3. GitHub Action 自动重编译 `rules/` `mrs/`、规范化 `source/` 并提交回来。
4. 客户端按 `interval` 拉到新版本。

本地预跑（可选，CI 会做同样的事）：

```bash
# 拿一个 mihomo 二进制（本机不常驻，用完即弃）
curl -fsSL -o /tmp/mihomo.gz \
  https://github.com/MetaCubeX/mihomo/releases/download/v1.19.30/mihomo-linux-amd64-v1.19.30.gz
gunzip -f /tmp/mihomo.gz && chmod +x /tmp/mihomo

python3 scripts/build_clash.py --mrs --normalize --mihomo /tmp/mihomo
python3 scripts/check_conflicts.py --strict
python3 scripts/validate.py --mihomo /tmp/mihomo
```

`build_clash.py` 内容不变就不落盘，重复跑不会产生噪声 diff。

## 编译时的语义映射

`source/`（classical）→ `rules/`（domain / ipcidr）：

| 源码 | 编译产物 | 含义 |
|---|---|---|
| `DOMAIN,a.com` | `'a.com'` | 精确 |
| `DOMAIN-SUFFIX,a.com` | `'+.a.com'` | a.com 及其所有子域 |
| `DOMAIN-KEYWORD,k` | — 跳过 | domain 行为表达不了 |
| `DOMAIN-REGEX,re` | — 跳过 | 同上 |
| `IP-CIDR,1.0.0.0/24` | `'1.0.0.0/24'` | ipcidr |
| `IP-CIDR6,2400::/32` | `'2400::/32'` | ipcidr |

一个源文件里域名规则和 IP 规则不能混写——rule-provider 的一个 behavior 只能是
一种，混了会在编译时报错。

## 自动同步

| 工作流 | 触发 | 做什么 |
|---|---|---|
| `build.yml` | push `source/**` 或 `scripts/**` | 重编译 → 冲突检查 → mihomo 真加载 → 提交 |
| `sync-proxy.yml` | 每日 02:40 UTC / 手动 | 同步上游 GFWList → 重编译 → 校验 → 提交 |
| `sync-geoip.yml` | 仅手动 | 刷新中国大陆 IP 段 → 重编译 → 校验 → 提交 |

两个同步工作流都有 **5% 安全阈值**：单次增删总量超过旧规则数的 5% 就失败，
必须人工审核后用 `workflow_dispatch` 勾选 `allow_large_change` 才能发布。
PR 只跑校验、不回写产物。

## 规则集清单

- `geosite_direct` — 直连域名（约 9.5 万条）
- `geosite_proxy` — 走代理域名（GFWList 转换，约 2.4 万条）
- `geosite_openai` — OpenAI 及相关 CDN
- `geosite_google` — 完整 Google 域名集（排除 `@cn`）
- `geosite_google-gemini` — Google Gemini 所需域名
- `geosite_claude` — Anthropic / Claude 全量
- `geosite_claude_dns` — 当前由解锁 DNS 覆盖的 Claude 域名
- `geosite_claude_warp` — 未被解锁 DNS 覆盖、用于 WARP 兜底的 Claude 域名
- `geosite_youtube` `geosite_spotify` `geosite_tiktok` — 流媒体 / 音乐 / 短视频
- `geosite_netflix` `geosite_disney` `geosite_primevideo` `geosite_hbo` — 影视
- `geosite_playstation` — PlayStation / Sony 账号登录及风控域名
- `geoip_cn` — 中国大陆 IP 段（IPv4 + IPv6），唯一的非域名规则集

命名沿用 `geosite_` / `geoip_` 前缀：`check_conflicts.py` 只扫 `geosite_*.yaml`
做域名重叠检查，IP 规则集换前缀即天然跳过。

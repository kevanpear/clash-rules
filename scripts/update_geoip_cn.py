#!/usr/bin/env python3
"""生成 source/geoip_cn.yaml（中国大陆 IPv4 + IPv6 段）。

为什么需要它：本仓库其余规则集全是域名匹配，而**不带域名、直接以 IP
发起的连接**（游戏、P2P、部分 App 的直连 API）匹配不到任何域名规则，
会落到 rules 段末尾的 MATCH 上。若 MATCH 是代理，国内 IP 的流量就会
绕道境外。geoip_cn 用于在 MATCH 之前兜底放行国内 IP。

命名用 geoip_ 而非 geosite_ 前缀：scripts/check_conflicts.py 只扫描
source/geosite_*.yaml（域名重叠检查），IP 规则集不适用该检查，改名即可
天然跳过。

用法:
  python3 scripts/update_geoip_cn.py [--dry-run] [--proxy http://127.0.0.1:7890]
"""
import argparse
import ipaddress
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ruleset  # noqa: E402

SRC = Path(__file__).resolve().parent.parent / "source"
OUT = SRC / "geoip_cn.yaml"

SOURCES = [
    ("IPv4", "https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt"),
    ("IPv6", "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china6.txt"),
]

# 单次变动超过旧规则数的这个比例即视为异常（与 update_proxy_from_gfwlist.py 同思路）
SAFE_RATIO = 0.05

HEADER = [
    "# 中国大陆 IP 段（IPv4 + IPv6）。",
    "# 由 scripts/update_geoip_cn.py 从上游自动生成，请勿手改。",
    "# Clash / mihomo classical 规则集（behavior: classical）；",
    "# 条目数以万计，实际引用建议用编译产物 rules/geoip_cn.yaml 或 mrs/geoip_cn.mrs",
    "#（behavior: ipcidr），匹配快得多。",
]


def fetch(url, proxy):
    if proxy:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    else:
        opener = urllib.request.build_opener()
    with opener.open(url, timeout=60) as response:
        return response.read().decode("utf-8", "replace")


def parse_cidrs(text):
    """逐行解析并用 ipaddress 严格校验，丢弃非法条目。"""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            network = ipaddress.ip_network(line, strict=False)
        except ValueError:
            print("  [skip] 非法 CIDR: %s" % line[:60], file=sys.stderr)
            continue
        out.append(("IP-CIDR6" if network.version == 6 else "IP-CIDR", str(network)))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    parser.add_argument("--proxy", default=None, help="下载用的 HTTP 代理")
    parser.add_argument("--allow-large-change", action="store_true",
                        help="允许超过安全阈值的变动")
    args = parser.parse_args()

    entries = []
    for name, url in SOURCES:
        print("下载 %s ..." % name)
        got = parse_cidrs(fetch(url, args.proxy))
        print("  %s: %d 条" % (name, len(got)))
        entries.extend(got)

    entries = ruleset.sort(entries)
    print("合计去重后: %d 条" % len(entries))

    if not entries:
        print("::error::解析结果为空，中止", file=sys.stderr)
        return 1

    old = 0
    if OUT.exists():
        try:
            old = len(ruleset.load(OUT))
        except ruleset.RuleSetError:
            old = 0

    if old:
        delta = abs(len(entries) - old)
        if delta > old * SAFE_RATIO and not args.allow_large_change:
            print("::error::变动 %d 条，超过旧规则数 %d 的 %.0f%% —— "
                  "请人工核对后用 --allow-large-change 发布"
                  % (delta, old, SAFE_RATIO * 100), file=sys.stderr)
            return 1
        print("与上一版相比变动 %d 条（旧 %d）" % (delta, old))

    if args.dry_run:
        print("[dry-run] 不写入。前 3 条: %s" % entries[:3])
        return 0

    ruleset.write_if_changed(OUT, ruleset.dump(entries, HEADER))
    print("已写入 %s（%d 条）" % (OUT, len(entries)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

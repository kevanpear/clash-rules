#!/usr/bin/env python3
"""从 Loyalsoldier/v2ray-rules-dat 同步几个细分列表 → Clash classical 规则集。

  geosite_reject      广告/追踪域名（reject-list）—— 用于拦截
  geosite_win_update  Windows 更新域名 —— 动辄几个 GB，不该吃代理流量
  geosite_win_spy     Windows 遥测域名 —— 拦截或直连，由客户端侧决定

本脚本是 sing-box-rules 侧 scripts/update_upstream_lists.py 的对应实现，
两边同步**同一个上游**、用**同一套转换语义**，以保证两个仓库规则内容一致
（见 README：内容一致、写法不同）。转换语义与那边逐条对齐：

  裸域名   → DOMAIN-SUFFIX   （v2ray 的 domain: 本就是后缀匹配）
  full:    → DOMAIN          （精确）
  regexp:  → DOMAIN-REGEX
  keyword: → DOMAIN-KEYWORD

用法：
  python3 scripts/update_upstream_lists.py [--only geosite_reject] [--dry-run]
"""
import argparse
import sys
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ruleset  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"

BASE_RAW = "https://raw.githubusercontent.com/Loyalsoldier/v2ray-rules-dat/release"
BASE_CDN = "https://fastly.jsdelivr.net/gh/Loyalsoldier/v2ray-rules-dat@release"

# 规则集名 -> (上游文件名, 规则数下限)
# 下限与 sing-box 侧保持一致：低于此值几乎肯定是上游文件截断或为空，
# 宁可同步失败，也不要发布一个残缺的清单。
LISTS = {
    "geosite_reject":     ("reject-list", 100000),
    "geosite_win_update": ("win-update", 300),
    "geosite_win_spy":    ("win-spy", 200),
}

HEADERS = {
    "geosite_reject": (
        "# 广告与追踪域名（上游 Loyalsoldier/v2ray-rules-dat 的 reject-list）。",
        "# Clash / mihomo classical 规则集，可直接被 rule-provider 引用；",
        "# behavior: classical, format: yaml。",
        "# 由 scripts/update_upstream_lists.py 自动生成，勿手改。",
    ),
    "geosite_win_update": (
        "# Windows 更新域名（上游 win-update）。更新包动辄数百 MB 到数 GB，",
        "# 走代理纯属浪费流量，通常配置为直连。",
        "# 由 scripts/update_upstream_lists.py 自动生成，勿手改。",
    ),
    "geosite_win_spy": (
        "# Windows 遥测域名（上游 win-spy）。可配置为拦截或直连——",
        "# 拦截有影响系统功能的风险，直连则至少不占代理带宽。",
        "# 由 scripts/update_upstream_lists.py 自动生成，勿手改。",
    ),
}


def fetch(urls):
    last = None
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read().decode("utf-8")
            print("[fetch] {} ({} 字节)".format(url, len(data.encode("utf-8"))))
            return data
        except (urllib.error.URLError, OSError) as exc:
            print("[warn] 取不到 {}: {}".format(url, exc))
            last = exc
    raise RuntimeError("所有源都取不到：{}".format(last))


def parse_domain_list(text):
    """v2ray 风格纯文本 → [(类型, 值)]，语义与 sing-box 侧逐条对齐。"""
    entries = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split()[0]          # 去掉 " @attr" 之类的尾随属性
        if line.startswith("full:"):
            value = line[5:].strip().lstrip(".").lower()
            kind = "DOMAIN"
        elif line.startswith("regexp:"):
            value = line[7:]
            kind = "DOMAIN-REGEX"
            if not value:
                raise ValueError("第 {} 行是空正则".format(number))
        elif line.startswith("keyword:"):
            value = line[8:]
            kind = "DOMAIN-KEYWORD"
        else:
            value = line.strip().lstrip(".").lower()
            kind = "DOMAIN-SUFFIX"
        if not value:
            raise ValueError("第 {} 行解析出空值".format(number))
        entries.append((kind, value))
    return entries


def sync(name, upstream, minimum, args):
    print("\n=== {} <- {}.txt ===".format(name, upstream))
    text = fetch(["{}/{}.txt".format(BASE_RAW, upstream),
                  "{}/{}.txt".format(BASE_CDN, upstream)])
    entries = ruleset.sort(parse_domain_list(text))

    path = SRC / "{}.yaml".format(name)
    first_time = not path.exists()
    old = set(ruleset.load(path)) if not first_time else set()
    new = set(entries)
    added, removed = len(new - old), len(old - new)
    base = len(old) or 1
    ratio = (added + removed) / base
    print("[delta] old={} new={} add={} remove={} ratio={:.2%}".format(
        len(old), len(new), added, removed, ratio))

    if len(new) < minimum:
        raise RuntimeError("生成的规则数 {} 低于安全下限 {}".format(len(new), minimum))
    if first_time:
        print("[init] 首次生成，跳过变动比例检查")
    elif ratio > args.max_change_ratio and not args.allow_large_change:
        raise RuntimeError(
            "变动比例 {:.2%} 超过上限 {:.2%}；确认无误后加 --allow-large-change".format(
                ratio, args.max_change_ratio))

    content = ruleset.dump(entries, header=HEADERS.get(name, ()))
    if args.dry_run:
        print("[dry-run] {} 会被更新".format(path))
        return False
    changed = ruleset.write_if_changed(path, content)
    print("[write] {}".format(path) if changed else "[skip] 内容无变化")
    return changed


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", choices=sorted(LISTS),
                        help="只同步指定规则集（可重复）")
    parser.add_argument("--max-change-ratio", type=float, default=0.15,
                        help="(新增+移除)/旧规则数 的上限（默认 0.15）")
    parser.add_argument("--allow-large-change", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    changed = []
    for name in (args.only or sorted(LISTS)):
        upstream, minimum = LISTS[name]
        if sync(name, upstream, minimum, args):
            changed.append(name)
    print("\n[done] 有变化的规则集: {}".format(", ".join(changed) or "(无)"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print("[error] {}".format(exc), file=sys.stderr)
        sys.exit(1)

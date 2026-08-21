#!/usr/bin/env python3
"""把上游 AutoProxy GFWList 转成 source/geosite_proxy.yaml。

上游文件是 Base64 编码的 AutoProxy 列表：域名锚点（||a.com^）变成
DOMAIN-SUFFIX，URL 锚点（|http://a.com/x）变成 DOMAIN，正则原样保留成
DOMAIN-REGEX，其余裸条目变成 DOMAIN-KEYWORD。

已经出现在 geosite_direct 里的精确条目会被剔除，避免生成的代理表把
直连/代理冲突重新引进来。

安全阈值：单次增删总量超过旧规则数的 5% 就报错，需人工确认后加
--allow-large-change 才写盘。
"""

import argparse
import base64
import binascii
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ruleset  # noqa: E402

PRIMARY_URL = (
    "https://raw.githubusercontent.com/YW5vbnltb3Vz/"
    "domain-list-community/release/gfwlist.txt"
)
FALLBACK_URL = (
    "https://fastly.jsdelivr.net/gh/YW5vbnltb3Vz/"
    "domain-list-community@release/gfwlist.txt"
)
KINDS = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX")
# 精确类型：与 direct 比对、以及判断重叠时只看这两类
EXACT_KINDS = ("DOMAIN", "DOMAIN-SUFFIX")

HEADER = [
    "# 走代理的域名。",
    "# 由 scripts/update_proxy_from_gfwlist.py 从上游 GFWList 自动生成，请勿手改；",
    "# 要长期加/去某个域名，改 source/geosite_direct.yaml 或另建规则集。",
    "# Clash / mihomo classical 规则集，可直接被 rule-provider 引用",
    "#（behavior: classical, format: yaml）。",
]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=PRIMARY_URL)
    parser.add_argument("--fallback", default=FALLBACK_URL)
    parser.add_argument("--output", type=Path, default=Path("source/geosite_proxy.yaml"))
    parser.add_argument("--direct", type=Path, default=Path("source/geosite_direct.yaml"))
    parser.add_argument("--max-change-ratio", type=float, default=0.05,
                        help="maximum (additions + removals) / old rule count (default: 0.05)")
    parser.add_argument("--minimum-rules", type=int, default=10_000,
                        help="reject generated lists smaller than this (default: 10000)")
    parser.add_argument("--allow-large-change", action="store_true",
                        help="accept a change larger than --max-change-ratio")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and report without writing the output file")
    return parser.parse_args()


def fetch(urls):
    errors = []
    for url in urls:
        if not url:
            continue
        request = urllib.request.Request(
            url,
            headers={"Accept": "text/plain", "User-Agent": "clash-rules-sync/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
            if len(body) < 1_000:
                raise ValueError("response is unexpectedly small: {} bytes".format(len(body)))
            print("[fetch] {} ({} bytes)".format(url, len(body)))
            return body
        except (OSError, ValueError, urllib.error.URLError) as exc:
            errors.append("{}: {}".format(url, exc))
    raise RuntimeError("all upstream downloads failed:\n  " + "\n  ".join(errors))


def decode_autoproxy(raw):
    compact = b"".join(raw.split())
    try:
        decoded = base64.b64decode(compact, validate=True).decode("ascii")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("upstream is not valid Base64-encoded ASCII") from exc
    lines = decoded.splitlines()
    if not lines or lines[0].strip() != "[AutoProxy 0.2.9]":
        raise ValueError("missing expected AutoProxy 0.2.9 header")
    return lines


def clean_domain(value, line_number):
    value = value.strip().lower().rstrip(".")
    if (
        not value
        or any(char.isspace() for char in value)
        or any(char in value for char in "/|^")
    ):
        raise ValueError("invalid domain at decoded line {}: {!r}".format(line_number, value))
    return value


def parse_rules(lines):
    rules = {kind: set() for kind in KINDS}
    metadata = []
    for line_number, raw_line in enumerate(lines, 1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("!") or line.startswith("["):
            metadata.append(line)
            continue
        if line.startswith("@@"):
            raise ValueError("unsupported AutoProxy exception at decoded line {}: {}"
                             .format(line_number, line))
        if line.startswith("||"):
            value = line[2:]
            if value.endswith("^"):
                value = value[:-1]
            rules["DOMAIN-SUFFIX"].add(clean_domain(value, line_number))
            continue
        if line.startswith("|http://") or line.startswith("|https://"):
            parsed = urlsplit(line[1:])
            if not parsed.hostname:
                raise ValueError("URL anchor has no hostname at decoded line {}: {}"
                                 .format(line_number, line))
            rules["DOMAIN"].add(clean_domain(parsed.hostname, line_number))
            continue
        if len(line) >= 2 and line.startswith("/") and line.endswith("/"):
            expression = line[1:-1]
            if not expression:
                raise ValueError("empty regex at decoded line {}".format(line_number))
            rules["DOMAIN-REGEX"].add(expression)
            continue
        if line.startswith("|") or any(char.isspace() for char in line):
            raise ValueError("unsupported AutoProxy syntax at decoded line {}: {}"
                             .format(line_number, line))
        rules["DOMAIN-KEYWORD"].add(line)
    return rules, metadata


def load_exact_terms(path):
    """一个规则集里的精确域名集合，用于剔除与 direct 的重叠。"""
    if not path.exists():
        return set()
    return set(value.lower()
               for value in ruleset.values(ruleset.load(path), *EXACT_KINDS))


def load_existing(path):
    buckets = {kind: set() for kind in KINDS}
    if not path.exists():
        return buckets
    for kind, value in ruleset.load(path):
        if kind in buckets:
            buckets[kind].add(value)
    return buckets


def report_delta(old, new):
    additions = 0
    removals = 0
    for kind in KINDS:
        added = len(new[kind] - old[kind])
        removed = len(old[kind] - new[kind])
        additions += added
        removals += removed
        print("[delta] {:15s} old={:6d} new={:6d} add={:5d} remove={:5d}"
              .format(kind, len(old[kind]), len(new[kind]), added, removed))
    old_total = sum(len(old[kind]) for kind in KINDS)
    new_total = sum(len(new[kind]) for kind in KINDS)
    ratio = (additions + removals) / max(old_total, 1)
    print("[delta] total old={} new={} add={} remove={} ratio={:.2%}"
          .format(old_total, new_total, additions, removals, ratio))
    return old_total, new_total, ratio


def render(rules):
    entries = [(kind, value) for kind in KINDS for value in rules[kind]]
    return ruleset.dump(ruleset.sort(entries), HEADER)


def main():
    args = parse_args()
    if not 0 <= args.max_change_ratio <= 1:
        raise ValueError("--max-change-ratio must be between 0 and 1")

    raw = fetch(dict.fromkeys((args.source, args.fallback)))
    rules, metadata = parse_rules(decode_autoproxy(raw))
    direct_terms = load_exact_terms(args.direct)
    before_filter = sum(len(rules[kind]) for kind in EXACT_KINDS)
    for kind in EXACT_KINDS:
        rules[kind] -= direct_terms
    filtered = before_filter - sum(len(rules[kind]) for kind in EXACT_KINDS)
    print("[filter] removed {} exact terms already present in direct".format(filtered))
    for line in metadata:
        if line.startswith("! Last Modified:"):
            print("[source]{}".format(line[1:]))

    old = load_existing(args.output)
    _, new_total, ratio = report_delta(old, rules)
    if new_total < args.minimum_rules:
        raise RuntimeError("generated rule count {} is below safety minimum {}"
                           .format(new_total, args.minimum_rules))
    if ratio > args.max_change_ratio and not args.allow_large_change:
        raise RuntimeError("change ratio {:.2%} exceeds safety limit {:.2%}; "
                           "review and rerun with --allow-large-change"
                           .format(ratio, args.max_change_ratio))

    content = render(rules)
    if args.output.exists() and args.output.read_text(encoding="utf-8") == content:
        print("[ok] {} is already up to date".format(args.output))
        return 0
    if args.dry_run:
        print("[dry-run] {} would be updated".format(args.output))
        return 0
    ruleset.write_if_changed(args.output, content)
    print("[write] updated {}".format(args.output))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("[error] {}".format(exc), file=sys.stderr)
        sys.exit(1)

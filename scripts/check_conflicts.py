#!/usr/bin/env python3
"""跨规则集冲突检查。

直连大盘 geosite_direct 与所有走代理的规则集之间，若出现同一个
DOMAIN / DOMAIN-SUFFIX 同时被列入，路由结果就只取决于 rules 段里谁写在前面，
容易出诡异 bug。默认只告警；CI 用 --strict 把重叠视为失败。

只扫 source/geosite_*.yaml —— IP 规则集（geoip_*）不适用域名重叠检查，
换前缀即天然跳过。

用法: python3 scripts/check_conflicts.py [--strict]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ruleset  # noqa: E402

SRC = Path(__file__).resolve().parent.parent / "source"
DIRECT = "geosite_direct"


def load_terms(path):
    """该规则集里的精确域名集合（DOMAIN + DOMAIN-SUFFIX）。

    KEYWORD / REGEX 不参与：它们是模糊匹配，跟精确条目比对只会产生噪声。
    """
    entries = ruleset.load(path)
    return set(ruleset.values(entries, "DOMAIN", "DOMAIN-SUFFIX"))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="return a non-zero status when conflicts are found")
    return parser.parse_args()


def main():
    args = parse_args()
    direct_path = SRC / ("%s.yaml" % DIRECT)
    if not direct_path.exists():
        print("[skip] 找不到 %s" % direct_path)
        return 0

    direct_terms = load_terms(direct_path)
    total = 0
    for path in sorted(SRC.glob("geosite_*.yaml")):
        name = path.stem
        if name == DIRECT:
            continue
        overlap = direct_terms & load_terms(path)
        if overlap:
            total += len(overlap)
            print("::warning::%s 与 %s 重叠 %d 个域名: %s%s"
                  % (DIRECT, name, len(overlap), ", ".join(sorted(overlap)[:20]),
                     " ..." if len(overlap) > 20 else ""))

    if total == 0:
        print("[ok] 无跨表域名冲突")
    else:
        print("[warn] 共发现 %d 处直连/代理重叠 —— 请确认路由顺序符合预期" % total)
    return 1 if total and args.strict else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ruleset.RuleSetError as exc:
        print("[error] %s" % exc, file=sys.stderr)
        sys.exit(1)

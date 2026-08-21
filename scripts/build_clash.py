#!/usr/bin/env python3
"""把 source/*.yaml（classical 写法）编译成两种高性能产物。

  source/<name>.yaml   手写的 classical 规则集，**本身就能被 rule-provider 直接引用**
                       （behavior: classical, format: yaml），DOMAIN-KEYWORD /
                       DOMAIN-REGEX 全量无损。
        │
        ├─> rules/<name>.yaml   behavior: domain 或 ipcidr。结构化匹配，性能好，
        │                       但 domain 行为**表达不了** DOMAIN-KEYWORD /
        │                       DOMAIN-REGEX，这类条目会被跳过（跳过多少条会写进
        │                       文件头注释，也打印到 stdout）。
        └─> mrs/<name>.mrs      由上面那份 yaml 转成的 mihomo 二进制，体积最小、
                                加载最快。需要 mihomo ≥ 1.18.9。

语义映射：

  DOMAIN,a.com          -> 'a.com'         精确
  DOMAIN-SUFFIX,a.com   -> '+.a.com'       a.com 及其所有子域（与 clash 的
                                           DOMAIN-SUFFIX 语义一致）
  DOMAIN-KEYWORD,k      -> 跳过
  DOMAIN-REGEX,re       -> 跳过
  IP-CIDR,1.0.0.0/24    -> '1.0.0.0/24'    behavior: ipcidr
  IP-CIDR6,2400::/32    -> '2400::/32'

用法：
  python3 scripts/build_clash.py                      # 只生成 rules/
  python3 scripts/build_clash.py --mrs                # 额外生成 mrs/（需要 mihomo）
  python3 scripts/build_clash.py --mrs --mihomo ./mihomo
  python3 scripts/build_clash.py --normalize          # 顺带把 source/ 排序去重写回
  python3 scripts/build_clash.py --check              # 只校验产物是否已最新
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ruleset  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source"
RULES = ROOT / "rules"
MRS = ROOT / "mrs"


def read_header(path):
    """取出 payload: 之前的注释行，normalize 写回时原样保留。"""
    header = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            stripped = raw.strip()
            if stripped.startswith("#"):
                header.append(raw.rstrip("\n"))
                continue
            if stripped:
                break
    return header


def behavior_of(entries, name):
    kinds = set(kind for kind, _ in entries)
    has_ip = bool(kinds & set(ruleset.IP_TYPES))
    has_domain = bool(kinds & set(ruleset.DOMAIN_TYPES))
    if has_ip and has_domain:
        raise SystemExit(
            "[error] source/%s.yaml 同时含域名与 IP 规则；"
            "clash 的 rule-provider 一个 behavior 只能是一种，请拆成两个文件。" % name
        )
    return "ipcidr" if has_ip else "domain"


def header_for(name, behavior, skipped):
    lines = [
        "# 由 scripts/build_clash.py 从 source/%s.yaml 编译，请勿手改。" % name,
        "# 要改规则请改 source/%s.yaml，push 后 CI 会自动重编译。" % name,
        "# behavior: %s, format: yaml" % behavior,
    ]
    if skipped:
        detail = "、".join("%d 条 %s" % (count, kind) for kind, count in skipped)
        lines.append("# 注意：本规则集另有 %s 无法用 %s 行为表达，已跳过；"
                     % (detail, behavior))
        lines.append("#       需要完整语义请直接引用 source/%s.yaml"
                     "（behavior: classical）。" % name)
    return lines


def build_payload(entries, behavior):
    """返回 (payload 行, 被跳过的类型计数)。"""
    payload = []
    skipped = []
    if behavior == "ipcidr":
        payload = ruleset.values(entries, *ruleset.IP_TYPES)
    else:
        payload = ruleset.values(entries, "DOMAIN")
        # DOMAIN-SUFFIX,a.com 命中 a.com 与所有子域 —— domain 行为里写作 +.a.com
        payload += ["+." + value for value in ruleset.values(entries, "DOMAIN-SUFFIX")]
        for kind in ("DOMAIN-KEYWORD", "DOMAIN-REGEX"):
            count = len(ruleset.values(entries, kind))
            if count:
                skipped.append((kind, count))
    return sorted(set(payload)), skipped


def convert_mrs(mihomo, behavior, yaml_path, mrs_path):
    mrs_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [mihomo, "convert-ruleset", behavior, "yaml", str(yaml_path), str(mrs_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("mihomo convert-ruleset %s 失败：%s"
                           % (yaml_path.name, (result.stderr or result.stdout).strip()[:400]))


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mrs", action="store_true", help="额外生成 mrs/（需要 mihomo）")
    parser.add_argument("--mihomo", default="mihomo", help="mihomo 可执行文件路径")
    parser.add_argument("--normalize", action="store_true",
                        help="把 source/ 排序去重后写回（手写完可以随手跑一下）")
    parser.add_argument("--check", action="store_true",
                        help="只校验产物是否已最新，有差异则以非零码退出")
    return parser.parse_args()


def main():
    args = parse_args()
    sources = sorted(SRC.glob("*.yaml"))
    if not sources:
        print("[error] source/ 下没有规则集", file=sys.stderr)
        return 1

    changed = []
    for path in sources:
        name = path.stem
        entries = ruleset.sort(ruleset.load(path))
        behavior = behavior_of(entries, name)

        if args.normalize:
            content = ruleset.dump(entries, read_header(path))
            if ruleset.write_if_changed(path, content):
                changed.append(path)
                print("[normalize] source/%s.yaml 已排序去重" % name)

        payload, skipped = build_payload(entries, behavior)
        lines = header_for(name, behavior, skipped) + ["payload:"]
        lines += ["  - " + ruleset.quote(item) for item in payload]
        rules_path = RULES / ("%s.yaml" % name)
        if ruleset.write_if_changed(rules_path, "\n".join(lines) + "\n"):
            changed.append(rules_path)

        note = ""
        if skipped:
            note = "（跳过 %s）" % "、".join("%d %s" % (c, k) for k, c in skipped)
        print("[%s] source/%s.yaml %d 条 -> rules/%s.yaml %d 条%s"
              % (behavior, name, len(entries), name, len(payload), note))

        if args.mrs:
            mrs_path = MRS / ("%s.mrs" % name)
            convert_mrs(args.mihomo, behavior, rules_path, mrs_path)
            print("[mrs]    mrs/%s.mrs %.1f KiB" % (name, mrs_path.stat().st_size / 1024))

    if args.check and changed:
        print("[error] 以下文件不是最新的，请先跑 scripts/build_clash.py --normalize：\n  "
              + "\n  ".join(str(p.relative_to(ROOT)) for p in changed), file=sys.stderr)
        return 1
    print("[ok] 共处理 %d 个规则集，更新 %d 个文件" % (len(sources), len(changed)))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ruleset.RuleSetError, RuntimeError) as exc:
        print("[error] %s" % exc, file=sys.stderr)
        sys.exit(1)

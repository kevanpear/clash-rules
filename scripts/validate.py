#!/usr/bin/env python3
"""用真实的 mihomo 加载全部规则集，确认它们真的能被解析。

YAML 语法检查只能证明文件是合法 YAML，证明不了 mihomo 认得 `+.` 前缀、
认得 DOMAIN-REGEX、认得 mrs 的版本号。这里生成一份把 source/（classical）、
rules/（domain / ipcidr）、mrs/ 全部挂成 file provider 的临时配置，
交给 `mihomo -t` 做真加载。

用法:
  python3 scripts/validate.py [--mihomo ./mihomo]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def behavior_of(name):
    """geoip_* 是 IP 规则集，其余是域名规则集。"""
    return "ipcidr" if name.startswith("geoip_") else "domain"


def collect():
    """返回 [(provider_tag, behavior, format, 绝对路径)]。"""
    entries = []
    for path in sorted((ROOT / "source").glob("*.yaml")):
        entries.append(("src_" + path.stem, "classical", "yaml", path))
    for path in sorted((ROOT / "rules").glob("*.yaml")):
        entries.append(("d_" + path.stem, behavior_of(path.stem), "yaml", path))
    for path in sorted((ROOT / "mrs").glob("*.mrs")):
        entries.append(("m_" + path.stem, behavior_of(path.stem), "mrs", path))
    return entries


def render_config(entries):
    lines = [
        "mixed-port: 17890",
        "mode: rule",
        "log-level: warning",
        "proxies: []",
        "proxy-groups:",
        "  - {name: PROXY, type: select, proxies: [DIRECT]}",
        "rule-providers:",
    ]
    for tag, behavior, fmt, path in entries:
        lines.append("  %s: {type: file, behavior: %s, format: %s, path: %s}"
                     % (tag, behavior, fmt, path))
    lines.append("rules:")
    for tag, _, _, _ in entries:
        lines.append("  - RULE-SET,%s,DIRECT" % tag)
    lines.append("  - MATCH,PROXY")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mihomo", default="mihomo", help="mihomo 可执行文件路径")
    args = parser.parse_args()

    if shutil.which(args.mihomo) is None and not Path(args.mihomo).exists():
        print("[error] 找不到 mihomo：%s（下载见 README）" % args.mihomo, file=sys.stderr)
        return 1

    entries = collect()
    if not entries:
        print("[error] source/ rules/ mrs/ 都是空的，先跑 build_clash.py", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as workdir:
        config = Path(workdir) / "config.yaml"
        config.write_text(render_config(entries), encoding="utf-8")
        # mihomo 只允许 file provider 指向 -d 目录或 SAFE_PATHS 之下，
        # 这里把仓库根显式放行，省得把几 MB 产物复制进临时目录。
        env = dict(os.environ, SAFE_PATHS=str(ROOT))
        result = subprocess.run(
            [args.mihomo, "-t", "-d", workdir, "-f", str(config)],
            capture_output=True, text=True, env=env)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            print("[error] mihomo 拒绝加载上述规则集", file=sys.stderr)
            return 1

    print("[ok] mihomo 成功加载 %d 个规则集（classical %d / yaml %d / mrs %d）" % (
        len(entries),
        sum(1 for e in entries if e[0].startswith("src_")),
        sum(1 for e in entries if e[0].startswith("d_")),
        sum(1 for e in entries if e[0].startswith("m_")),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())

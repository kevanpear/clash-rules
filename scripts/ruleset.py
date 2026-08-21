#!/usr/bin/env python3
"""source/*.yaml（Clash classical 规则集）的读写。

只被其它脚本 import，不单独执行。

刻意不依赖 PyYAML：源文件的形态是固定的「注释 + payload: + 一行一条规则」，
自己解析反而能对写歪的行给出精确报错，也省掉 CI 里一次 pip 安装。
解析是容错的——引号可有可无、单双引号皆可、行内 `#` 注释会被剥掉——
手写时不必迁就格式，`build_clash.py --normalize` 会把入库形态统一回来。
"""
import ipaddress
import os
import re
import tempfile

# 顺序即规范化后的输出顺序：先精确、再后缀、再模糊、最后 IP
RULE_TYPES = (
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-REGEX",
    "IP-CIDR",
    "IP-CIDR6",
)
DOMAIN_TYPES = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX")
IP_TYPES = ("IP-CIDR", "IP-CIDR6")

# behavior: domain 能表达的类型；keyword / regex 表达不了
DOMAIN_BEHAVIOR_TYPES = ("DOMAIN", "DOMAIN-SUFFIX")

_ITEM = re.compile(r"^\s*-\s*(.+?)\s*$")


class RuleSetError(ValueError):
    """源文件写法有误。消息里带文件名与行号。"""


def _strip_inline_comment(text):
    """剥掉行尾注释。带引号的值里出现 # 不算注释。"""
    if text[:1] in ("'", '"'):
        quote = text[0]
        end = 1
        while end < len(text):
            if text[end] == quote:
                if text[end:end + 2] == quote * 2:   # YAML 里 '' 表示一个引号
                    end += 2
                    continue
                end += 1
                break
            end += 1
        head, tail = text[:end], text[end:]
        return head + tail.split("#", 1)[0]
    return text.split("#", 1)[0]


def _unquote(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        inner = text[1:-1]
        return inner.replace("''", "'") if text[0] == "'" else inner
    return text


def parse_line(raw, path=None, lineno=None):
    """把一行 payload 解析成 (类型, 值)；不是规则行返回 None。"""
    stripped = raw.strip()
    if not stripped or stripped.startswith("#") or stripped == "payload:":
        return None
    match = _ITEM.match(raw)
    if not match:
        raise RuleSetError("%s:%s 既不是注释也不是 `- 规则` 行：%r"
                           % (path, lineno, raw.rstrip()))
    value = _unquote(_strip_inline_comment(match.group(1)))
    if not value:
        return None
    if "," not in value:
        raise RuleSetError("%s:%s 缺少规则类型前缀（应形如 DOMAIN-SUFFIX,a.com）：%r"
                           % (path, lineno, value))
    kind, _, payload = value.partition(",")
    kind = kind.strip().upper()
    payload = payload.strip()
    if kind not in RULE_TYPES:
        raise RuleSetError("%s:%s 不支持的规则类型 %r（支持：%s）"
                           % (path, lineno, kind, "、".join(RULE_TYPES)))
    if not payload:
        raise RuleSetError("%s:%s 规则 %s 的值为空" % (path, lineno, kind))
    if kind in IP_TYPES:
        try:
            network = ipaddress.ip_network(payload, strict=False)
        except ValueError as exc:
            raise RuleSetError("%s:%s 非法 CIDR %r：%s" % (path, lineno, payload, exc))
        expect = "IP-CIDR6" if network.version == 6 else "IP-CIDR"
        if kind != expect:
            raise RuleSetError("%s:%s %s 是 IPv%d 网段，应写成 %s"
                               % (path, lineno, payload, network.version, expect))
    return kind, payload


def load(path):
    """读一个 classical 源文件，返回去重后的 [(类型, 值)]（保持出现顺序）。"""
    entries = []
    seen = set()
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            item = parse_line(raw, path=path, lineno=lineno)
            if item is None or item in seen:
                continue
            seen.add(item)
            entries.append(item)
    return entries


def values(entries, *kinds):
    """取出指定类型的值列表。"""
    return [value for kind, value in entries if kind in kinds]


def counts(entries):
    """按类型计数，只含出现过的类型。"""
    result = {}
    for kind, _ in entries:
        result[kind] = result.get(kind, 0) + 1
    return result


def _sort_key(item):
    kind, value = item
    order = RULE_TYPES.index(kind)
    if kind in IP_TYPES:
        network = ipaddress.ip_network(value, strict=False)
        return (order, 1, "", int(network.network_address), network.prefixlen)
    return (order, 0, value, 0, 0)


def sort(entries):
    return sorted(set(entries), key=_sort_key)


def quote(value):
    """YAML 单引号标量：内部单引号写成两个。"""
    return "'" + value.replace("'", "''") + "'"


def dump(entries, header=()):
    lines = list(header)
    lines.append("payload:")
    lines += ["  - " + quote("%s,%s" % (kind, value)) for kind, value in entries]
    return "\n".join(lines) + "\n"


def write_if_changed(path, content):
    """内容不变就不落盘，免得 CI 产生空提交。返回是否写了。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    return True

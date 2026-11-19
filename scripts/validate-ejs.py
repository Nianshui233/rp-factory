#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分档控制器（EJS）校验器：查语法纪律、变量路径、被控条目与边界连续性。

用法：
    python scripts/validate-ejs.py <控制器.ejs> [--book <世界书.json>] [--no-mvu] [--range 0,100]

--book      native 世界书（对象形状或数组形状都认）：查 getwi 的条目是否存在且已禁用
--no-mvu    没有 MVU 时用 initial. 前缀，getvar 路径降级检查
--range     轴的取值区间，E06 用它判"两端有没有盖住"，默认 0,100

退出码：0 全过；1 有 FAIL；2 用法错误。
只依赖标准库。
"""
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PLACEHOLDERS = ('【AI补全·可替换】', '[待定', '【未知】')
BANNED = ('JSON.parse', 'fetch(', 'require(', 'new Function', 'eval(', 'XMLHttpRequest')


class Report:
    def __init__(self):
        self.fails = []
        self.warns = []
        self.oks = []

    def fail(self, msg):
        self.fails.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def ok(self, msg):
        self.oks.append(msg)


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def blocks(src):
    """返回所有 <%_ … _%> / <%- … %> / <% … %> 的 (开标签, 内容)。"""
    return re.findall(r'<%(=?[-_]?)(.*?)%>', src, re.S)


def check(path, book_p, no_mvu, rng):
    r = Report()
    src = read(path)

    # E01 标签纪律：只许 <%_ … _%>
    loose = re.findall(r'<%(?![-_=#])', src)
    eq = re.findall(r'<%=', src)
    if loose or eq:
        r.fail(f'E01 有 {len(loose) + len(eq)} 处非 <%_ _%> 标签（<% 、<%= 会留空行，一多就撑爆上下文）')
    else:
        r.ok('E01 只用 <%_ _%>（<%- 输出标签不计）')

    bs = blocks(src)
    if not bs:
        r.fail('E01 文件里一个 EJS 标签都没有——控制器不渲染等于没做')
        return r

    # E02 首个块里的变量要有 typeof 守卫 + var
    first = bs[0][1]
    declares = re.findall(r'\bvar\s+(\w+)\s*=\s*getvar', first)
    if re.search(r'\bgetvar\(', first) and not declares:
        r.fail('E02 首个块里有 getvar 但没有 var 声明')
    for name in declares:
        if not re.search(r"typeof\s+" + re.escape(name) + r"\s*===\s*'undefined'", first):
            r.fail(f'E02 变量 {name} 缺 typeof 守卫——重复渲染会抛 Identifier has already been declared')
        if re.search(r'\b(?:let|const)\s+' + re.escape(name) + r'\b', src):
            r.fail(f'E02 变量 {name} 用了 let/const——多次渲染会重复声明，必须用 var')
    if declares and not r.fails:
        r.ok(f'E02 {len(declares)} 个变量都有 typeof 守卫 + var')

    # 循环里的局部变量不算（只查首个块，已由上面保证）

    # E03 getvar 路径前缀
    paths = re.findall(r"getvar\(\s*'([^']+)'", src) + re.findall(r'getvar\(\s*"([^"]+)"', src)
    if paths:
        if no_mvu:
            bad = [p for p in paths if not (p.startswith('stat_data.') or p.startswith('initial.'))]
            if bad:
                r.warn(f'E03 --no-mvu 下路径应以 initial. 开头：{bad[:2]}')
            else:
                r.ok('E03 路径前缀合规（initial.）')
        else:
            bad = [p for p in paths if not p.startswith('stat_data.')]
            if bad:
                for b in bad:
                    r.fail(f'E03 getvar 路径「{b}」没有 stat_data. 前缀——读到的永远是 undefined')
            else:
                r.ok(f'E03 {len(paths)} 条 getvar 路径都以 stat_data. 开头')

    # E04 getwi 必须 await；条目名能从 --book 找到
    getwi = re.findall(r'(await\s+)?getwi\(\s*null\s*,\s*[\'"]([^\'"]+)[\'"]', src)
    no_await = [n for a, n in getwi if not a]
    if no_await:
        for n in no_await:
            r.fail(f'E04 getwi 少了 await（{n}）——拿到的是 Promise，渲染出来是 [object Promise]')
    if getwi and not no_await:
        r.ok(f'E04 {len(getwi)} 处 getwi 都带 await')

    names = [n for _, n in getwi]
    if book_p and names:
        try:
            raw = json.loads(read(book_p))
            ents = raw.get('entries') if isinstance(raw, dict) else raw
            if isinstance(ents, list):
                ents = {str(i): v for i, v in enumerate(ents)}
            by_comment = {str(v.get('comment', '')): v for v in ents.values() if isinstance(v, dict)}
            miss = [n for n in names if n not in by_comment]
            if miss:
                for n in miss:
                    r.fail(f'E04 被控条目「{n}」在世界书里找不到')
            else:
                r.ok(f'E04 {len(names)} 个被控条目都存在')
            still_on = [n for n in names if n in by_comment
                        and by_comment[n].get('enabled', True) is not False
                        and by_comment[n].get('disable', False) is not True]
            if still_on:
                for n in still_on:
                    r.fail(f'E05 被控条目「{n}」没禁用——它会同控制器一起常驻，等于白拆')
            elif not miss:
                r.ok('E05 被控条目全部禁用')
        except Exception as e:
            r.fail(f'E04 世界书读不了：{e}')

    # E06 边界：数字单调，且（无 else 时）两端盖住 range
    conds = re.findall(r'\bif\s*\(([^)]*)\)|\belse\s+if\s*\(([^)]*)\)', src)
    nums = []
    for a, b in conds:
        c = a or b
        for op, val in re.findall(r'(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)', c):
            nums.append(float(val))
    if nums:
        uniq = [nums[0]]
        for v in nums[1:]:
            if v != uniq[-1]:
                uniq.append(v)
        asc = all(b > a for a, b in zip(uniq, uniq[1:]))
        desc = all(b < a for a, b in zip(uniq, uniq[1:]))
        if not (asc or desc):
            r.fail('E06 分支边界的数值不是单调的（' + ' → '.join(f'{v:g}' for v in uniq) + '）：多半有区间重叠或顺序写反')
        else:
            r.ok('E06 边界数值单调')
        has_else = re.search(r'\belse\s*\{', src) is not None
        lo, hi = rng
        if not has_else:
            if min(uniq) > lo + 0.001 or max(uniq) < hi - 0.001:
                r.fail(f'E06 末档没有 else 兜底，且边界没盖住 {lo:g}–{hi:g}（最小 {min(uniq):g} / 最大 {max(uniq):g}）')
            else:
                r.ok('E06 末端与两端覆盖完整')
        else:
            r.ok('E06 末档用 else 兜底（允许）')

    # E07 禁用能力
    hit = [b for b in BANNED if b in src]
    if hit:
        for h in hit:
            r.fail(f'E07 用了做不到的能力：{h}')
    else:
        r.ok('E07 无越界 API')

    # E08 占位符
    ph = [p for p in PLACEHOLDERS if p in src]
    if ph:
        for p in ph:
            r.fail(f'E08 正文里有构建期占位符 {p}')
    else:
        r.ok('E08 占位符 0 命中')

    return r


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2
    path = argv[1]
    if not os.path.exists(path):
        print(f'找不到：{path}')
        return 2

    book = None
    no_mvu = '--no-mvu' in argv
    rng = (0.0, 100.0)
    for i, a in enumerate(argv):
        if a == '--book' and i + 1 < len(argv):
            book = argv[i + 1]
        if a == '--range' and i + 1 < len(argv):
            try:
                lo, hi = argv[i + 1].split(',')
                rng = (float(lo), float(hi))
            except Exception:
                print('--range 要写成 0,100')
                return 2

    r = check(path, book, no_mvu, rng)
    name = os.path.basename(path)
    if r.fails:
        print(f'[FAIL] {name}')
        for m in r.fails:
            print('   - ' + m)
    for w in r.warns:
        print('   ! ' + w)
    if not r.fails:
        print(f'[  ok ] {name}  {len(r.oks)} 项通过' if not r.warns
              else f'[WARN] {name}  {len(r.oks)} 项通过，{len(r.warns)} 处提醒')
    total = len(r.oks) + len(r.fails) + len(r.warns)
    print(f'\n{total} 项：{len(r.fails)} 失败 / {len(r.warns)} 警告')
    return 0 if not r.fails else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""分档控制器（EJS）校验器：查语法纪律、变量路径、被控条目与边界连续性。

用法：
    python scripts/validate-ejs.py <控制器.ejs> [--book <世界书.json>] [--no-mvu] [--range 0,100]

--book      native 世界书（对象形状或数组形状都认）：查 getwi 的条目是否存在且已禁用
--no-mvu    没有 MVU 时用 initial. 前缀，getvar 路径降级检查
--range     轴的取值区间，E06 用它判"两端有没有盖住"，默认 0,100

退出码：0 全过；1 有 FAIL；2 用法错误。
需要 Node.js；随包编译器仅编译，不执行项目模板。
"""
import json
import operator
import os
import re
import sys
import subprocess
from pathlib import Path

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


def compile_controller(path, report):
    # 仅编译。不调用模板函数，不运行任何项目提供的 JavaScript。
    compiler = Path(__file__).parent / 'vendor' / 'ejs' / 'ejs.cjs'
    command = """const fs = require('node:fs');
const ejs = require(process.argv[1]);
try {
  ejs.compile(fs.readFileSync(process.argv[2], 'utf8'), {
    async: true, client: true, _with: true, localsName: 'locals', outputFunctionName: 'print'
  });
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}"""
    try:
        result = subprocess.run(['node', '-e', command, str(compiler.resolve()), str(path)],
                                capture_output=True, text=True, encoding='utf-8', timeout=15)
    except (OSError, subprocess.TimeoutExpired) as error:
        report.fail(f'E00 编译器未完成：{error}')
        return
    if result.returncode:
        report.fail('E00 EJS 编译失败：' + result.stderr.strip()[:700])
    else:
        report.ok('E00 通过 ST-Prompt-Template 同版 EJS 编译')


def check(path, book_p, no_mvu, rng):
    r = Report()
    src = read(path)

    compile_controller(path, r)

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
    first = next((body for tag, body in bs if tag in ('_', '')), '')
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

    # 只对能静态辨认的同一变量的单阈值 if/else if 链判断覆盖。
    # 逐个阈值及相邻区间取一点，保留 < 与 <= 的端点差异。
    ops = {'<': operator.lt, '<=': operator.le, '>': operator.gt, '>=': operator.ge}
    predicate = re.compile(r'^(?:}\s*)?(if|else\s+if)\s*\(\s*(\w+)\s*(>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)\s*\)\s*{\s*$')
    chain = []

    def check_chain(has_else):
        if not chain:
            return
        lo, hi = rng
        cuts = sorted({lo, hi, *(v for _, _, v in chain if lo <= v <= hi)})
        points = set(cuts) | {(a + b) / 2 for a, b in zip(cuts, cuts[1:])}
        remaining = points
        for name, op, cutoff in chain:
            matched = {x for x in remaining if ops[op](x, cutoff)}
            if not matched:
                r.fail(f'E06 分支 {name} {op} {cutoff:g} 在指定范围内不可达')
            remaining = remaining - matched
        if remaining and not has_else:
            r.fail(f'E06 分档未覆盖 {min(remaining):g}，且没有 else 兜底')
        chain.clear()

    for tag, body in bs:
        if tag not in ('_', ''):
            continue
        code = body.strip().removesuffix('_').strip()
        match = predicate.fullmatch(code)
        if match:
            keyword, name, op, value = match.groups()
            if keyword == 'if':
                chain.clear()  # 嵌套分支有自己的条件，不能当作上一档的边界
            elif not chain or chain[0][0] != name:
                chain.clear()
                continue
            chain.append((name, op, float(value)))
        elif re.fullmatch(r'}\s*else\s*{', code):
            check_chain(True)
        elif code == '}':
            check_chain(False)
        elif code:
            chain.clear()  # 嵌套或复合条件不由这个静态检查推断
    check_chain(False)

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
                if rng[0] > rng[1]:
                    raise ValueError("范围逆序")
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

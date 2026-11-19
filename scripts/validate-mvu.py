#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""变量系统（MVU）校验器：查投影出来的三个文件与两条正则，外加几个真会出事故的点。

用法：
    python scripts/validate-mvu.py <产物目录> [--contract <contract.yaml>] [--book <世界书.json>] [--no-regex]

目录里应有：变量结构.js、[initvar]变量初始化.yaml、变量规则.yaml、regex-mvu.json
可选：--book 传入 native 世界书，校验 [initvar] 条目是否禁用、uid 是否与键对齐。

退出码：0 全过；1 有 FAIL；2 用法错误 / 依赖缺失。
只依赖 PyYAML（节点可选：有 node 才做正则与语法实测）。
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    import yaml
except ImportError:
    print('需要 PyYAML：python -m pip install pyyaml')
    sys.exit(2)

PLACEHOLDERS = ('【AI补全·可替换】', '[待定', '【未知】')
VAR_LIST_EXACT = '{{format_message_variable::stat_data}}'
ENTRY_KEYS = ('constant', 'position', 'depth', 'order', 'exclude_recursion', 'prevent_recursion')


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


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def strip_js_comments(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    src = re.sub(r'(?m)^\s*//.*$', '', src)
    src = re.sub(r'\s//[^\n\'"]*$', '', src, flags=re.M)
    return src


def has_node():
    return shutil.which('node') is not None


def node_check(path):
    """把 ES module 拷成 .mjs 再 node --check。返回 (ok, message)。"""
    if not has_node():
        return None, '没装 node，跳过语法实测'
    tmpdir = tempfile.mkdtemp()
    try:
        dst = os.path.join(tmpdir, 'schema.mjs')
        shutil.copyfile(path, dst)
        p = subprocess.run([shutil.which('node'), '--check', dst],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        return p.returncode == 0, (p.stderr or '').strip()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def node_regex_ok(patterns):
    """把一串正则字符串交给 node 逐条 new RegExp。返回 list[bool] 或 None。"""
    if not has_node():
        return None
    tmpdir = tempfile.mkdtemp()
    try:
        data = os.path.join(tmpdir, 'p.json')
        with open(data, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False)
        runner = os.path.join(tmpdir, 'r.js')
        with open(runner, 'w', encoding='utf-8') as f:
            f.write("""
const fs = require('fs');
const pats = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = pats.map((p) => {
  try { new RegExp(p); return 'ok'; } catch (e) { return 'bad: ' + e.message; }
});
process.stdout.write(JSON.stringify(out));
""")
        p = subprocess.run([shutil.which('node'), runner, data],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        if p.returncode != 0:
            return None
        return json.loads(p.stdout)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def load_contract(path):
    d = yaml.safe_load(read(path)) or {}
    axes = ((d.get('naming') or {}).get('axes') or [])
    out = []
    for a in axes:
        if isinstance(a, dict) and a.get('name'):
            out.append(a)
        elif isinstance(a, str):
            out.append({'name': a})
    return out


def check(schema_p, init_p, entries_p, regex_p, axes, book_p, need_regex):
    r = Report()

    # M01 文件齐
    missing = [p for p in (schema_p, init_p, entries_p) if not p]
    if missing:
        r.fail(f'M01 缺文件：{", ".join(os.path.basename(m) for m in missing)}（变量结构.js / [initvar]yaml / 变量规则.yaml 三件必交）')
        return r
    r.ok('M01 三件齐')

    src = read(schema_p)
    code = strip_js_comments(src)

    # M02 注册骨架
    if 'registerMvuSchema' in code and re.search(r'\$\(\s*\(\s*\)\s*=>', code):
        r.ok('M02 有 registerMvuSchema 与 $(() =>')
    else:
        r.fail('M02 变量结构.js 缺 registerMvuSchema 或 $(() => …) 注册骨架')

    # M03 initvar 不许 $meta
    init_txt = read(init_p)
    init_code = re.sub(r'(?m)^\s*#.*$', '', init_txt)
    if '$meta' in init_code:
        r.fail('M03 [initvar] 里出现 $meta——结构应写在 zod 脚本里，$meta 是没有脚本时的退化路线')
    else:
        r.ok('M03 [initvar] 无 $meta')
    try:
        init = yaml.safe_load(init_code) or {}
    except Exception as e:
        r.fail(f'M03 [initvar] 不是合法 YAML：{e}')
        init = {}
    if isinstance(init, dict) and ('enabled' in init or 'disable' in init):
        r.warn('M03 [initvar] 文件里写着条目开关——条目配置放变量规则.yaml 或世界书，别混进值文件')

    # M04 轴与 clamp 上界
    if axes:
        bad = []
        for a in axes:
            name = a['name']
            rng = a.get('range') or []
            if name not in code:
                bad.append(f'{name} 没出现在 schema 里')
                continue
            if len(rng) == 2:
                hi = rng[1]
                pat = re.compile(re.escape(name) + r'[^\n]*?clamp\(\s*v\s*,\s*-?\d+\s*,\s*' + str(hi) + r'\s*\)')
                pat2 = re.compile(re.escape(name) + r'[^\n]*?刻度\(\s*\d+\s*,\s*' + str(hi) + r'\s*\)')
                if not (pat.search(code) or pat2.search(code)):
                    bad.append(f'{name} 的夹取上界不是 range 的 {hi}')
        if bad:
            for b in bad:
                r.fail('M04 ' + b)
        else:
            r.ok(f'M04 {len(axes)} 条轴的夹取上界与 range 一致')
    else:
        r.ok('M04 未传契约，跳过轴名与上界比对')

    # M05 不许 z.number()
    if re.search(r'\bz\.number\(', code):
        r.fail('M05 用了 z.number()——用 z.coerce.number().catch(初值) 接住字符串与脏值')
    else:
        r.ok('M05 没有裸 z.number()')

    # M06–M08 条目配置与内容
    try:
        ents = (yaml.safe_load(read(entries_p)) or {}).get('entries') or []
    except Exception as e:
        r.fail(f'M06 变量规则.yaml 解析失败：{e}')
        ents = []
    by_name = {}
    for e in ents:
        if isinstance(e, dict) and e.get('comment'):
            by_name[e['comment']] = e
    need = ['[mvu_update]变量更新规则', '变量列表', '[mvu_update]变量输出格式']
    miss = [n for n in need if n not in by_name]
    if miss:
        r.fail('M06 缺条目：' + '、'.join(miss))
    else:
        r.ok('M06 三条条目齐')
    for n, e in by_name.items():
        wrong = []
        if e.get('constant') is not True:
            wrong.append('constant 必须是 true')
        if e.get('position') != 4:
            wrong.append('position 必须是 4（atDepth）')
        if e.get('depth') != 0:
            wrong.append('depth 必须是 0')
        if e.get('order') != 200:
            wrong.append('order 必须是 200')
        if e.get('exclude_recursion') is not True or e.get('prevent_recursion') is not True:
            wrong.append('递归要双向 prevent')
        if wrong:
            r.fail(f'M06 「{n}」配置不对：' + '；'.join(wrong))

    vl = by_name.get('变量列表')
    if vl is not None:
        content = (vl.get('content') or '').strip()
        if content == VAR_LIST_EXACT:
            r.ok('M07 变量列表内容逐字符正确')
        else:
            r.fail(f'M07 变量列表内容必须是 {VAR_LIST_EXACT}（不加空格不换行），现在是 {content[:40]!r}')

    fmt = by_name.get('[mvu_update]变量输出格式')
    if fmt is not None:
        c = (fmt.get('content') or '')
        lack = [t for t in ('<UpdateVariable>', '<JSONPatch>', 'delta') if t not in c]
        if lack:
            r.fail('M08 输出格式缺：' + '、'.join(lack))
        else:
            r.ok('M08 输出格式含 UpdateVariable / JSONPatch / delta')

    # M09 占位符
    hits = []
    for p in (schema_p, init_p, entries_p):
        txt = read(p)
        for ph in PLACEHOLDERS:
            if ph in txt:
                hits.append(os.path.basename(p) + ' 含 ' + ph)
    if hits:
        for h in hits:
            r.fail('M09 ' + h + '（构建期占位符不许落进运行时）')
    else:
        r.ok('M09 占位符 0 命中')

    # M10 语法
    ok, msg = node_check(schema_p)
    if ok is None:
        r.warn('M10 ' + msg)
    elif ok:
        r.ok('M10 node --check 通过')
    else:
        first = (msg.splitlines() or [''])[0]
        r.fail('M10 变量结构.js 语法错误：' + first)

    # M11 世界书 uid 对齐
    if book_p:
        try:
            book = json.loads(read(book_p))
            entries = (book.get('entries') or {})
            if isinstance(entries, list):
                entries = {str(i): v for i, v in enumerate(entries)}
            bad = [k for k, v in entries.items()
                   if isinstance(v, dict) and 'uid' in v and str(v['uid']) != str(k)]
            if bad:
                r.fail(f'M11 世界书 uid 与键不一致（{bad[:3]}…）：ST 面板按 uid 取条目，错位会静默丢条目')
            else:
                r.ok(f'M11 {len(entries)} 条 uid 与键对齐')
            init_ents = [v for v in entries.values()
                         if isinstance(v, dict) and '[initvar]' in str(v.get('comment', '')).lower()]
            if init_ents:
                on = [v for v in init_ents
                      if v.get('enabled', True) is not False and v.get('disable', False) is not True]
                if on:
                    r.fail('M11 [initvar] 条目必须 enabled: false（只在开聊时读一次）')
                else:
                    r.ok('M11 [initvar] 条目已禁用')
            else:
                r.warn('M11 世界书里没有 comment 含 [initvar] 的条目——MVU 读不到初值')
        except Exception as e:
            r.fail(f'M11 世界书读不了：{e}')

    # M12 initvar 与 prefault 的差异（否则验不出是否读到）
    if isinstance(init, dict):
        flat = {}

        def walk(node, prefix=''):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, prefix + '/' + str(k))
            else:
                flat[prefix] = node
        walk(init)
        vals = [v for v in flat.values() if isinstance(v, (int, float))]
        same = 0
        compared = 0
        for a in axes:
            name = a['name']
            pref = None
            m = re.search(re.escape(name) + r'\s*:\s*[^\n]*?(?:刻度|prefault|catch)\(\s*(-?\d+)', code)
            if m:
                pref = int(m.group(1))
            have = [v for k, v in flat.items() if k.endswith('/' + name)]
            if pref is None or not have:
                continue
            compared += 1
            if all(float(h) == float(pref) for h in have):
                same += 1
        if compared and same == compared:
            r.warn('M12 initvar 的值与 schema prefault 全都相同——找一个轴改成不同值，否则验不出 initvar 读没读到')
        elif compared:
            r.ok(f'M12 {compared} 条轴里 {compared - same} 条的 initvar 与 prefault 不同（能验出读取）')

    # M13 正则
    if not need_regex:
        r.ok('M13 跳过正则检查（--no-regex）')
    elif not regex_p:
        r.fail('M13 缺 regex-mvu.json：没有它，模型下一轮会看到上次的补丁、玩家会看到 JSONPatch 原文')
    else:
        try:
            regs = json.loads(read(regex_p))
        except Exception as e:
            r.fail(f'M13 regex-mvu.json 解析失败：{e}')
            regs = []
        if isinstance(regs, dict):
            regs = [regs]
        pots = [x for x in regs if x.get('promptOnly') and not x.get('markdownOnly')]
        mds = [x for x in regs if x.get('markdownOnly') and not x.get('promptOnly')]
        if not pots:
            r.fail('M13 缺 promptOnly 那条（否则模型下一轮会看到自己的补丁）')
        if not mds:
            r.fail('M13 缺 markdownOnly 那条（否则玩家会看到 JSONPatch 原文）')
        ph = [x for x in regs if '<StatusPlaceHolderImpl' in str(x.get('findRegex', '')).replace('\\', '')]
        if not ph:
            r.warn('M13 没有隐藏 <StatusPlaceHolderImpl/> 的规则——做了状态栏才需要，没做就别留这条')
        pats = []
        for x in regs:
            fr = x.get('findRegex') or ''
            m = re.match(r'^/(.*)/([a-z]*)$', fr, re.S)
            pats.append(m.group(1) if m else fr)
        res = node_regex_ok(pats)
        if res is None:
            r.warn('M13 没装 node，跳过正则编译实测')
        else:
            bad = [(i, s) for i, s in enumerate(res) if s != 'ok']
            if bad:
                for i, s in bad:
                    r.fail(f'M13 第 {i + 1} 条正则编译失败：{s}')
            else:
                r.ok(f'M13 {len(pats)} 条正则都能编译')

    return r


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2

    target = argv[1]
    contract = None
    book = None
    need_regex = '--no-regex' not in argv
    for i, a in enumerate(argv):
        if a == '--contract' and i + 1 < len(argv):
            contract = argv[i + 1]
        if a == '--book' and i + 1 < len(argv):
            book = argv[i + 1]

    if not os.path.isdir(target):
        print(f'不是目录：{target}')
        return 2

    def pick(*patterns):
        for pat in patterns:
            hits = sorted(glob.glob(os.path.join(target, pat)))
            if hits:
                return hits[0]
        return None

    schema_p = pick('变量结构.js', '*schema*.js')
    init_p = pick('[[]initvar[]]*.yaml', '*initvar*.yaml', '*变量初始化*.yaml')
    entries_p = pick('变量规则.yaml', '*entries*.yaml', '*变量规则*.yaml')
    regex_p = pick('regex-mvu.json', 'regex*.json') if need_regex else None

    axes = load_contract(contract) if contract else []
    if contract and not os.path.exists(contract):
        print(f'找不到契约：{contract}')
        return 2

    r = check(schema_p, init_p, entries_p, regex_p, axes, book, need_regex)

    if r.fails:
        print('[FAIL] ' + target)
        for m in r.fails:
            print('   - ' + m)
    for w in r.warns:
        print('   ! ' + w)
    if not r.fails and not r.warns:
        print(f'[  ok ] {target}  {len(r.oks)} 项通过')
    elif not r.fails:
        print(f'[WARN] {target}  {len(r.oks)} 项通过，{len(r.warns)} 处提醒')
    total = len(r.oks) + len(r.fails) + len(r.warns)
    print(f'\n{total} 项：{len(r.fails)} 失败 / {len(r.warns)} 警告')
    return 0 if not r.fails else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

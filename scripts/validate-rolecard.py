#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""角色卡校验器：抄 templates/rolecard.yaml 的骨架检查，外加本包的几条规矩。

用法：
    python scripts/validate-rolecard.py <卡.yaml> [更多卡.yaml …]
    python scripts/validate-rolecard.py <目录>            # 目录下所有 *.yaml

退出码：0 全过；1 有 FAIL；2 用法错误 / 依赖缺失。
只依赖 PyYAML。W 是警告，可以带着走，但要知道自己在忽略什么。
"""
import sys
import os
import glob

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    import yaml
except ImportError:
    print('需要 PyYAML：python -m pip install pyyaml')
    sys.exit(2)

PLACEHOLDERS = ('【AI补全·可替换】', '[待定', '【未知】', '[推断：')
BASE_BLOCKS = ('name', 'identity', 'psychology', 'behavior', 'attitudes',
               'speech', 'background', 'anti_ooc')
NSFW_KEYS = ('sexual_orientation', 'standing', 'fetish', 'preference',
             'sex_organs', 'sensitive_areas', 'contrast')
ATTITUDE_KEYS = ('close_ones', 'strangers', 'enemies', 'authority')
SPEECH_RULE_KINDS = ('under_pressure', 'when_close', 'when_angry', 'when_lying',
                     'casual', 'conflict', 'formal', 'praise')


class Report:
    def __init__(self, path):
        self.path = path
        self.fails = []
        self.warns = []
        self.oks = []

    def fail(self, msg):
        self.fails.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def ok(self, msg):
        self.oks.append(msg)


def strings(obj):
    """把任意嵌套结构里的字符串摊平。"""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from strings(v)


def check_file(path, nsfw_required=False):
    r = Report(path)
    try:
        doc = yaml.safe_load(open(path, encoding='utf-8'))
    except Exception as e:
        r.fail(f'YAML 解析失败：{e}')
        return r

    if not isinstance(doc, dict) or 'character' not in doc:
        r.fail('顶层必须是 {character: {...}}')
        return r
    c = doc['character']
    if not isinstance(c, dict):
        r.fail('character 必须是对象')
        return r

    # 1 块：精简档四个必需，其余缺失只警告
    CORE_BLOCKS = ('psychology', 'behavior', 'speech', 'anti_ooc')
    core_miss = [k for k in CORE_BLOCKS if k not in c]
    if core_miss:
        r.fail('缺核心块：' + '、'.join(core_miss))
    optional_miss = [k for k in BASE_BLOCKS if k not in c and k not in CORE_BLOCKS]
    if optional_miss:
        r.warn('缺标准档字段：' + '、'.join(optional_miss) + '（精简档可以没有；标准/扩展档必须有）')
    if not core_miss and not optional_miss:
        r.ok('基础块齐全（8 块 + name）')

    # 2 name
    if not str(c.get('name') or '').strip():
        r.fail('name 为空')

    # 3 psychology
    psy = c.get('psychology') or {}
    if isinstance(psy, dict):
        ranks = psy.get('values', {}).get('ranking') if isinstance(psy.get('values'), dict) else None
        if isinstance(ranks, str):
            n = len([x for x in ranks.replace('>', '＞').split('＞') if x.strip()])
            if n < 3:
                r.fail(f'values.ranking 只有 {n} 项，至少 3 项')
        elif isinstance(ranks, list) and len(ranks) < 3:
            r.fail(f'values.ranking 只有 {len(ranks)} 项，至少 3 项')
        else:
            r.warn('values.ranking 缺失或不是字符串/列表')
        for k in ('motivations', 'fears', 'taboos'):
            if not psy.get(k):
                r.fail(f'psychology.{k} 为空')

    # 4 behavior
    beh = c.get('behavior') or {}
    rules = beh.get('rules') or []
    if not isinstance(rules, list) or len(rules) < 4:
        r.fail(f'behavior.rules 只有 {len(rules) if isinstance(rules, list) else 0} 条，至少 4 条')
    else:
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                r.fail(f'behavior.rules[{i}] 不是对象')
                continue
            for k in ('trigger', 'action'):
                if not rule.get(k):
                    r.fail(f'behavior.rules[{i}] 缺 {k}')
            if not any(rule.get(k) for k in ('condition', 'reason', 'cost')):
                r.warn(f'behavior.rules[{i}] 没有 condition / reason / cost')
        r.ok(f'behavior.rules {len(rules)} 条')
    v = beh.get('stress_response') or []
    if not isinstance(v, list) or len(v) < 3:
        r.fail('behavior.stress_response 少于 3 项')
    v = beh.get('quirks') or []
    if not isinstance(v, list) or len(v) < 3:
        r.warn('behavior.quirks 少于 3 项（标准档要求 ≥3）')
    if not beh.get('cooperation'):
        r.warn('behavior.cooperation 缺失')

    # 5 attitudes 四类各 ≥2
    att = c.get('attitudes') or {}
    if not isinstance(att, dict) or not att:
        r.warn('没有 attitudes 块（精简档可以没有；标准档必须有四类各 ≥2 项）')
    else:
        for k in ATTITUDE_KEYS:
            blk = att.get(k) if isinstance(att, dict) else None
            if not isinstance(blk, dict):
                r.fail(f'attitudes.{k} 缺失')
                continue
            filled = [x for x in blk.values() if str(x or '').strip()]
            if len(filled) < 2:
                r.fail(f'attitudes.{k} 只有 {len(filled)} 项有内容，至少 2 项')

    # 6 speech
    sp = c.get('speech') or {}
    if not isinstance(sp, dict):
        r.fail('speech 缺失')
    else:
        style = sp.get('style') or {}
        if not isinstance(style, dict) or len([v for v in style.values() if str(v or '').strip()]) < 2:
            r.fail('speech.style 至少要有 2 个子键有内容（tone / structure / vocabulary）')
        srules = sp.get('rules') or []
        if not isinstance(srules, list) or len(srules) < 3:
            r.fail('speech.rules 少于 3 条')
        v = sp.get('quotes') or []
        if not isinstance(v, list) or len(v) < 3:
            r.fail('speech.quotes 少于 3 条')
        v = sp.get('catchphrases') or []
        if not isinstance(v, list) or len(v) < 3:
            r.warn('speech.catchphrases 少于 3 条（标准档要求 ≥3）')

    # 7 taboos ⊆ anti_ooc.never（语义包含：任一侧包含即算对应）
    never = (c.get('anti_ooc') or {}).get('never') or []
    taboos = psy.get('taboos') or []
    if isinstance(never, list) and isinstance(taboos, list) and taboos:
        for tb in taboos:
            tb_s = str(tb)
            hit = any(tb_s in str(n) or str(n) in tb_s for n in never if str(n).strip())
            if not hit:
                r.fail(f'taboos 里「{tb_s[:24]}」在 anti_ooc.never 里找不到对应')

    # 8 nsfw：块与契约开关的一致性由调用方的 --nsfw 决定；这里只查形状
    nsfw = c.get('nsfw')
    if nsfw is None:
        if nsfw_required:
            r.fail('契约 nsfw: true，但卡里没有 nsfw 块——回生成步补，不是跳过')
        else:
            r.warn('没有 nsfw 块——契约 nsfw: false 时正常')
    elif isinstance(nsfw, dict):
        miss = [k for k in NSFW_KEYS if k not in nsfw]
        if miss:
            r.fail('nsfw 缺键：' + '、'.join(miss))
        else:
            r.ok('nsfw 七键齐全')
    else:
        r.fail('nsfw 不是对象')

    # 9 占位符
    hits = []
    for s in strings(c):
        for ph in PLACEHOLDERS:
            if ph in s:
                hits.append((ph, s[:60]))
                break
    if hits:
        r.fail(f'正文里有构建期占位符 {len(hits)} 处，例如：{hits[0][1]}')
    else:
        r.ok('正文无占位符')

    # 10 自创顶层键（只警告）
    allowed = set(BASE_BLOCKS) | {'nsfw', 'lore', 'relationships', 'growth_arc'}
    extra = [k for k in c if k not in allowed]
    if extra:
        r.warn('模板外的顶层键：' + '、'.join(extra) + '（须已在 decisions 记过）')

    return r


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    nsfw_required = '--nsfw' in argv
    argv = [a for a in argv if a != '--nsfw']

    paths = []
    for a in argv[1:]:
        if os.path.isdir(a):
            paths.extend(sorted(glob.glob(os.path.join(a, '*.yaml'))))
        elif os.path.exists(a):
            paths.append(a)
        else:
            print(f'找不到：{a}')
            return 2
    if not paths:
        print('没有可校验的文件')
        return 2

    total_f = 0
    for p in paths:
        r = check_file(p, nsfw_required)
        name = os.path.basename(p)
        if r.fails:
            print(f'\n[FAIL] {name}')
            for m in r.fails:
                print('   - ' + m)
        elif r.warns:
            print(f'\n[WARN] {name}')
            for m in r.warns:
                print('   ! ' + m)
        else:
            print(f'[  ok ] {name}  {len(r.oks)} 项通过')
        total_f += len(r.fails)

    print(f'\n共 {len(paths)} 张卡：{total_f} 处失败')
    return 0 if total_f == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))

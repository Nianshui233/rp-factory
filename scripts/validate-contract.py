#!/usr/bin/env python3
"""校验 contract.yaml：阶段状态、产物索引、交付路线、命名表是否自洽。

用法：
    python scripts/validate-contract.py <创作痕迹/contract.yaml>
    python scripts/validate-contract.py <项目根目录>

退出码：0 全部通过（可能有警告）／1 有失败／2 用法错误。

为什么需要它：契约是唯一索引，一旦它和产物对不上，后续每个阶段都建立在错的前提上。
一次实操里出现过 stages.1 停在 partial 未收口、artifacts[].type 写了枚举外的
`role-cards` / `secret-layer`、scene-sheet 的 path 写成一个目录——机器不报错，人也不会看。
"""
import sys
import pathlib

sys.stdout.reconfigure(encoding='utf-8')

try:
    import yaml
except ImportError:
    print('需要 PyYAML：python -m pip install pyyaml')
    sys.exit(2)

STAGES = [1, 2, 3, 4, 5, 6, 7]
STAGE_STATES = {'none', 'partial', 'done', 'skipped'}
ROUTES = {'native', 'st', 'both'}
HARD_SOURCES = {'用户确认', '推导'}

# 阶段 → 该阶段至少产出的 type（任一即可）
STAGE_ARTIFACT = {
    1: {'world-bible'},
    2: {'rolecard'},
    3: {'scene-sheet'},
    4: {'axis-system'},
    5: {'opening-ui'},
    6: {'statusbar-ui'},
    7: {'st-card'},
}

ARTIFACT_TYPES = {
    'project-profile', 'world-bible', 'rolecard', 'scene-sheet', 'axis-system',
    'opening-ui', 'statusbar-ui', 'st-card', 'st-worldbook',
}
# 历史漂移里出现过的错名，直接点出来，比「不在枚举内」更好用
LEGACY_ALIASES = {
    'role-cards': 'rolecard（多张卡时用 path 指向目录，type 仍是 rolecard）',
    'character-cards': 'rolecard',
    'secret-layer': '不属于任何阶段产物；秘密写进 world-bible 的 `信息分层`',
    'world': 'world-bible',
    'scene': 'scene-sheet',
    'axis': 'axis-system',
    'st': 'st-card',
}

NAME_LISTS = ('factions', 'places', 'systems', 'axes')

fails, warns = [], []


def fail(rule, msg):
    fails.append((rule, msg))


def warn(rule, msg):
    warns.append((rule, msg))


def as_dict(v):
    return v if isinstance(v, dict) else {}


def load(path: pathlib.Path):
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except Exception as e:  # noqa: BLE001
        print(f'[ FAIL ] C00  无法解析 {path}: {e}')
        sys.exit(1)


def check_project(c, root):
    p = as_dict(c.get('project'))
    if not p:
        fail('C01', '缺 `project` 段')
        return
    for k in ('name', 'workspace', 'mode', 'rp_form', 'language'):
        if not p.get(k):
            warn('C01', f'`project.{k}` 为空')
    if p.get('mode') not in (None, 'text', 'engineering'):
        fail('C01', f'`project.mode` 只能是 text / engineering，实际 {p.get("mode")!r}')
    ws = p.get('workspace') or ''
    if ws and not (ws.startswith('/') or (len(ws) > 2 and ws[1] == ':')):
        warn('C02', f'`project.workspace` 应是绝对路径，实际 {ws!r}')
    name = p.get('name') or ''
    if name and name != '未命名项目' and ws:
        proj = pathlib.Path(ws) / name
        if not proj.exists():
            warn('C02', f'`<workspace>/<name>` 不存在：{proj}')
        elif proj.resolve() != root:
            warn('C02', f'契约所在目录 {root} 与 `<workspace>/<name>` = {proj} 不一致')
    sr = p.get('stages_requested')
    if sr is not None:
        if not isinstance(sr, list):
            fail('C03', '`project.stages_requested` 必须是列表')
        else:
            bad = [x for x in sr if x not in STAGES]
            if bad:
                fail('C03', f'`project.stages_requested` 含非法阶段：{bad}')
    if 'web_research' in p and not isinstance(p['web_research'], bool):
        fail('C03', '`project.web_research` 必须是布尔值')


def check_stages(c):
    s = as_dict(c.get('stages'))
    if not s:
        fail('C04', '缺 `stages` 段')
        return
    for k in s:
        if k not in STAGES:
            fail('C04', f'`stages` 出现非法键 {k!r}（只能是 1–7）')
    for n in STAGES:
        v = s.get(n)
        if v is None:
            fail('C04', f'`stages.{n}` 缺失（没跑就写 none / skipped）')
        elif v not in STAGE_STATES:
            fail('C04', f'`stages.{n}` = {v!r}，只能是 {" / ".join(sorted(STAGE_STATES))}')
    if s.get(1) == 'skipped' and any(s.get(n) not in (None, 'none', 'skipped') for n in (2, 3, 4)):
        warn('C04', '`stages.1` 是 skipped，但后续阶段已推进；世界观缺位时下游只能靠推断')


def check_artifacts(c, root):
    arts = c.get('artifacts')
    if arts is None:
        fail('C05', '缺 `artifacts` 段（没有产物就写 `artifacts: []`）')
        return set()
    if not isinstance(arts, list):
        fail('C05', '`artifacts` 必须是列表')
        return set()
    seen_paths = {}
    types = set()
    for i, a in enumerate(arts, 1):
        a = as_dict(a)
        t = a.get('type')
        path = a.get('path') or ''
        if not t:
            fail('C05', f'artifacts 第 {i} 条缺 `type`')
            continue
        if t in LEGACY_ALIASES:
            fail('C06', f'artifacts 第 {i} 条 type = {t!r}；应为 {LEGACY_ALIASES[t]}')
        elif t not in ARTIFACT_TYPES:
            fail('C06', f'artifacts 第 {i} 条 type = {t!r} 不在枚举内：{" / ".join(sorted(ARTIFACT_TYPES))}')
        types.add(t)
        if not path:
            if not a.get('inline_ref'):
                warn('C07', f'artifacts 第 {i} 条（{t}）path 与 inline_ref 都空')
            continue
        if path.startswith('/') or (len(path) > 2 and path[1] == ':'):
            fail('C07', f'artifacts 第 {i} 条 path 是绝对路径：{path}（要写相对项目根）')
            continue
        if '..' in pathlib.PurePath(path).parts:
            fail('C07', f'artifacts 第 {i} 条 path 含 `..`：{path}')
            continue
        if path in seen_paths:
            fail('C07', f'artifacts 里 {path} 出现两次（第 {seen_paths[path]} 条与第 {i} 条）')
        seen_paths[path] = i
        target = root / path
        if not target.exists():
            fail('C08', f'artifacts 第 {i} 条 path 不存在：{path}')
        elif target.is_dir() and t not in ('rolecard', 'scene-sheet'):
            warn('C08', f'artifacts 第 {i} 条（{t}）path 指向目录：{path}')
    return types


def check_stage_artifacts(c, types):
    s = as_dict(c.get('stages'))
    for n in STAGES:
        if s.get(n) != 'done':
            continue
        need = STAGE_ARTIFACT[n]
        if not (types & need):
            fail('C09', f'`stages.{n}: done` 但 artifacts 里没有 {" 或 ".join(sorted(need))}')


def check_delivery(c):
    d = as_dict(c.get('delivery'))
    s = as_dict(c.get('stages'))
    if not d:
        if s.get(7) == 'done':
            fail('C10', '`stages.7: done` 但缺 `delivery` 段')
        return
    route = d.get('route')
    if route not in ROUTES:
        fail('C10', f'`delivery.route` = {route!r}，只能是 native / st / both')
        return
    if route in ('st', 'both'):
        if not d.get('st_name'):
            warn('C10', '`delivery.route` 含 st，但 `st_name` 为空（默认取 `project.name`）')
        files = d.get('files')
        if not isinstance(files, list) or not files:
            fail('C10', '`delivery.route` 含 st，但 `files` 不是非空列表')
        else:
            for f in files:
                if not isinstance(f, str) or f.startswith('/') or '..' in pathlib.PurePath(f).parts:
                    fail('C10', f'`delivery.files` 里 {f!r} 必须是相对 `最终产物/st/` 的文件名')
        if d.get('st_name') and c.get('naming', {}).get('world'):
            expect = f'{d["st_name"]} 世界书'
            if d.get('worldbook_name') and d['worldbook_name'] != expect:
                warn('C10', f'`delivery.worldbook_name` = {d["worldbook_name"]!r}，默认应为 {expect!r}')


def check_naming(c):
    nm = c.get('naming')
    if nm is None:
        return
    nm = as_dict(nm)
    if not nm.get('world'):
        warn('C11', '`naming.world` 为空')
    for key in NAME_LISTS:
        v = nm.get(key)
        if v is None:
            continue
        if not isinstance(v, list):
            fail('C11', f'`naming.{key}` 必须是列表')
            continue
        for item in v:
            if isinstance(item, str):
                continue
            item = as_dict(item)
            if not (item.get('name') or item.get('id')):
                fail('C11', f'`naming.{key}` 有条目既无 name 也无 id：{item}')
    axes = nm.get('axes') or []
    for item in axes:
        if isinstance(item, dict) and item.get('provisional') and as_dict(c.get('stages')).get(4) == 'done':
            fail('C11', f'`naming.axes` 里 {item.get("name")!r} 仍带 `provisional: true`，阶段 4 完成时应已接管')


def check_lists(c):
    # decisions 允许两种形状：阶段决策 {stage, question, answer} 与过程决策 {item, choice}
    shapes = {
        'hard_settings': [('id', 'text', 'source')],
        'pending': [('stage', 'item')],
        'decisions': [('stage', 'question', 'answer'), ('item', 'choice')],
    }
    for key, options in shapes.items():
        v = c.get(key)
        if v is None:
            continue
        if not isinstance(v, list):
            fail('C12', f'`{key}` 必须是列表')
            continue
        for i, item in enumerate(v, 1):
            item = as_dict(item)
            if key == 'decisions':
                def present(f):
                    return f in item and item[f] not in (None, '')
                if not any(all(present(f) for f in need) for need in options):
                    fail('C12', f'`decisions` 第 {i} 条既不是 {{stage,question,answer}} 也不是 {{item,choice}}')
                continue
            for f in options[0]:
                if not item.get(f):
                    fail('C12', f'`{key}` 第 {i} 条缺 `{f}`')
            if key == 'hard_settings' and item.get('source'):
                head = str(item['source']).split('（')[0].strip()
                if head not in HARD_SOURCES:
                    fail('C12', f'`hard_settings` 第 {i} 条 source = {item["source"]!r}，必须以 用户确认 / 推导 开头')
            if key == 'pending' and item.get('stage') is not None and item['stage'] not in STAGES:
                fail('C12', f'`pending` 第 {i} 条 stage = {item["stage"]!r} 非法')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    arg = pathlib.Path(sys.argv[1])
    if arg.is_dir():
        path = next((arg / '创作痕迹' / 'contract.yaml', arg / 'contract.yaml'), None)
        if not path or not path.exists():
            path = arg / '创作痕迹' / 'contract.yaml'
        root = arg
    else:
        path, root = arg, arg.parent.parent
    if not path.exists():
        print(f'找不到契约：{path}')
        return 2
    c = load(path)
    print(f'契约：{path}')
    print('-' * 52)

    check_project(c, root)
    check_stages(c)
    types = check_artifacts(c, root)
    check_stage_artifacts(c, types)
    check_delivery(c)
    check_naming(c)
    check_lists(c)

    rules = {
        'C00': '契约可解析',
        'C01': 'project 必填项',
        'C02': 'workspace / name 指向真实目录',
        'C03': 'stages_requested 与 web_research 类型',
        'C04': 'stages 键为 1–7、值在枚举内',
        'C05': 'artifacts 是列表且 type 非空',
        'C06': 'artifact type 在八类枚举内',
        'C07': 'path 相对、无 ..、不重复',
        'C08': 'path 指向真实存在的产物',
        'C09': 'done 的阶段有对应产物',
        'C10': 'delivery 路线与文件自洽',
        'C11': 'naming 表与 provisional 收口',
        'C12': 'hard_settings / pending / decisions 形状',
    }
    bad = {r for r, _ in fails}
    for r, name in rules.items():
        if r in bad:
            for _, msg in [x for x in fails if x[0] == r]:
                print(f'[ FAIL ] {r}  {msg}')
        else:
            print(f'[  ok  ] {r}  {name}')
    for r, msg in warns:
        print(f'[ warn ] {r}  {msg}')
    print('-' * 52)
    print(f'共 {len(rules)} 项：{len(fails)} 失败，{len(warns)} 警告')
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())

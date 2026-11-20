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

# 阶段用名字键（顺序即执行顺序）；旧的数字键仍认，但会提醒改
STAGE_ORDER = ['world', 'cast', 'scenes', 'axes', 'mvu', 'ejs', 'opening', 'statusbar', 'delivery']
# 旧数字键是"七阶段时代"的编号：5/6 是 opening/statusbar。新写法一律用名字，
# 免得 5 在旧契约里指 opening、在新枚举里指 mvu 这种静默错位。
STAGE_NUM = {1: 'world', 2: 'cast', 3: 'scenes', 4: 'axes',
             5: 'opening', 6: 'statusbar', 7: 'delivery'}
STAGES = STAGE_ORDER
STAGE_STATES = {'none', 'partial', 'done', 'skipped'}
# decisions[].state：确认 / 我提的 / 还悬着 / 被否掉（见 references/decisions.md）
DECISION_STATES = {'confirmed', 'proposed', 'pending', 'rejected'}
UNANSWERED_MARKERS = ('没回答', '没有回答', '未回答', '未答', '没答', '未确认', '没确认', '用户未定')
ROUTES = {'native', 'st', 'both'}
HARD_SOURCES = {'用户确认', '推导'}

# 阶段 → 该阶段至少产出的 type（任一即可）
STAGE_ARTIFACT = {
    'world': {'world-bible'},
    'cast': {'rolecard'},
    'scenes': {'scene-sheet'},
    'axes': {'axis-system'},
    'mvu': {'mvu-schema', 'mvu-initvar', 'mvu-entries'},
    'ejs': {'ejs-controller'},
    'opening': {'opening-ui'},
    'statusbar': {'statusbar-ui'},
    'delivery': {'st-card', 'st-regex', 'st-worldbook'},
}

ARTIFACT_TYPES = {
    'project-profile', 'world-bible', 'rolecard', 'scene-sheet', 'axis-system',
    'mvu-schema', 'mvu-initvar', 'mvu-entries', 'mvu-regex', 'ejs-controller',
    'opening-ui', 'statusbar-ui', 'st-card', 'st-regex', 'st-worldbook',
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
    'regex': 'st-regex',
    'worldbook': 'st-worldbook',
    'schema': 'mvu-schema',
    'initvar': 'mvu-initvar',
    'controller': 'ejs-controller',
}

NAME_LISTS = ('factions', 'places', 'systems', 'axes')

fails, warns = [], []


def fail(rule, msg):
    if (rule, msg) not in fails:
        fails.append((rule, msg))


def warn(rule, msg):
    if (rule, msg) not in warns:
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
            for x in sr:
                key = STAGE_NUM.get(x, x)
                if key not in STAGES:
                    fail('C03', f'`project.stages_requested` 含非法阶段：{x!r}')
            if any(isinstance(x, int) for x in sr):
                warn('C03', '`project.stages_requested` 用了数字，改成阶段名（world / cast / … / delivery）')
    if 'web_research' in p and not isinstance(p['web_research'], bool):
        fail('C03', '`project.web_research` 必须是布尔值')


def stage_map(raw):
    """把 stages 段归一到名字键；旧的数字键仍认，给一条提醒。"""
    out = {}
    numeric = False
    for k, v in as_dict(raw).items():
        if isinstance(k, int) or (isinstance(k, str) and k.isdigit()):
            numeric = True
        key = STAGE_NUM.get(k, k)
        if key not in STAGES:
            fail('C04', f'`stages` 出现非法键 {k!r}（只能是 {" / ".join(STAGE_ORDER)}）')
            continue
        out[key] = v
    if numeric:
        warn('C04', '`stages` 还在用数字键（按旧的七阶段编号解释），改成阶段名：world / cast / scenes / axes / mvu / ejs / opening / statusbar / delivery')
    return out


def check_stages(c):
    raw = c.get('stages')
    if not raw:
        fail('C04', '缺 `stages` 段')
        return
    s = stage_map(raw)
    for n in STAGES:
        v = s.get(n)
        if v is None and n in ("mvu", "ejs") and s:
            # 这两段是后加的，旧契约里没有很正常：提醒补，不判失败
            warn("C04", f"`stages.{n}` 缺失（旧契约）：补上 `{n}: none` 或 `skipped`")
            continue
        if v is None:
            fail('C04', f'`stages.{n}` 缺失（没跑就写 none / skipped）')
        elif v not in STAGE_STATES:
            fail('C04', f'`stages.{n}` = {v!r}，只能是 {" / ".join(sorted(STAGE_STATES))}')
    if s.get('world') == 'skipped' and any(s.get(n) not in (None, 'none', 'skipped') for n in ('cast', 'scenes', 'axes')):
        warn('C04', '`stages.world` 是 skipped，但后续阶段已推进；世界观缺位时下游只能靠推断')

    # C14：partial 必须挂 pending——否则「先放着」会变成没人回头
    pending_stages = set()
    for item in (c.get('pending') or []):
        item = as_dict(item)
        if item.get('stage') is not None:
            pending_stages.add(STAGE_NUM.get(item['stage'], item['stage']))
    for n in STAGES:
        if s.get(n) == 'partial' and n not in pending_stages:
            fail('C14', f'`stages.{n}` = partial，但 `pending` 里没有这一阶段缺什么：'
                        f'补一条 {{stage: {n}, item: <缺什么>}}，否则后面会建在没收口的块上')


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
    s = stage_map(c.get('stages'))
    for n in STAGES:
        if s.get(n) != 'done':
            continue
        need = STAGE_ARTIFACT[n]
        if not (types & need):
            fail('C09', f'`stages.{n}: done` 但 artifacts 里没有 {" 或 ".join(sorted(need))}')


def check_delivery(c):
    d = as_dict(c.get('delivery'))
    s = stage_map(c.get('stages'))
    if not d:
        if s.get('delivery') == 'done':
            fail('C10', '`stages.delivery: done` 但缺 `delivery` 段')
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
                    fail('C10', f'`delivery.files` 里 {f!r} 必须是相对 `最终产物/` 的文件名')
        if d.get('st_name') and c.get('naming', {}).get('world'):
            expect = f'{d["st_name"]} 世界书'
            if d.get('worldbook_name') and d['worldbook_name'] != expect:
                warn('C10', f'`delivery.worldbook_name` = {d["worldbook_name"]!r}，默认应为 {expect!r}')


def check_output_dirs(c, root):
    """最终产物/ 是交付目录：交付前必须空着（C15）。"""
    s = stage_map(c.get('stages'))
    d = as_dict(c.get('delivery'))
    route = d.get('route') if d else None
    delivered = s.get('delivery') == 'done'
    out = root / '最终产物'
    items = sorted(p.name for p in out.iterdir()) if out.is_dir() else []
    if not delivered:
        if items:
            fail('C15', f'`stages.delivery` 还没 done，但 `最终产物/` 已有 {len(items)} 项：{", ".join(items[:5])}（过程产物应放 创作痕迹/产物/）')
        return
    if not route:
        fail('C15', '`stages.delivery: done` 但 `delivery.route` 为空')
        return
    if not items:
        fail('C15', '`stages.delivery: done` 但 `最终产物/` 是空的')
        return
    if route in ('st', 'both'):
        want = {'正则.json'}
        names = set(items)
        if not any(n.endswith('世界书.json') for n in names):
            fail('C15', '酒馆路线缺 `<世界名> 世界书.json`')
        missing = want - names
        if missing:
            fail('C15', f'酒馆路线缺 {", ".join(sorted(missing))}')


def check_player_agency(c):
    """C16：演出许可自洽。缺省 = player-controlled（老契约不受影响）。"""
    if 'player_agency' not in c:
        return
    pa = c.get('player_agency')
    if not isinstance(pa, dict):
        fail('C16', '`player_agency` 必须是映射（mode / allowed / excluded / scope / duration / source）')
        return
    mode = pa.get('mode')
    if mode not in (None, 'player-controlled', 'limited', 'delegated'):
        fail('C16', f'`player_agency.mode` 只能是 player-controlled / limited / delegated，实际 {mode!r}')
        return
    mode = mode or 'player-controlled'
    allowed = pa.get('allowed') or []
    if not isinstance(allowed, list):
        fail('C16', '`player_agency.allowed` 必须是列表')
        allowed = []
    duration = str(pa.get('duration') or '').strip()
    if mode in ('limited', 'delegated') and not allowed:
        fail('C16', f'`player_agency.mode` = {mode}，但 `allowed` 是空的：'
                    f'放宽许可必须写清允许写的那几处，否则等于默认可代演')
    if mode == 'delegated' and not duration:
        fail('C16', '`player_agency.mode` = delegated，但没写 `duration`：'
                    '代跑只对某一段生效，不写时长就变成了整局代玩')
    if mode != 'player-controlled' and not str(pa.get('source') or '').startswith('用户确认'):
        fail('C16', f'`player_agency.mode` = {mode}，但 `source` = {pa.get("source")!r}：'
                    '放宽许可是用户定的，不许自己调（写 source: 用户确认）')


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
                state = item.get('state')
                if state is None:
                    continue
                if state not in DECISION_STATES:
                    fail('C13', f'`decisions` 第 {i} 条 state = {state!r}，只能是 '
                                f'{" / ".join(sorted(DECISION_STATES))}')
                    continue
                if state == 'proposed' and not (present('why') or present('because')):
                    fail('C13', f'`decisions` 第 {i} 条是 proposed：写清 `why`——'
                                f'是替用户拍的还是还欠一句确认，两者后面的动作不同')
                if state == 'confirmed':
                    blob = ' '.join(str(item.get(f, '')) for f in ('answer', 'choice', 'because', 'why'))
                    if any(m in blob for m in UNANSWERED_MARKERS):
                        fail('C13', f'`decisions` 第 {i} 条写着「没回答」却是 confirmed：'
                                    f'未答不是委托，该记 proposed 或 pending')
                continue
            for f in options[0]:
                if not item.get(f):
                    fail('C12', f'`{key}` 第 {i} 条缺 `{f}`')
            if key == 'hard_settings' and item.get('source'):
                head = str(item['source']).split('（')[0].strip()
                if head not in HARD_SOURCES:
                    fail('C12', f'`hard_settings` 第 {i} 条 source = {item["source"]!r}，必须以 用户确认 / 推导 开头')
            if key == 'pending' and item.get('stage') is not None:
                st = STAGE_NUM.get(item['stage'], item['stage'])
                if st not in STAGES:
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
    check_output_dirs(c, root)
    check_naming(c)
    check_player_agency(c)
    check_lists(c)

    rules = {
        'C00': '契约可解析',
        'C01': 'project 必填项',
        'C02': 'workspace / name 指向真实目录',
        'C03': 'stages_requested 与 web_research 类型',
        'C04': 'stages 键为 1–7、值在枚举内',
        'C05': 'artifacts 是列表且 type 非空',
        'C06': 'artifact type 在枚举内',
        'C07': 'path 相对、无 ..、不重复',
        'C08': 'path 指向真实存在的产物',
        'C09': 'done 的阶段有对应产物',
        'C10': 'delivery 路线与文件自洽',
        'C11': 'naming 表与 provisional 收口',
        'C12': 'hard_settings / pending / decisions 形状',
        'C13': 'decisions[].state 四态与「未答≠委托」',
        'C14': 'partial 阶段必须挂 pending',
        'C15': '最终产物/ 交付前空、交付后三件齐',
        'C16': 'player_agency 三档自洽（放宽须用户确认，delegated 须有时长）',
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

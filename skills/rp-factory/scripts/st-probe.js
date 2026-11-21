#!/usr/bin/env node
/**
 * 真机验收：用无头 Chrome 打开正在跑的酒馆，点开角色卡，量前端界面的高度。
 *
 * 用途：导入之后确认「界面真的渲染出来了」，而不是只剩一条代码块或一圈 2px 黑边。
 *
 * 依赖：puppeteer-core + 本机 Chrome（不需要下载 Chromium）
 *   npm i puppeteer-core
 *
 * 用法:
 *   node scripts/st-probe.js --st http://127.0.0.1:8000 --char 白潮
 *   node scripts/st-probe.js --char 白潮 --shot shot.png --chrome "C:/Program Files/Google/Chrome/Application/chrome.exe"
 *   node scripts/st-probe.js --char 白潮 --json --report 制作文件/项目记录/probe.json
 *   node scripts/st-probe.js --char 白潮 --interact-input "input[data-name=灯芯]=55" \
 *        --interact-click "#rp-cc-apply" --interact-click "#rp-cc-confirm" \
 *        --interact-expect "stat_data.灯芯=55"
 *
 * 它产出的不是「验收通过」，是 L4 里可脚本判的五维（references/acceptance.md 第三节）：
 *   import     卡在侧栏、名字对得上
 *   fresh_chat 新聊天首条消息真渲染出内容
 *   console    没有新增页面错误
 *   dom        挂了 iframe、高度够、没有裸代码块漏出
 *   interaction 给了 --interact-* 时：点完之后变量真的变了（否则该维跳过，写「未测」）
 * 另外六维（dependencies/style/data/lifecycle/responsive/security）只能人看。
 *
 * 退出码: 0 = 至少一个 iframe 渲染出高度；1 = 没渲染；2 = 环境问题（缺依赖/缺 Chrome/连不上）。
 */
'use strict';

// 仓库根 package.json 是 "type": "module"（DSH 插件与 .mjs 脚本需要），
// 所以这份必须用 ESM 写法 + createRequire 去加载 puppeteer-core。
import fs from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);

function arg(name, fallback) {
  const i = process.argv.indexOf('--' + name);
  return i === -1 ? fallback : process.argv[i + 1];
}

// 可重复参数：--interact-click 可以给多次
function argAll(name) {
  const out = [];
  process.argv.forEach((a, i) => {
    if (a === '--' + name && process.argv[i + 1] !== undefined) out.push(process.argv[i + 1]);
  });
  return out;
}

function pickPath(obj, path) {
  return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj);
}

function diffVars(before, after) {
  const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})]);
  const changed = [];
  for (const k of keys) {
    const a = JSON.stringify(before ? before[k] : undefined);
    const b = JSON.stringify(after ? after[k] : undefined);
    if (a !== b) changed.push(`${k}: ${a === undefined ? '（无）' : a} → ${b === undefined ? '（无）' : b}`);
  }
  return changed;
}

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  process.env.CHROME,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].filter(Boolean);

function emit(report, asJson, reportPath) {
  const payload = { tool: 'st-probe', layer: 'L4', ...report };
  if (asJson) console.log(JSON.stringify(payload, null, 2));
  if (reportPath) {
    try {
      fs.writeFileSync(reportPath, JSON.stringify(payload, null, 2) + '\n');
      console.log(`报告: ${reportPath}`);
    } catch (e) {
      console.error(`写报告失败（不影响判定）: ${e.message}`);
    }
  }
}

async function main() {
  let puppeteer;
  try {
    puppeteer = require('puppeteer-core');
  } catch (e) {
    console.error('缺少 puppeteer-core：先在本目录跑 `npm i puppeteer-core`（不会下载 Chromium）');
    return 2;
  }
  const chrome = arg('chrome') || CHROME_CANDIDATES.find(p => { try { return fs.existsSync(p); } catch (_) { return false; } });
  if (!chrome) {
    console.error('找不到 Chrome：用 --chrome 指定可执行文件');
    return 2;
  }

  const base = (arg('st', 'http://127.0.0.1:8000')).replace(/\/$/, '');
  const want = arg('char', '');
  const shot = arg('shot', '');
  const minHeight = Number(arg('min-height', '60'));
  const asJson = process.argv.includes('--json');
  const reportPath = arg('report', '');

  const browser = await puppeteer.launch({
    executablePath: chrome,
    headless: 'new',
    args: ['--no-sandbox'],
    defaultViewport: { width: 1400, height: 1200 },
  });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e.message).slice(0, 160)));
    await page.goto(base, { waitUntil: 'networkidle2', timeout: 60000 });
    await new Promise(r => setTimeout(r, 2500));

    const picked = await page.evaluate(name => {
      const cards = [...document.querySelectorAll('#rm_print_characters_block .character_select')];
      const card = name ? cards.find(c => (c.textContent || '').includes(name)) : cards[0];
      if (!card) return null;
      card.scrollIntoView();
      card.click();
      return (card.textContent || '').trim().slice(0, 40);
    }, want);
    if (!picked) {
      // import 维失败也要落报告：账本里记的是「跑过、这一维没过」，不是「没跑」。
      emit({ card: want || null, dimensions: { import: { ok: false, detail: `没在侧栏找到角色卡${want ? `「${want}」` : ''}` } }, verdict: 'fail' },
           asJson, reportPath);
      console.error(`没在侧栏找到角色卡${want ? `「${want}」` : ''}：确认它已导入、名字对得上`);
      return 1;
    }
    await new Promise(r => setTimeout(r, 6000));

    const report = await page.evaluate(() => {
      const mes = [...document.querySelectorAll('#chat > .mes')].pop();
      const text = mes && mes.querySelector('.mes_text');
      const frames = [...(text ? text.querySelectorAll('iframe') : [])];
      return {
        mesCount: document.querySelectorAll('#chat > .mes').length,
        height: text ? text.clientHeight : 0,
        text: (text ? text.innerText : '').replace(/\s+/g, ' ').slice(0, 90),
        iframes: frames.map(f => f.clientHeight),
        // 酒馆助手会把代码块包进 .TH-render 并保留一个折叠用的 pre，那一份不算「裸代码块漏出」
        preCount: text ? [...text.querySelectorAll('pre')].filter(p => !p.closest('.TH-render')).length : 0,
      };
    });

    const inner = [];
    for (const fr of page.frames()) {
      if (fr === page.mainFrame()) continue;
      try {
        inner.push(await fr.evaluate(() => ({
          h: document.body ? document.body.scrollHeight : 0,
          text: (document.body ? document.body.innerText : '').replace(/\s+/g, ' ').slice(0, 90),
        })));
      } catch (_) { /* 未加载完的 iframe 直接跳过 */ }
    }

    const tallest = Math.max(0, ...report.iframes, ...inner.map(f => f.h));

    // ---- 可选的交互探测：点一下，变量真的变了吗 ----
    const inputs = argAll('interact-input').map(s => {
      const i = s.lastIndexOf('=');
      return i < 0 ? null : { kind: 'input', sel: s.slice(0, i), value: s.slice(i + 1) };
    }).filter(Boolean);
    const clicks = argAll('interact-click').map(sel => ({ kind: 'click', sel }));
    const expect = arg('interact-expect', '');
    const steps = [...inputs, ...clicks];

    let interaction = { ok: null, detail: '未测（没给 --interact-*）' };
    if (steps.length) {
      const frames = await page.$$('#chat iframe');
      const handle = frames[frames.length - 1];
      const frame = handle && await handle.contentFrame();
      const readVars = () => frame.evaluate(() => {
        try {
          if (typeof Mvu === 'undefined') return { error: 'Mvu 未启用，改不了变量' };
          const d = Mvu.getMvuData({ type: 'message', message_id: getCurrentMessageId() });
          return { data: (d && d.stat_data) ? d.stat_data : null };
        } catch (e) { return { error: String((e && e.message) || e) }; }
      });

      if (!frame) {
        interaction = { ok: false, detail: '没有 iframe，无法交互' };
      } else {
        const before = await readVars();
        if (before.error) {
          interaction = { ok: false, detail: before.error };
        } else {
          let stepErr = null;
          for (const s of steps) {
            try {
              await frame.evaluate(({ kind, sel, value }) => {
                const el = document.querySelector(sel);
                if (!el) throw new Error('找不到 ' + sel);
                if (kind === 'input') {
                  el.value = value;
                  el.dispatchEvent(new Event('input', { bubbles: true }));
                  el.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                  el.click();
                }
              }, s);
              await new Promise(r => setTimeout(r, 400));
            } catch (e) { stepErr = `${s.kind} ${s.sel}: ${e.message}`; break; }
          }
          if (stepErr) {
            interaction = { ok: false, detail: stepErr };
          } else {
            await new Promise(r => setTimeout(r, 1200));
            const after = await readVars();
            if (after.error) {
              interaction = { ok: false, detail: after.error };
            } else {
              const changed = diffVars(before.data, after.data);
              if (expect) {
                const [path, want] = [expect.slice(0, expect.lastIndexOf('=')), expect.slice(expect.lastIndexOf('=') + 1)];
                const got = pickPath(after.data, path.replace(/^stat_data\./, ''));
                const match = String(got) === String(want);
                interaction = {
                  ok: match && changed.length > 0,
                  detail: `期望 ${path}=${want}，实际 ${got}；变量变化 ${changed.length ? changed.join('; ') : '无'}`,
                };
              } else {
                interaction = {
                  ok: changed.length > 0,
                  detail: changed.length ? `变量变化：${changed.join('; ')}` : '点完了，变量没变',
                };
              }
            }
          }
        }
      }
    }

    // 四个可脚本判的维。detail 是给账本抄的，不要写成「正常」。
    const dimensions = {
      import: { ok: true, detail: `侧栏命中「${picked}」` },
      fresh_chat: {
        // 首条就是纯 HTML 界面时 innerText 为空、但 iframe 已经挂上——那也算渲染出来了
        ok: report.mesCount >= 1 && (report.text.length > 0 || report.iframes.length > 0),
        detail: `消息数 ${report.mesCount}，首条正文 ${report.text ? JSON.stringify(report.text) : '（空）'}`,
      },
      console: {
        ok: errors.length === 0,
        detail: errors.length ? `${errors.length} 条页面错误：${errors.slice(-3).join(' | ')}` : '页面错误 0',
      },
      dom: {
        ok: report.iframes.length > 0 && tallest >= minHeight && report.preCount === 0,
        detail: `iframe ${report.iframes.length} 个（高度 ${report.iframes.join(', ') || '无'}），` +
                `最高 ${tallest}px，pre 块 ${report.preCount} 个`,
      },
      interaction,
    };

    if (shot) {
      await page.screenshot({ path: shot });
      console.log(`截图: ${shot}`);
    }

    console.log(`角色: ${picked} · 消息数 ${report.mesCount} · 首条正文文字 ${JSON.stringify(report.text)}`);
    console.log(`iframe 高度: ${report.iframes.length ? report.iframes.join(', ') : '（没有 iframe）'}`);
    inner.forEach((f, i) => console.log(`  iframe#${i} 内容高度 ${f.h} · ${JSON.stringify(f.text)}`));
    for (const [name, dim] of Object.entries(dimensions)) {
      const mark = dim.ok === null ? 'skip' : (dim.ok ? 'ok  ' : 'FAIL');
      console.log(`  [${mark}] ${name.padEnd(11)} ${dim.detail}`);
    }

    if (report.iframes.length === 0) {
      console.log('判定: 没渲染成 iframe——检查正则是否启用、酒馆助手是否开启「消息渲染」、消息里是否有 <body>');
      emit({ card: picked, dimensions, verdict: 'fail' }, asJson, reportPath);
      return 1;
    }
    if (tallest < minHeight) {
      console.log(`判定: iframe 只有 ${tallest}px——多半是内联脚本语法错误（HTML 实体被解码），跑 validate-frontend.py 的 F04`);
      emit({ card: picked, dimensions, verdict: 'fail' }, asJson, reportPath);
      return 1;
    }
    // 判定跟维度必须一致：任何一维 fail 就不算 pass（interaction 为 null 表示未测，不参与）
    const failed = Object.entries(dimensions).filter(([, d]) => d.ok === false).map(([k]) => k);
    if (failed.length) {
      console.log(`判定: 未通过（${failed.join(' / ')}）`);
      emit({ card: picked, dimensions, verdict: 'fail' }, asJson, reportPath);
      return 1;
    }
    console.log(`判定: 渲染正常（最高 ${tallest}px）`);
    emit({ card: picked, dimensions, verdict: 'pass' }, asJson, reportPath);
    return 0;
  } finally {
    await browser.close();
  }
}

main().then(code => process.exit(code)).catch(err => {
  console.error('探测失败:', err.message);
  process.exit(2);
});

import asyncio, sys
from playwright.async_api import async_playwright

import pathlib
SP = "."
URL = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
results = []
def check(name, ok, detail=''):
    results.append((name, ok, detail)); print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail else ''))

async def S(page, js): return await page.evaluate(js)

async def start(page):
    await page.click('#playBtn')
    await page.wait_for_timeout(300)
    m = await S(page, 'UVIT.state.mode')
    check('countdown starts after Play', m == 'countdown', m)
    await page.wait_for_function('UVIT.state.mode === "playing"', timeout=5000)
    check('countdown reaches GO and play begins', True)

async def place(page, typ, x, y):
    await S(page, f'(() => {{ UVIT.state.objs = []; UVIT.state.spawnTimer = 99; const o = UVIT.spawn("{typ}", {x}, {y}); return o.id; }})()')

async def run(browser, mobile=False):
    tag = 'mobile' if mobile else 'desktop'
    ctx = await browser.new_context(viewport={'width': 390, 'height': 780} if mobile else {'width': 1280, 'height': 800}, has_touch=mobile, device_scale_factor=2 if mobile else 1)
    page = await ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    await page.goto(URL); await page.wait_for_timeout(800)
    await page.screenshot(path=f'{SP}/{tag}_menu.png')
    if mobile:
        await page.click('#howBtn'); await page.wait_for_timeout(500)
        await page.screenshot(path=f'{SP}/{tag}_how.png'); await page.click('#howClose'); await page.wait_for_timeout(400)
    await start(page)
    b = await S(page, '({l:UVIT.bounds.l,t:UVIT.bounds.t,r:UVIT.bounds.r,b:UVIT.bounds.b})')
    cx, cy = (b['l'] + b['r']) / 2, (b['t'] + b['b']) / 2
    tap = (lambda x, y: page.touchscreen.tap(x, y)) if mobile else (lambda x, y: page.mouse.click(x, y))

    async def smash(typ, freeze_filter=True):
        if freeze_filter: await S(page, 'UVIT.state.filter.next = 999')
        await place(page, typ, cx, cy)
        before = await S(page, 'UVIT.state.score')
        await tap(cx, cy); await page.wait_for_timeout(60)
        return (await S(page, 'UVIT.state.score')) - before

    await S(page, 'UVIT.state.combo = 0')
    for typ, pts in [('star', 10), ('agn', 50)]:
        await S(page, 'UVIT.state.combo = 0')
        d = await smash(typ); check(f'{tag}: {typ} gives {pts}', d == pts, d)
    for typ, pts in [('rrlyrae', 40), ('galaxy', 60), ('noise', 15)]:
        await S(page, 'UVIT.state.combo = 0')
        d = await smash(typ); check(f'{tag}: {typ} gives {pts}', d == pts, d)

    # no double scoring: tap same spot twice
    await S(page, 'UVIT.state.combo = 0')
    await place(page, 'star', cx, cy)
    s0 = await S(page, 'UVIT.state.score'); await tap(cx, cy); await tap(cx, cy); await page.wait_for_timeout(50)
    check(f'{tag}: object scores only once', (await S(page, 'UVIT.state.score')) - s0 == 10)

    # combo multipliers
    await S(page, 'UVIT.state.combo = 0')
    gains = []
    for i in range(10):
        gains.append(await smash('star'))
    check(f'{tag}: combo multipliers 1,1,1.2,1.2,1.5..,2', gains == [10, 10, 12, 12, 15, 15, 15, 15, 15, 20], gains)

    # filter flip bonus
    await S(page, '(() => { const G = UVIT.state; G.combo = 0; G.filter.next = G.elapsed; G.filter.count = 0; })()')
    await page.wait_for_timeout(900)
    mode = await S(page, 'UVIT.state.filter.mode')
    await S(page, 'UVIT.state.objs = []; UVIT.state.spawnTimer = 99')
    o = await S(page, f'(() => {{ const o = UVIT.spawn("agn", {cx}, {cy}); return o.fuv; }})()')
    s0 = await S(page, 'UVIT.state.score'); await tap(cx, cy); await page.wait_for_timeout(50)
    check(f'{tag}: filter flip ({mode}) highlighted AGN pays +20 bonus', (await S(page, 'UVIT.state.score')) - s0 == 70, (await S(page, 'UVIT.state.score')) - s0)
    if not mobile: await page.screenshot(path=f'{SP}/{tag}_play.png')

    # hazard
    await S(page, 'UVIT.state.combo = 4')
    await place(page, 'rock', cx, cy)
    s0 = await S(page, 'UVIT.state.score'); l0 = await S(page, 'UVIT.state.lives')
    await tap(cx, cy); await page.wait_for_timeout(50)
    st = await S(page, '({l: UVIT.state.lives, c: UVIT.state.combo, s: UVIT.state.score})')
    check(f'{tag}: rock costs a life, resets combo, keeps score', st['l'] == l0 - 1 and st['c'] == 0 and st['s'] == s0, st)
    await place(page, 'meteor', cx, cy)
    await tap(cx, cy); await page.wait_for_timeout(50)
    check(f'{tag}: meteor costs a life', await S(page, 'UVIT.state.lives') == l0 - 2)

    # empty tap no penalty
    await S(page, 'UVIT.state.objs = []')
    l1 = await S(page, 'UVIT.state.lives'); await tap(cx, cy)
    check(f'{tag}: tapping empty space is harmless', await S(page, 'UVIT.state.lives') == l1)

    # combo expiry
    await smash('star'); await page.wait_for_timeout(2700)
    check(f'{tag}: combo expires after idle', await S(page, 'UVIT.state.combo') == 0)

    # pause / resume
    await S(page, 'UVIT.state.spawnTimer = 0')
    await page.click('#pauseBtn') if not mobile else await page.tap('#pauseBtn')
    e0 = await S(page, 'UVIT.state.elapsed'); n0 = await S(page, 'UVIT.state.objs.map(o=>o.x+","+o.y).join("|")')
    await page.wait_for_timeout(700)
    e1 = await S(page, 'UVIT.state.elapsed'); n1 = await S(page, 'UVIT.state.objs.map(o=>o.x+","+o.y).join("|")')
    vis = await page.is_visible('#resumeBtn')
    check(f'{tag}: pause freezes timer and objects', e0 == e1 and n0 == n1 and vis)
    if mobile: await page.screenshot(path=f'{SP}/{tag}_pause.png')
    await page.click('#resumeBtn'); await page.wait_for_timeout(400)
    check(f'{tag}: resume continues timer', await S(page, 'UVIT.state.elapsed') > e1)

    # difficulty progression
    await S(page, 'UVIT.state.elapsed = 52')
    await page.wait_for_timeout(1500)
    info = await S(page, '({n: UVIT.state.objs.length, lvl: document.getElementById("level").textContent, fin: document.getElementById("timer").classList.contains("final")})')
    check(f'{tag}: late round is level 5 with final-10s state', info['lvl'] == 'LV5' and info['fin'], info)
    if mobile: await page.screenshot(path=f'{SP}/{tag}_play.png')

    # bounds: all objects inside play area
    inside = await S(page, '''UVIT.state.objs.filter(o=>o.type!=="meteor").every(o => o.x>=UVIT.bounds.l-1 && o.x<=UVIT.bounds.r+1 && o.y>=UVIT.bounds.t-1 && o.y<=UVIT.bounds.b+1)''')
    check(f'{tag}: objects stay inside play area (below HUD)', inside)

    # timer end
    score = await S(page, 'UVIT.state.score')
    await S(page, 'UVIT.state.elapsed = 59.5')
    await page.wait_for_function('UVIT.state.mode === "results"', timeout=4000)
    fs = await page.inner_text('#finalScore')
    check(f'{tag}: results appear when timer hits zero', fs.replace(',', '') == str(score), fs)
    await page.screenshot(path=f'{SP}/{tag}_results.png')
    stats = await S(page, '[...document.querySelectorAll(".stat .v")].map(e=>e.textContent)')
    check(f'{tag}: results list stats', len(stats) == 7, stats)

    # best persists after reload
    await page.reload(); await page.wait_for_timeout(600)
    mb = await page.inner_text('#menuBest')
    check(f'{tag}: best score persists after refresh', mb.replace(',', '') == str(score), mb)

    # lives to zero ends early; play again resets
    await start(page)
    for _ in range(3):
        await place(page, 'rock', cx, cy); await tap(cx, cy); await page.wait_for_timeout(40)
    m = await S(page, 'UVIT.state.mode')
    check(f'{tag}: zero lives ends round early', m == 'over', m)
    await page.wait_for_function('UVIT.state.mode === "results"', timeout=3000)
    await page.click('#againBtn')
    st = await S(page, '({m:UVIT.state.mode,s:UVIT.state.score,l:UVIT.state.lives,c:UVIT.state.combo,e:UVIT.state.elapsed,h:UVIT.state.stats.hazard})')
    check(f'{tag}: Play Again resets all state', st == {'m': 'countdown', 's': 0, 'l': 3, 'c': 0, 'e': 0, 'h': 0}, st)

    # restart from pause & quit to menu
    await page.wait_for_function('UVIT.state.mode === "playing"', timeout=5000)
    await page.click('#pauseBtn'); await page.click('#restartBtn')
    check(f'{tag}: Restart from pause works', await S(page, 'UVIT.state.mode') == 'countdown')
    await page.wait_for_timeout(500); await page.click('#pauseBtn'); await page.click('#quitBtn'); await page.wait_for_timeout(400)
    check(f'{tag}: Quit returns to menu', await S(page, 'UVIT.state.mode') == 'menu' and await page.is_visible('#playBtn'))

    # mute toggle
    t0 = await page.inner_text('#soundBtn1'); await page.click('#soundBtn1'); t1 = await page.inner_text('#soundBtn1')
    await page.reload(); await page.wait_for_timeout(300); t2 = await page.inner_text('#soundBtn1')
    check(f'{tag}: mute toggles and persists', t0 != t1 and t1 == t2, f'{t0} -> {t1} -> {t2}')

    # single rAF loop: measure frame callbacks rate after many restarts
    for _ in range(4):
        await page.click('#playBtn'); await page.wait_for_timeout(100); await S(page, 'UVIT.pauseGame()'); await page.click('#quitBtn'); await page.wait_for_timeout(100)
    hscroll = await S(page, 'document.documentElement.scrollWidth > window.innerWidth')
    check(f'{tag}: no horizontal overflow', not hscroll)
    errors = [e for e in errors if 'Failed to load resource' not in e]  # ignore offline font loads
    check(f'{tag}: no script errors', not errors, errors[:3])
    await ctx.close()

async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch()
        await run(br, False)
        await run(br, True)
        await br.close()
    fails = [r for r in results if not r[1]]
    print(f'\n{len(results)-len(fails)}/{len(results)} passed')
asyncio.run(main())

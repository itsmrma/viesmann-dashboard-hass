// Run with npm run test:ui. Add -- --screenshots=before (or after) for PR evidence.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '../..');
const screenshotSet = process.argv.find(arg => arg.startsWith('--screenshots='))?.split('=')[1];
const evidenceDir = process.argv.find(arg => arg.startsWith('--evidence-dir='))?.split('=')[1] || 'docs/issue-22';
const htmlFile = process.argv.find(arg => arg.startsWith('--html='))?.slice('--html='.length)
  || path.join(root, 'addon/viesmann_dashboard/viesmann_dashboard/www/index.html');
const date = '2026-10-27T12:00:00Z';
const entity = (key, state, unit, extra = {}) => ({
  entity_id: `sensor.vicare_${key}`, translation_key: key, device_id: 'heat-pump',
  state: String(state), last_updated: date, area: null,
  attributes: { friendly_name: key.replaceAll('_', ' '), unit_of_measurement: unit }, ...extra,
});
const fixture = {
  sources: Object.fromEntries(['2701', 'vicare'].map(key => [key, { status: 'fresh', last_updated: date }])),
  '2701': { season: 'winter', zones: ['Circuito diretto', 'Cucina', 'Sala', 'Matrimoniale', 'Cameretta', 'Armadi', 'Bagni'].map((name, id) => ({
    id, name, room_temperature: 20.5 + id / 10, target_temperature: 21, humidity: id ? 48 : null, active: id % 2 === 0,
  })) },
  vicare: [
    entity('power_consumption_today', 8.4, 'kWh', { area: 'Cucina', entity_id: 'sensor.renamed_daily' }),
    entity('energy_summary_consumption_heating_currentday', 6.1, 'kWh'),
    entity('energy_dhw_summary_consumption_heating_currentday', 2.3, 'kWh'),
    entity('supply_temperature', 34.8, '°C'), entity('return_temperature', 29.1, '°C'),
    entity('dhw_storage_temperature', 48.2, '°C'), entity('outside_temperature', 12.3, '°C'),
    entity('compressor_power', 1.2, 'kW'), entity('compressor_modulation', 42, '%'),
    entity('signal_strength', -62, 'dBm'), entity('compressor_hours_loadclass1', 4567, 'h'),
  ],
};
fixture.history = {
  '2701': Array.from({ length: 8 }, (_, index) => ({
    at: new Date(Date.parse(date) - (7 - index) * 120000).toISOString(),
    readings: fixture['2701'].zones.map(zone => ({ ...zone,
      room_temperature: zone.room_temperature - (7 - index) * .08,
      humidity: zone.humidity == null ? null : zone.humidity + (7 - index),
      active: index % 3 === 0 ? false : zone.active,
    })),
  })),
  vicare: Array.from({ length: 8 }, (_, index) => ({
    at: new Date(Date.parse(date) - (7 - index) * 120000).toISOString(),
    readings: fixture.vicare.map(entity => ({ id: entity.entity_id,
      value: Number(entity.state) * (1 - (7 - index) * .025), unit: entity.attributes.unit_of_measurement })),
  })),
};
let payload = structuredClone(fixture);
let refreshStatus = 200, refreshDelay = 0;
const refreshRequests = [];
const failures = [];
function check(name, run) {
  return Promise.resolve().then(run).then(() => console.log(`PASS ${name}`), error => {
    failures.push(name); console.error(`FAIL ${name}: ${error.stack}`);
  });
}
async function main() {
  const server = http.createServer((req, res) => {
    if (req.url.endsWith('/api/refresh/2701') && req.method === 'POST') {
      refreshRequests.push({ url: req.url, header: req.headers['x-requested-with'] });
      setTimeout(() => {
        res.writeHead(refreshStatus, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ snapshot: payload }));
      }, refreshDelay);
    } else if (req.url.endsWith('/api/status')) {
      res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(payload));
    } else {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.end(fs.readFileSync(htmlFile));
    }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, hasTouch: true, timezoneId: 'Europe/Rome' });
  const errors = [], writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (!['GET', 'HEAD'].includes(request.method()) && !request.url().endsWith('/api/refresh/2701')) writes.push(request.url()); });
  const base = `http://127.0.0.1:${server.address().port}/`;
  await page.goto(base);
  await page.locator('.room-card').first().waitFor();
  await page.evaluate(() => document.fonts.ready);
  async function capture(name) {
    if (!screenshotSet) return;
    const dir = path.join(root, evidenceDir, screenshotSet);
    fs.mkdirSync(dir, { recursive: true });
    await page.screenshot({ path: path.join(dir, `${name}.png`), fullPage: !name.startsWith('color-dialog'), animations: 'disabled' });
  }
  let visitNumber = 0;
  async function visit(hash) {
    await page.goto(`${base}?case=${++visitNumber}${hash}`);
    await page.locator('nav').waitFor(); await page.evaluate(() => document.fonts.ready);
  }
  async function checkColorSliderAlignment() {
    for (const slider of await page.locator('.color-channel input').all()) {
      const png = (await slider.screenshot({ animations: 'disabled' })).toString('base64');
      const geometry = await slider.evaluate(async (input, png) => {
        const color = getComputedStyle(input).accentColor.match(/[\d.]+/g).slice(0, 3).map(Number);
        const image = new Image();image.src = `data:image/png;base64,${png}`;await image.decode();
        const canvas = document.createElement('canvas');canvas.width = image.width;canvas.height = image.height;
        const context = canvas.getContext('2d');context.drawImage(image, 0, 0);
        const { data } = context.getImageData(0, 0, image.width, image.height), rows = [];
        for (let y = 0; y < image.height; y++) {
          let count = 0;
          for (let x = 0; x < image.width; x++) {
            const offset = (y * image.width + x) * 4;
            if (color.every((value, channel) => Math.abs(data[offset + channel] - value) <= 1)) count++;
          }
          if (count >= 4) rows.push(y);
        }
        return { center: (rows[0] + rows.at(-1) + 1) / 2, trackCenter: image.height / 2 };
      }, png);
      assert.ok(Math.abs(geometry.center - geometry.trackCenter) <= 1,
        `${await slider.getAttribute('aria-label')}: thumb ${geometry.center}px, track ${geometry.trackCenter}px`);
    }
  }
  await capture('overview-desktop');
  await check('requested room order', async () => {
    const names = await page.locator('.room-title').allTextContents();
    assert.deepEqual(names, ['Cucina','Sala','Matrimoniale','Cameretta','Armadi','Bagni','Circuito diretto']);
    const boxes = await page.locator('.room-card').evaluateAll(nodes => nodes.map(node => ({ x: node.offsetLeft, y: node.offsetTop })));
    assert.equal(boxes.at(-1).x, boxes[0].x); assert.ok(boxes.at(-1).y > boxes.at(-2).y);
  });
  await visit('#room/cucina');
  await capture('room-desktop');
  await check('season preview removed', async () => assert.equal(await page.locator('.season-control').count(), 0));
  async function equalControls() {
    const metrics = await page.locator('.control-group').evaluateAll(nodes => nodes.map(node => ({
      height: node.getBoundingClientRect().height,
      font: getComputedStyle(node.querySelector('output')).fontSize,
      sliderY: node.querySelector('input').getBoundingClientRect().top - node.getBoundingClientRect().top,
    })));
    assert.equal(metrics.length, 2);
    assert.equal(metrics[0].height, metrics[1].height);
    assert.equal(metrics[0].font, metrics[1].font);
    assert.equal(metrics[0].sliderY, metrics[1].sliderY);
    const overlap = await page.locator('.temperature-control').evaluate(node => {
      const value = node.querySelector('.setpoint-value'), stepper = node.querySelector('.setpoint-stepper');
      const last = value.lastElementChild.getBoundingClientRect();
      return last.right > stepper.getBoundingClientRect().left;
    });
    assert.equal(overlap, false, 'value and +/- buttons must not overlap');
  }
  await check('equal control height, font and track position', equalControls);
  await check('local temperature preview sends no commands', async () => {
    await page.getByRole('button', { name: 'Aumenta temperatura obiettivo di mezzo grado', exact: true }).click();
    assert.equal(await page.locator('.temperature-control output').textContent(), '21.5');
    assert.deepEqual(writes, []);
  });
  await visit('#system');
  await capture('system-desktop');
  await check('curated heat pump readings include assigned, renamed entities', async () => {
    const text = await page.locator('#app').innerText();
    assert.match(text, /Consumo elettrico oggi/); assert.match(text, /8[,.]4/);
    assert.match(text, /Mandata/); assert.match(text, /34[,.]8/);
    assert.doesNotMatch(text, /signal_strength|compressor_hours_loadclass1/);
  });
  await check('back link returns a directly opened room to the overview', async () => {
    await visit('#room/cucina');
    await page.getByRole('link', { name: 'Torna alla panoramica' }).click();
    await page.locator('.room-card').first().waitFor();
    assert.equal(await page.locator('h1').textContent(), 'Panoramica');
  });
  await check('internal color dialog validates HEX, applies, cancels and survives polling', async () => {
    await visit('#settings');
    await page.getByRole('button', { name: 'Personalizzata', exact: false }).click();
    assert.equal(await page.locator('input[type=color]').count(), 0);
    const trigger = page.getByRole('button', { name: 'Accento', exact: true });
    await trigger.click();
    const dialog = page.getByRole('dialog'), hex = dialog.getByRole('textbox', { name: 'Codice HEX' });
    assert.equal(await hex.evaluate(node => node === document.activeElement), true);
    await hex.fill('#xyz');
    assert.equal(await dialog.getByRole('button', { name: 'Applica colore' }).isDisabled(), true);
    assert.equal(await hex.getAttribute('aria-invalid'), 'true');
    await hex.fill('#A1B2C3');
    // Simulate the same render used by the 15-second status refresh.
    await page.evaluate(() => render(latest));
    assert.equal(await hex.inputValue(), '#A1B2C3');
    assert.equal(await dialog.isVisible(), true);
    await dialog.getByRole('button', { name: 'Applica colore' }).click();
    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('heating-dashboard-custom-palette')));
    assert.equal(stored.light.accent, '#a1b2c3');
    assert.equal(await trigger.evaluate(node => node === document.activeElement), true);
    await trigger.click();await hex.fill('#123456');await page.keyboard.press('Escape');
    assert.equal(await dialog.isVisible(), false);
    await trigger.click();assert.equal(await hex.inputValue(), '#A1B2C3');
    await hex.fill('#abc');await dialog.getByRole('button', { name: 'Annulla', exact: true }).click();
    await trigger.click();assert.equal(await hex.inputValue(), '#A1B2C3');
    await hex.fill('369');await hex.press('Enter');
    await page.reload();
    await trigger.click();assert.equal(await hex.inputValue(), '#336699');
    await dialog.getByRole('slider', { name: 'Tonalità' }).fill('180');
    assert.notEqual(await hex.inputValue(), '#336699');
    await check('color slider thumbs centered on desktop tracks', checkColorSliderAlignment);
    await capture('color-dialog-desktop');
    await page.setViewportSize({ width: 320, height: 568 });
    await check('color slider thumbs centered on mobile tracks', checkColorSliderAlignment);
    assert.equal(await dialog.evaluate(node => node.scrollWidth <= node.clientWidth), true);
    // Keep focus inside the modal, including Tab at either end.
    await dialog.getByRole('button', { name: 'Applica colore' }).focus();await page.keyboard.press('Tab');
    assert.equal(await dialog.evaluate(node => node.contains(document.activeElement)), true);
    await capture('color-dialog-mobile');
    await page.keyboard.press('Escape');
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.evaluate(() => { localStorage.clear(); });
  });
  await check('theme-specific palettes, keyboard feedback and reduced motion', async () => {
    await visit('#settings');
    await page.getByRole('button', { name: 'Scuro Per ambienti', exact: false }).click();
    await page.getByRole('button', { name: 'Personalizzata', exact: false }).click();
    const trigger = page.getByRole('button', { name: 'Accento', exact: true });
    await trigger.click();
    await page.getByRole('textbox', { name: 'Codice HEX' }).fill('#8055aa');
    await page.getByRole('button', { name: 'Applica colore' }).click();
    const colors = await page.evaluate(() => JSON.parse(localStorage.getItem('heating-dashboard-custom-palette')));
    assert.equal(colors.dark.accent, '#8055aa');assert.notEqual(colors.light.accent, '#8055aa');
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await trigger.click();
    assert.equal(await page.getByRole('dialog').evaluate(node => node.getAnimations().length), 0);
    await capture('color-dialog-dark');
    await page.keyboard.press('Escape');
    await visit('#room/cucina');
    await page.getByRole('button', { name: 'Aumenta temperatura obiettivo di mezzo grado', exact: true }).focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.temperature-control output').textContent(), '21.5');
    assert.equal(await page.locator('.temperature-control output').evaluate(node => node.getAnimations().length), 0);
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.evaluate(() => { localStorage.clear(); });
  });
  for (const width of [320, 375, 390, 520, 600, 760, 768, 1024, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    const navigationTops = [];
    for (const hash of ['', '#room/cucina', '#system', '#settings']) {
      await visit(hash);
      if (!hash.startsWith('#room')) navigationTops.push(await page.locator('nav').evaluate(node => node.getBoundingClientRect().top));
      await check(`no overflow ${width}px ${hash || 'overview'}`, async () => {
        const size = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
        assert.ok(size.scroll <= size.client, JSON.stringify(size));
      });
      if (hash === '#room/cucina') await check(`equal controls ${width}px`, equalControls);
      if (width === 390 && hash !== '#settings') await capture(hash === '#system' ? 'system-mobile' : hash ? 'room-mobile' : 'overview-mobile');
    }
    await check(`stable main-page headings ${width}px`, () => {
      assert.ok(Math.max(...navigationTops) - Math.min(...navigationTops) <= 1, JSON.stringify(navigationTops));
    });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await check('winter disables humidity; summer enables only a local preview', async () => {
    await visit('#room/cucina');
    assert.equal(await page.locator('.humidity-control input').isDisabled(), true);
    payload['2701'].season = 'summer';
    await visit('#room/cucina');
    assert.equal(await page.locator('.humidity-control input').isDisabled(), false);
    await page.getByRole('button', { name: 'Aumenta umidità obiettivo', exact: true }).click();
    assert.equal(await page.locator('.humidity-control output').textContent(), '51');
  });
  await check('native temperature slider responds to touch tap and drag', async () => {
    const slider = page.locator('.temperature-control input');
    await slider.scrollIntoViewIfNeeded();
    const rect = await slider.boundingBox();
    await page.touchscreen.tap(rect.x + rect.width * .6, rect.y + rect.height / 2);
    const first = Number(await slider.inputValue());
    assert.ok(first > 15 && first < 25);
    const cdp = await page.context().newCDPSession(page);
    const y = rect.y + rect.height / 2;
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: rect.x + rect.width * .6, y }] });
    for (const fraction of [.65, .7, .75, .8]) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: rect.x + rect.width * fraction, y }] });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    assert.ok(Number(await slider.inputValue()) > first);
    await cdp.detach();
  });
  await check('zero, unavailable, native units and metadata matching', async () => {
    payload.vicare = [entity('power_consumption_today', 0, 'Wh'), entity('supply_temperature', 'unavailable', '°C'),
      entity('return_temperature', 88, '°F'), entity('other', 999, 'kWh', { entity_id: 'sensor.fake_power_consumption_today' })];
    await visit('#system');
    const values = await page.locator('.system-value').allTextContents();
    assert.deepEqual(values, ['0Wh', '—', '88°F']);
    assert.match(await page.locator('.system-water').innerText(), /Non disponibile/);
    payload.vicare = [entity('supply_temperature', 35, '°C', { translation_key: null })];
    await visit('#system');
    assert.match(await page.locator('.system-water').innerText(), /35/);
    payload.vicare = [];
    await visit('#system');
    assert.match(await page.locator('.empty').innerText(), /Nessuna lettura/);
  });
  await check('additional areas stay visible before the final direct circuit', async () => {
    payload = structuredClone(fixture);
    payload.vicare.push(entity('unknown', 0, '', { area: 'Studio' }));
    await visit('');
    const names = await page.locator('.room-title').allTextContents();
    assert.ok(names.includes('Studio')); assert.equal(names.at(-1), 'Circuito diretto');
    payload['2701'].zones = []; payload.vicare = [];
    await visit(''); assert.equal(await page.locator('.room-card').count(), 0);
  });
  for (const language of ['it', 'en']) for (const theme of ['light', 'dark']) for (const palette of ['forest', 'ocean', 'violet', 'custom']) {
    payload = structuredClone(fixture);
    payload.vicare[0].attributes.friendly_name = 'PompaDiCaloreConNomeMoltoLungo'.repeat(8);
    payload.vicare.push(entity('power_consumption_today', 1.5, 'kWh', { entity_id: 'sensor.second_heat_pump' }));
    await page.evaluate(({ language, theme, palette }) => {
      for (const [key, value] of Object.entries({ language, theme, palette })) localStorage.setItem(`heating-dashboard-${key}`, value);
    }, { language, theme, palette });
    for (const hash of ['#room/cucina', '#system']) {
      await visit(hash);
      await check(`${language} ${theme} ${palette} ${hash} with long names`, async () => {
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        if (hash.startsWith('#room')) await equalControls();
      });
    }
  }
  await page.evaluate(() => { localStorage.setItem('heating-dashboard-language', 'en');localStorage.setItem('heating-dashboard-palette', 'forest'); });
  payload = structuredClone(fixture);
  await check('charts show real timestamps, native units and accessible values', async () => {
    await visit('');
    assert.equal(await page.getByRole('img', { name: 'Active zones over time · zones', exact: true }).count(), 1);
    await visit('#room/cucina');
    assert.equal(await page.getByRole('img', { name: 'Temperatures over time · °C', exact: true }).count(), 1);
    assert.equal(await page.getByRole('img', { name: 'Humidity over time · %', exact: true }).count(), 1);
    await page.locator('.trend-panel').first().locator('summary').click();
    assert.equal(await page.locator('.trend-panel').first().locator('tbody tr').count(), 8);
    assert.match(await page.locator('.trend-panel').first().innerText(), /12:46/);
    await visit('#system');
    assert.ok(await page.locator('.trend-svg').count() >= 3);
    assert.match(await page.locator('.trend-panel').allTextContents().then(text => text.join(' ')), /kWh|°C/);
    assert.equal(await page.locator('path[d*="NaN"]').count(), 0);
    payload.history['2701'][3].readings[1].room_temperature = null;
    await visit('#room/cucina');
    const measuredPath = await page.locator('.trend-svg').first().locator('path').first().getAttribute('d');
    assert.equal((measuredPath.match(/M/g) || []).length, 2, 'missing readings must break the curve');
    payload = structuredClone(fixture);
  });
  await check('missing and single samples show an honest chart empty state', async () => {
    payload.history = { '2701': [fixture.history['2701'][0]], vicare: [] };
    await visit('#room/cucina');
    assert.equal(await page.locator('.trend-svg').count(), 0);
    assert.match(await page.locator('.room-trends').innerText(), /Waiting for at least two valid readings/);
    payload['2701'].zones[1].active = null;
    await visit('#room/cucina');
    assert.equal(await page.locator('.heading .status-chip').textContent(), 'helpStatus unavailable');
    await visit('');
    assert.match(await page.locator('.summary').innerText(), /4 confirmed active zones/);
    assert.match(await page.locator('.summary').innerText(), /7 zones detected/);
    payload = structuredClone(fixture);
  });
  await check('manual refresh is single-flight, survives polling, reports errors and retries under ingress', async () => {
    // Serve exactly as an Ingress page with a relative API base.
    await page.route('**/api/hassio_ingress/test/', async route => {
      await route.fulfill({ contentType: 'text/html', body: fs.readFileSync(htmlFile, 'utf8').replace('</head>', '<base href="/api/hassio_ingress/test/"></head>') });
    });
    await page.goto(`${base}api/hassio_ingress/test/`);
    await page.locator('.refresh-button').waitFor();
    const originalButton = await page.locator('.refresh-button').elementHandle();
    await page.evaluate(() => render(latest));
    assert.equal(await originalButton.evaluate(node => node.isConnected), true, 'polling must retain the live status region and button');
    refreshDelay = 150;
    const button = page.getByRole('button', { name: 'Refresh 2701', exact: true });
    await button.click();
    assert.equal(await page.getByRole('button', { name: 'Refreshing…' }).isDisabled(), true);
    await page.evaluate(() => render(latest));
    assert.equal(await page.getByRole('button', { name: 'Refreshing…' }).isDisabled(), true);
    await page.getByRole('status').filter({ hasText: '2701 readings updated.' }).waitFor();
    assert.equal(refreshRequests.length, 1);
    for (const [status, message] of [[409, 'Refresh already in progress'], [502, 'Refresh failed'], [200, '2701 readings updated.']]) {
      refreshStatus = status;await button.click();
      await page.getByRole('status').filter({ hasText: message }).waitFor();
      assert.equal(await page.locator('.room-card').count(), 7);
    }
    assert.ok(refreshRequests.every(request => request.url === '/api/hassio_ingress/test/api/refresh/2701' && request.header === 'Dashboard'));
    await page.unroute('**/api/hassio_ingress/test/');
  });
  await check('no browser errors or device writes', () => { assert.deepEqual(errors, []); assert.deepEqual(writes, []); });
  await browser.close(); await new Promise(resolve => server.close(resolve));
  console.log(`${failures.length} failed checks`); if (failures.length) process.exitCode = 1;
}
main().catch(error => { console.error(error); process.exit(1); });

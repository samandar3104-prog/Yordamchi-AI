import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

// usage: node render.mjs <outDir> [t1,t2,...]   (no times = full 30fps render)
const out = process.argv[2] || 'frames';
const only = process.argv[3] ? process.argv[3].split(',').map(Number) : null;
const FPS = 30, DUR = 10.43;
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => console.log('[err]', e.message));
await page.goto('http://127.0.0.1:8765/' + (process.env.PAGE || 'index.html'));
await page.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
await page.evaluate(() => document.fonts.ready);

const times = only ?? Array.from({ length: Math.ceil(DUR * FPS) }, (_, i) => i / FPS);
for (let i = 0; i < times.length; i++) {
  await page.evaluate(t => window.renderAt(t), times[i]);
  const name = only ? `t_${times[i].toFixed(2)}.jpg` : `f${String(i).padStart(4, '0')}.jpg`;
  await page.screenshot({ path: `${out}/${name}`, type: 'jpeg', quality: 93 });
  if (i % 30 === 0) console.log('frame', i, '/', times.length);
}
await browser.close();

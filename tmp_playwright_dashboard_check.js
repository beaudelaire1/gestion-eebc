const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  await context.addCookies([
    {
      name: 'sessionid',
      value: 'ynz9j898okwjgr1090q1ekj5r0n4x7gx',
      url: 'http://127.0.0.1:8000',
      path: '/',
      httpOnly: true,
      sameSite: 'Lax'
    }
  ]);

  const page = await context.newPage();
  const consoleMessages = [];
  const pageErrors = [];

  page.on('console', message => {
    consoleMessages.push(`${message.type()}: ${message.text()}`);
  });

  page.on('pageerror', error => {
    pageErrors.push(error.message);
  });

  const response = await page.goto('http://127.0.0.1:8000/app/finance/?year=2025', {
    waitUntil: 'networkidle'
  });

  const diagnostics = await page.evaluate(() => {
    const chartCanvas = document.getElementById('donationsChart');
    const expensesCanvas = document.getElementById('expensesChart');
    const getCanvasInfo = canvas => {
      if (!canvas) {
        return null;
      }
      const rect = canvas.getBoundingClientRect();
      const ctx = canvas.getContext('2d');
      const sample = ctx.getImageData(0, 0, Math.min(canvas.width || 1, 50), Math.min(canvas.height || 1, 50)).data;
      let nonTransparentPixels = 0;
      for (let index = 3; index < sample.length; index += 4) {
        if (sample[index] !== 0) {
          nonTransparentPixels += 1;
        }
      }
      return {
        width: canvas.width,
        height: canvas.height,
        rectWidth: rect.width,
        rectHeight: rect.height,
        nonTransparentPixels,
      };
    };

    return {
      chartDefined: typeof window.Chart !== 'undefined',
      chartInstances: typeof window.Chart !== 'undefined' ? Object.keys(window.Chart.instances || {}).length : 0,
      donationsScriptData: document.getElementById('donations-data')?.textContent,
      donationsCanvas: getCanvasInfo(chartCanvas),
      expensesCanvas: getCanvasInfo(expensesCanvas),
      donationsStats: chartCanvas?.closest('.card')?.querySelector('.row.mt-3')?.innerText || null,
    };
  });

  console.log(JSON.stringify({
    status: response?.status(),
    diagnostics,
    consoleMessages,
    pageErrors,
  }, null, 2));

  await browser.close();
})();

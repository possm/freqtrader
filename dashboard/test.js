import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('pageerror', err => {
    console.error('Page error:', err);
  });
  page.on('console', msg => {
    if (msg.type() === 'error') console.error('Console error:', msg.text());
  });
  await page.goto('http://192.168.2.4:80'); 
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: 'screenshot.png' });
  await browser.close();
})();

import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('pageerror', err => {
    console.error('Page error:', err.message);
  });
  page.on('console', msg => {
    if (msg.type() === 'error') console.error('Console error:', msg.text());
  });
  await page.goto('http://192.168.2.4:80'); 
  await new Promise(r => setTimeout(r, 1000));
  
  // Type in the form
  await page.type('input[placeholder="Wolf Custom Swing"]', 'TestBot');
  
  // Click Connect
  await page.click('button[type="submit"]');
  
  await new Promise(r => setTimeout(r, 3000));
  await page.screenshot({ path: 'screenshot2.png' });
  await browser.close();
})();

const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('LOG:', msg.text()));
  await page.goto('http://192.168.2.4/');
  await new Promise(r => setTimeout(r, 2000));
  
  await page.evaluate(() => {
    console.log("Found:", document.querySelectorAll('div[title="Chart"]').length);
  });
  await browser.close();
})();

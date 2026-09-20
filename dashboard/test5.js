import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('http://192.168.2.4:80'); 
  await new Promise(r => setTimeout(r, 1000));
  
  await page.type('input[placeholder="Wolf Custom Swing"]', 'TestBot');
  await page.type('input[type="password"]', 'freqtrader');
  await page.click('button[type="submit"]');
  
  await new Promise(r => setTimeout(r, 3000));
  const rootHtml = await page.evaluate(() => document.getElementById('root').innerHTML);
  console.log("Root innerHTML length:", rootHtml.length);
  console.log("Root innerHTML:", rootHtml);
  await browser.close();
})();

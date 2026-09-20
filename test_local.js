const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('LOG:', msg.text()));
  page.on('pageerror', err => console.log('ERROR:', err.toString()));
  await page.goto('http://127.0.0.1/');
  await new Promise(r => setTimeout(r, 2000));
  
  await page.evaluate(() => {
    const inputs = document.querySelectorAll('input');
    const setVal = (el, val) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(el, val);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    };
    if (inputs.length >= 3) {
      setVal(inputs[1], 'http://127.0.0.1:8080'); // the backend proxy handles this!
      setVal(inputs[2], 'freqtrader');
      setVal(inputs[3], 'freqtrader');
      const btn = document.querySelector('button');
      if(btn) btn.click();
    }
  });
  await new Promise(r => setTimeout(r, 4000));
  
  await page.evaluate(() => {
    const btns = Array.from(document.querySelectorAll('button'));
    const btn = btns.find(b => b.textContent.includes('Chart') || b.title === 'Chart');
    if(btn) btn.click();
  });
  await new Promise(r => setTimeout(r, 4000));
  await page.screenshot({ path: 'local_chart_real.png' });
  await browser.close();
})();

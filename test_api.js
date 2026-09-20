const crypto = require('crypto');
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('response', async res => {
    if (res.url().includes('pair_candles')) {
      console.log('--- pair_candles response ---');
      console.log('URL:', res.url());
      console.log('Status:', res.status());
      try {
        const json = await res.json();
        console.log('Data columns:', json.columns || 'none');
        console.log('Rows count:', json.data ? json.data.length : '0');
        if (json.data && json.data.length > 0) {
           console.log('First row length:', json.data[0].length);
        }
      } catch (e) {
        console.log('Failed to parse json');
      }
    }
  });

  await page.goto('http://192.168.2.4/');
  await new Promise(r => setTimeout(r, 2000));
  
  await page.evaluate(() => {
    const inputs = document.querySelectorAll('input');
    const setVal = (el, val) => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(el, val);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    };
    if (inputs.length >= 3) {
      setVal(inputs[1], 'http://192.168.2.4:8080');
      setVal(inputs[2], 'freqtrader');
      setVal(inputs[3], 'freqtrader');
      const btn = document.querySelector('button');
      if(btn) btn.click();
    }
  });
  
  await new Promise(r => setTimeout(r, 4000));
  
  // click Chart tab
  await page.evaluate(() => {
    const btn = document.querySelector('div[title="Chart"]');
    if(btn) btn.click();
  });
  
  await new Promise(r => setTimeout(r, 4000));
  
  // change timeframe
  await page.evaluate(() => {
    const selects = document.querySelectorAll('.segmented span');
    for (let s of selects) {
      if (s.textContent.includes('5m')) s.click();
    }
  });
  
  await new Promise(r => setTimeout(r, 4000));
  await browser.close();
})();

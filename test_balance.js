import fetch from 'node-fetch';
(async () => {
  const auth = 'Basic ' + Buffer.from('freqtrader:freqtrader').toString('base64');
  const res = await fetch('http://127.0.0.1:8080/api/v1/balance', {
    headers: { 'Authorization': auth }
  });
  const data = await res.json();
  console.log(JSON.stringify(data, null, 2));
})();

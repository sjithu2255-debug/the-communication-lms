const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('LOG:', msg.text()));
  page.on('pageerror', err => console.log('ERR:', err.toString()));
  
  await page.goto('file:///Users/jithusreekumar111gmail.com/thecommunciationgym/The-communication-gym/english-conversationally.html');
  await page.waitForTimeout(1000);
  await browser.screenshot({ path: 'screenshot.png' });
  await browser.close();
})();

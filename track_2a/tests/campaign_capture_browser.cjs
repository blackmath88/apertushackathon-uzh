// Usage: python3 tests/campaign_capture_fixture_server.py 8767 & node tests/campaign_capture_browser.cjs http://127.0.0.1:8767 OUT_DIR
const {chromium}=require('playwright');
const fs=require('node:fs');
const url=process.argv[2],out=process.argv[3];
if(!url||!out)throw Error('Usage: node campaign_capture_browser.cjs URL OUTPUT_DIR');
fs.mkdirSync(out,{recursive:true});
(async()=>{
const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']});
const errors=[];
for(const [name,viewport] of [['desktop',{width:1440,height:1050}],['mobile',{width:390,height:844}]]){
  const p=await browser.newPage({viewport});p.on('pageerror',e=>errors.push(name+': '+e.message));
  await p.goto(url);await p.getByRole('button',{name:'Open campaign →'}).first().click();await p.getByRole('button',{name:'Scope',exact:true}).click();
  const row=p.locator('#preparation [data-family="fam1"]');await row.waitFor();
  if(await row.locator('[data-status]').getAttribute('data-status')!=='not_captured'&&name==='desktop')throw Error('initial status');
  if(name==='desktop'){
    await row.getByRole('button',{name:'Capture fixture evidence'}).click(); // uncertified: must be refused, nothing captured
    await p.locator('#error:not([hidden])').waitFor();
    await row.getByLabel('Reviewer').fill('Fixture reviewer');await row.getByLabel('Pairing rationale').fill('Authored fixture pair');await row.getByLabel('Rights basis').fill('Project-authored fixture');
    await row.getByLabel(/I certify/).check();await row.getByRole('button',{name:'Capture fixture evidence'}).click();
    await p.locator('#preparation [data-status="captured"]').waitFor();
  }
  // reload persistence: state comes from the server, not the page
  await p.reload();await p.getByRole('button',{name:'Open campaign →'}).first().click();await p.getByRole('button',{name:'Scope',exact:true}).click();
  await p.locator('#preparation [data-status="captured"]').waitFor();
  await p.getByText(/Live original \(left\)/).waitFor();await p.getByText(/Captured evidence \(left\): sha256:/).waitFor();
  const overflow=await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
  if(overflow)throw Error(name+': horizontal overflow');
  await p.screenshot({path:`${out}/capture-${name}.png`,fullPage:true});await p.close();
}
await browser.close();
if(errors.length)throw Error(errors.join('\n'));
console.log('capture preparation browser check passed');
})();

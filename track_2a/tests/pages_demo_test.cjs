// Exercise the shipped JS using a small DOM contract; not rendered-browser acceptance.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(process.argv[2]+'/index.html','utf8');
const fixture=html.match(/id="fixture">([\s\S]*?)<\/script>/)[1];
class Element{constructor(tag,text=''){this.tag=tag;this.textContent=text;this.children=[];this.value='';this.classList={add:()=>{}};this.dataset={};}append(...xs){this.children.push(...xs);}replaceChildren(...xs){this.children=xs;}setAttribute(k,v){this[k]=v;}click(){this.onclick?.();}addEventListener(){}showModal(){this.open=true;}close(){this.open=false;}}
const nodes={};for(const id of ['fixture','view','navigation','breadcrumb','error'])nodes['#'+id]=new Element('div');nodes['#fixture'].textContent=fixture;
let stored;const preferences=new Map();const body=new Element('body');const context=vm.createContext({document:{getElementById:id=>nodes['#'+id],querySelector:s=>nodes[s]||walk(body).find(n=>s==='#'+n.id),body,createTextNode:t=>new Element('text',t),createElement:t=>new Element(t)},localStorage:{getItem:k=>k==='lost-in-switzerland:guidance:v1'?preferences.get(k):stored,setItem:(k,v)=>{if(k==='lost-in-switzerland:guidance:v1')preferences.set(k,v);else stored=v;},removeItem:()=>{stored=null}},window:{scrollTo:()=>{}},crypto:require('node:crypto').webcrypto,structuredClone,console,Blob,URL,setTimeout:()=>{},confirm:()=>true});
vm.runInContext(fs.readFileSync(process.argv[2]+'/app.js','utf8'),context);
function walk(n){return [n,...n.children.flatMap(walk)];}
function click(text){const b=walk(nodes['#view']).find(n=>n.tag==='button'&&n.textContent===text);assert.ok(b,text);b.click();}
click('Set scope');click('Load authored findings →');
assert.equal(JSON.parse(stored).cases[0].loaded,true);
assert.ok(walk(nodes['#view']).some(n=>n.textContent==='Different deadlines'));
const form=walk(nodes['#view']).find(n=>n.tag==='form'),elements=walk(form);
elements.find(n=>n.tag==='input').value='Demo reviewer';elements.find(n=>n.tag==='textarea').value='The stated number of days differs.';elements.find(n=>n.tag==='select').value='confirmed';
form.onsubmit({preventDefault(){}});
assert.equal(JSON.parse(stored).cases[0].reviews[0].state,'confirmed');
click('Continue to report →');
const report=walk(nodes['#view']).find(n=>n.tag==='pre').textContent;
assert.match(report,/Authored examples only/);assert.match(report,/Demo reviewer/);assert.match(report,/Model calls: 0/);
// Reload preserves the review and doesn't require a network API.
vm.runInContext('render()',context);assert.equal(JSON.parse(stored).cases[0].reviews.length,1);
console.log('Pages scope → authored findings → review → report: passed (DOM contract only)');

click('Theatre');click('Preview Apertus workflow');click('Next event');
assert.ok(walk(nodes['#view']).some(n=>n.textContent==='ILLUSTRATED PREVIEW · NO EXECUTION'));
assert.equal(JSON.parse(stored).cases[0].reviews.length,1);
click('Show recorded activity');
assert.ok(walk(nodes['#view']).some(n=>n.textContent==='CASE ACTIVITY · 0 MODEL CALLS'));
click('‹ All cases');
const createForm=walk(nodes['#view']).find(n=>n.tag==='form');
walk(createForm).find(n=>n.tag==='input').value='Second investigation';
createForm.onsubmit({preventDefault(){}});
assert.equal(JSON.parse(stored).cases.length,2);
assert.equal(JSON.parse(stored).cases[1].reviews.length,0);
assert.equal(JSON.parse(stored).cases[0].reviews.length,1);
console.log('Case isolation and non-executing theatre preview: passed');

// Tour navigation and preferences cannot mutate the saved case portfolio.
const before=stored;
vm.runInContext("go('Settings'); startGuide()",context);
for(let i=0;i<5;i++)vm.runInContext('guideIndex++;drawGuide()',context);
assert.ok(walk(body).some(n=>n.textContent==='Take the evidence and decisions with you'));
vm.runInContext('dismissGuide()',context);
assert.equal(stored,before);
assert.ok(walk(nodes['#view']).some(n=>n.textContent==='Settings'));
vm.runInContext('guidance.welcome=false;saveGuidance()',context);
assert.equal(JSON.parse(preferences.get('lost-in-switzerland:guidance:v1')).welcome,false);
vm.runInContext('showWelcome()',context);
assert.equal(walk(body).find(n=>n.tag==='input').checked,true);
vm.runInContext('dismissGuide()',context);
assert.equal(stored,before);
console.log('Guidance: six steps, restoration, separate preferences and case preservation passed (DOM contract)');

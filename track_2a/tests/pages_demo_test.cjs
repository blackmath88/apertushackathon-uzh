// Exercise the shipped JS using a small DOM contract; not rendered-browser acceptance.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(process.argv[2]+'/index.html','utf8');
const fixture=html.match(/id="fixture">([\s\S]*?)<\/script>/)[1];
class Element{constructor(tag,text=''){this.tag=tag;this.textContent=text;this.children=[];this.value='';this.classList={add:()=>{}};this.dataset={};}append(...xs){this.children.push(...xs);}replaceChildren(...xs){this.children=xs;}setAttribute(k,v){this[k]=v;}click(){this.onclick?.();}}
const nodes={};for(const id of ['fixture','view','navigation','breadcrumb','error'])nodes['#'+id]=new Element('div');nodes['#fixture'].textContent=fixture;
let stored;const context=vm.createContext({document:{getElementById:id=>nodes['#'+id],querySelector:s=>nodes[s],createElement:t=>new Element(t)},localStorage:{getItem:()=>stored,setItem:(k,v)=>{stored=v},removeItem:()=>{stored=null}},window:{scrollTo:()=>{}},structuredClone,console,Blob,URL,setTimeout:()=>{},confirm:()=>true});
vm.runInContext(fs.readFileSync(process.argv[2]+'/app.js','utf8'),context);
function walk(n){return [n,...n.children.flatMap(walk)];}
function click(text){const b=walk(nodes['#view']).find(n=>n.tag==='button'&&n.textContent===text);assert.ok(b,text);b.click();}
click('Start with the federal directory →');click('Load authored findings →');
assert.equal(JSON.parse(stored).loaded,true);
assert.ok(walk(nodes['#view']).some(n=>n.textContent==='Different deadlines'));
const form=walk(nodes['#view']).find(n=>n.tag==='form'),elements=walk(form);
elements.find(n=>n.tag==='input').value='Demo reviewer';elements.find(n=>n.tag==='textarea').value='The stated number of days differs.';elements.find(n=>n.tag==='select').value='confirmed';
form.onsubmit({preventDefault(){}});
assert.equal(JSON.parse(stored).reviews[0].state,'confirmed');
click('Continue to report →');
const report=walk(nodes['#view']).find(n=>n.tag==='pre').textContent;
assert.match(report,/Authored examples only/);assert.match(report,/Demo reviewer/);assert.match(report,/Model calls: 0/);
// Reload preserves the review and doesn't require a network API.
vm.runInContext('render()',context);assert.equal(JSON.parse(stored).reviews.length,1);
console.log('Pages scope → authored findings → review → report: passed (DOM contract only)');

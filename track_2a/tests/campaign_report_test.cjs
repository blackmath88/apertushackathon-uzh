// Report contract smoke test: exercises the actual UI export function, without a browser dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '../src/uzh_rsd/campaign_center.html'), 'utf8');
const reportFunction = html.split('\n').find(line => line.startsWith('function report(c)'));
assert.ok(reportFunction, 'report export function exists');
const doc = (locale, time) => ({locale, source_url:`https://www.bfe.admin.ch/${locale}/source`, canonical_url:`https://www.bfe.admin.ch/${locale}/final`, retrieved_at_utc:time, sha256_html:'a'.repeat(64), sha256_extract:'b'.repeat(64)});
const c = {
  name:'Authored report test', scope:{site_ids:['bfe'], catalogue_version:'fixture'},
  discovery_runs:[{id:'discovery-1', site_id:'bfe', started_at:'2026-10-15T05:00:00Z', state:'complete', stop_reason:'candidate_budget', summary:{families:1,candidates:2,unvisited:2}}],
  captures:[{id:'failed-capture',at:'2026-10-15T05:01:00Z',status:'failed',blockers:['fetch_failed:right:TimeoutError']}],
  pairs:[{id:'pair-1',title:'Fixture deadline',status:'ready',bundle:{fixture:true,digest:'c'.repeat(64),left:doc('de','2026-10-15T05:02:00Z'),right:doc('fr','2026-10-15T05:02:03Z'),analysis:{status:'not_run',candidates:[]},capture_evidence:{snapshot_id:'snapshot-1',family_id:'family-1',pairing:{status:'CANDIDATE',rationale:'Reviewer assertion'},omission_confirmation:{allowed:false,blockers:['extraction_partial:left']}}}}]
};
const result = vm.runInNewContext(reportFunction + '\nreport(c)', {c});
for (const expected of ['AUTHORED DEMONSTRATION', 'candidate_budget', 'Not visited: 2', 'fetch_failed:right:TimeoutError', 'Analysis: ready', 'Run: no model run recorded', '/de/final', '05:02:00Z', '05:02:03Z', 'snapshot-1', 'BLOCKED: extraction_partial:left', 'not evidence of a fix']) assert.ok(result.includes(expected), expected);
assert.ok(!result.includes('undefined'), 'report should not leak absent-field placeholders');
console.log('PASS actual campaign report function: coverage, failures, individual provenance, no-run state and omission gate');

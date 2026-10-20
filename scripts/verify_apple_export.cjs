// Independent local checks for the Apple collection and offline review viewer.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=process.argv[2];
if(!root)throw new Error('Usage: node verify_apple_export.cjs OUTPUT_DIR');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
const all=read('all_languages_fetched.json'),english=read('english_as_of_2026-10-19.json'),windowRows=read('english_six_months.json'),report=read('collection_report.json');
assert.equal(all.length,1000);assert.equal(windowRows.length,171);assert.equal(english.length,469);
assert.equal(new Set(all.map(r=>r.app_id+':'+r.review_id)).size,all.length);
for(let i=1;i<all.length;i++)assert.ok(all[i-1].review_timestamp_seconds>=all[i].review_timestamp_seconds);
for(const r of windowRows){assert.equal(r.language_status,'english');assert.ok(r.review_timestamp_seconds>=Date.parse('2026-04-19T00:00:00+08:00')/1000);assert.ok(r.review_timestamp_seconds<Date.parse('2026-10-20T00:00:00+08:00')/1000)}
const pageChecks=[];
for(const crawl of report.crawls){const successful=new Map(crawl.pages.filter(p=>p.returned>0).map(p=>[p.page,p]));assert.deepEqual([...successful.keys()].sort((a,b)=>a-b),[1,2,3,4,5,6,7,8,9,10]);assert.equal(crawl.unresolved_empty_pages.length,0);assert.equal(crawl.errors.length,0);for(let page=1;page<10;page++)assert.ok(Date.parse(successful.get(page).earliest_hk)>=Date.parse(successful.get(page+1).latest_hk));pageChecks.push({app:crawl.app,successful_pages:successful.size,returned_per_page:[...successful.values()].map(p=>p.returned),unresolved_empty_pages:0})}
const source=fs.readFileSync(path.join(root,'review_browser.html'),'utf8');
const embedded=JSON.parse(source.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);assert.deepEqual(embedded.reviews,english);
new vm.Script(source.match(/<script>([\s\S]*?)<\/script>/)[1],{filename:'apple_review_browser.html:inline.js'});
assert.equal(report.verification.records_traced_to_original_http,all.length);assert.equal(report.verification.errors.length,0);
const result={all_records:all.length,english_fetched:english.length,english_six_months:windowRows.length,newest_first:true,unique_app_review_ids:true,html_javascript_syntax:'passed',embedded_data_matches_export:true,page_checks:pageChecks};
fs.writeFileSync(path.join(root,'independent_checks.json'),JSON.stringify(result,null,2)+'\n','utf8');console.log(JSON.stringify(result,null,2));

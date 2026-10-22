"""Run real browser interactions on a temporary local copy with a clean profile."""
import json
import re
import subprocess
import tempfile
from pathlib import Path

from feedback_io import dump, load, require, sha

HARNESS = r'''
<script>
(function(){
const checks=[]; const check=(name,ok)=>checks.push({name,passed:!!ok});
const rows=()=>Array.from(document.querySelectorAll('#commentRows tr'));
const keys=()=>rows().map(r=>r.dataset.recordKey);
const set=(id,value)=>{document.getElementById(id).value=value;document.getElementById(id).dispatchEvent(new Event('input',{bubbles:true}));};
const reset=()=>['search','appFilter','ratingFilter','sentimentFilter','themeFilter'].forEach(id=>set(id,''));
function expected(name,records){check(name,JSON.stringify(keys())===JSON.stringify(records.slice(0,60).map(r=>r.record_key)));check(name+' count',document.getElementById('resultCount').textContent.includes('/ '+records.length+' 条'));}
try{
 check('runtime',typeof DATA==='object'); check('monthly',document.querySelectorAll('.month-row').length===DATA.monthly.length);
 const visited=[];let pages=0;
 do{
  rows().forEach(row=>{const r=DATA.comments[visited.length];visited.push(row.dataset.recordKey);
   check('body '+visited.length,row.querySelector('.comment-text').textContent===(r.title||'')+r.text);
   check('time '+visited.length,row.querySelector('time').getAttribute('datetime')===r.review_time_hk);
   check('source '+visited.length,row.cells[6].querySelectorAll('a')[0].getAttribute('href')===r.source_url);
   check('raw '+visited.length,row.cells[6].querySelectorAll('a')[1].getAttribute('href')===r.raw_response_workspace_path);
  });pages++;if(document.getElementById('nextPage').disabled)break;document.getElementById('nextPage').click();
 }while(pages<=Math.ceil(DATA.comments.length/60));
 check('complete ordered pagination',JSON.stringify(visited)===JSON.stringify(DATA.comments.map(r=>r.record_key))&&new Set(visited).size===DATA.comments.length);
 check('page count',pages===Math.max(1,Math.ceil(DATA.comments.length/60)));
 if(pages>1){document.getElementById('prevPage').click();check('previous page',keys()[0]===DATA.comments[(pages-2)*60].record_key);}
 reset();
 for(const app of ['',...DATA.apps.map(a=>a.key)]){
  set('appFilter',app);const ap=DATA.comments.filter(r=>!app||r.app_key===app);expected('app '+app,ap);
  for(const n of ['1','2','3','4','5']){set('ratingFilter',n);expected('rating '+app+n,ap.filter(r=>r.rating===Number(n)));}set('ratingFilter','');
  for(const s of ['negative','neutral','positive']){set('sentimentFilter',s);expected('sentiment '+app+s,ap.filter(r=>r.rating_sentiment===s));}set('sentimentFilter','');
  for(const t of DATA.theme_names){set('themeFilter',t.key);expected('theme '+app+t.key,ap.filter(r=>r.themes.includes(t.key)));}set('themeFilter','');
 }
 reset();for(const word of ['crash','verification','transfer','THE APP','<script>']){set('search',word);expected('search '+word,DATA.comments.filter(r=>[r.text,r.title,...r.theme_labels].join(' ').toLowerCase().includes(word.toLowerCase())));}
 reset();set('ratingFilter','1');set('sentimentFilter','positive');check('contradiction empty',rows().length===0&&!document.getElementById('empty').hidden);
 reset();set('search','zz_no_such_review_8573206');check('no results',rows().length===0);reset();
 if(DATA.comments.length){const r=DATA.comments.find(r=>r.themes.length)||DATA.comments[0];set('appFilter',r.app_key);set('ratingFilter',String(r.rating));set('sentimentFilter',r.rating_sentiment);set('themeFilter',r.themes[0]||'');set('search',r.text.slice(0,12));expected('combined',DATA.comments.filter(x=>x.app_key===r.app_key&&x.rating===r.rating&&x.rating_sentiment===r.rating_sentiment&&(!r.themes.length||x.themes.includes(r.themes[0]))&&[x.text,x.title,...x.theme_labels].join(' ').toLowerCase().includes(r.text.slice(0,12).toLowerCase())));}
 reset();check('no external resource downloads',performance.getEntriesByType('resource').length===0);
 check('no page horizontal overflow',document.documentElement.scrollWidth<=innerWidth+1);
 const d=document.createElement('div');d.innerHTML=esc('<img src=x onerror=alert(1)>');check('text escaping',d.childElementCount===0);
}catch(error){checks.push({name:'runtime error',passed:false,detail:String(error.stack||error)});}
const result={checks_run:checks.length,successful:checks.every(c=>c.passed),failed:checks.filter(c=>!c.passed),viewport:{width:innerWidth,height:innerHeight},checks};
const out=document.createElement('script');out.id='browserTestResults';out.type='application/json';out.textContent=JSON.stringify(result);document.body.appendChild(out);
})();</script>
'''


def run(root, browser=None):
    if browser is None:
        candidates = [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                      Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")]
        browser = next((p for p in candidates if p.is_file()), None)
    require(browser is not None and browser.is_file(), "Specify an installed Chromium-family executable using --browser")
    document = (root / "report_customer_feedback.html").read_text(encoding="utf-8")
    cache = root / ".cache"
    cache.mkdir(exist_ok=True)
    # Local HTML has no relative runtime assets; source links are inspected but
    # never clicked. Temporary copies may be tested without relocating evidence.
    with tempfile.TemporaryDirectory(prefix="skill_browser_", dir=cache) as temp:
        folder = Path(temp).resolve()
        require(folder.is_relative_to(cache.resolve()), "Scratch path left intended cache")
        target = folder / "test.html"
        target.write_text(document.replace("</body>", HARNESS + "</body>"), encoding="utf-8")
        common = [str(browser), "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--disable-background-networking", "--disable-component-update", "--disable-sync", "--force-device-scale-factor=1",
            "--window-size=1440,1000", f"--user-data-dir={folder / 'profile'}"]
        process = subprocess.run(common + ["--dump-dom", "--virtual-time-budget=2000", target.as_uri()], capture_output=True, timeout=55)
        text = process.stdout.decode("utf-8", errors="replace")
        match = re.search(r'<script id="browserTestResults" type="application/json">(.*?)</script>', text, re.S)
        require(match, f"Browser returned no result; exit={process.returncode}; {process.stderr.decode(errors='replace')[-600:]}")
        result = json.loads(match.group(1))
        result.update(browser=str(browser), browser_exit_code=process.returncode,
            report_sha256=sha(root / "report_customer_feedback.html"), mode="local file, clean headless profile")
        screenshots = []
        for name, section in (("overview", ""), ("themes", "themes"), ("comments", "comments")):
            shot_page = root / "report_customer_feedback.html"
            if section:
                shot_page = folder / (section + ".html")
                style = '<style>header,nav,footer,main>section:not(#' + section + '){display:none!important}</style>'
                shot_page.write_text(document.replace("</head>", style + "</head>"), encoding="utf-8")
            output = root / "screenshots" / (name + ".png")
            output.parent.mkdir(exist_ok=True)
            shot = subprocess.run(common + [f"--screenshot={output}", "--virtual-time-budget=2000", shot_page.as_uri()], capture_output=True, timeout=45)
            screenshots.append({"file": output.relative_to(root).as_posix(), "saved": output.is_file() and output.stat().st_size > 0, "exit_code": shot.returncode})
        result["screenshots"] = screenshots
        result["successful"] = bool(result["successful"] and process.returncode == 0 and all(s["saved"] and s["exit_code"] == 0 for s in screenshots))
    dump(root / "browser_test_results.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}, ensure_ascii=False, indent=2))
    require(result["successful"], "Browser checks failed; inspect result JSON")
    return result

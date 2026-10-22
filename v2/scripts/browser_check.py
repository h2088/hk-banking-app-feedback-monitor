"""Exercise the delivered V2 HTML in real headless Edge and save screenshots."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
from feedback_io import dump, load, now, sha

HARNESS = r'''
let count=0, failures=[];
function assert(x,label){count++;if(!x)failures.push(label)}
function choose(id,value){$(id).value=value;$(id).dispatchEvent(new Event(id==="searchFilter"?"input":"change"))}
function reset(){ $("resetFilters").click() }
function expected(){const s=$("storeFilter").value,b=$("bankFilter").value,se=$("sentimentFilter").value,ra=$("ratingFilter").value,t=$("themeFilter").value,q=$("searchFilter").value.trim().toLowerCase();return EXPECTED.filter(r=>r.platform===s&&(!b||r.app_key===b)&&(!se||r.rating_sentiment===se)&&(!ra||r.rating===Number(ra))&&(!t||(t==="unclassified"?r.themes.length===0:r.themes.includes(t)))&&(!q||((r.title||"")+"\n"+r.text).toLowerCase().includes(q)))}
function checkView(label){let e=expected();let actual=[...$("reviewList").querySelectorAll("article")];assert(actual.length===Math.min(25,e.length),label+" first page count");assert($("resultCount").textContent.startsWith(e.length+" matching"),label+" result count");assert(actual.map(n=>n.dataset.key).join("|")===e.slice(0,25).map(r=>r.record_key).join("|"),label+" ordered IDs")}
try {
assert(document.documentElement.lang==="en","English document language");
for(const store of ["Google Play","Apple App Store"]){
 reset();choose("storeFilter",store);
 const group=EXPECTED.filter(r=>r.platform===store);
 assert($("overviewTitle").textContent.startsWith(store),store+" title");
 [...$("cards").children].forEach((card,i)=>{
   const key=APP_KEYS[i],rows=group.filter(r=>r.app_key===key),n=rows.length,mean=n?rows.reduce((a,r)=>a+r.rating,0)/n:null,low=rows.filter(r=>r.rating<=2).length;
   assert(card.querySelector(".score").firstChild.textContent===(mean===null?"N/A":mean.toFixed(2)),store+key+" mean");
   assert(card.textContent.includes(n+" English reviews"),store+key+" denominator");
   assert(card.querySelector(".measure strong").textContent===(n?(100*low/n).toFixed(1)+"%":"N/A"),store+key+" low share");
 });
 const ds=DATA.deltas.filter(d=>d.platform===store);assert($("comparisons").children.length===2,store+" two benchmarks");
 ds.forEach((d,i)=>{const p=group.filter(r=>r.app_key==="sc_mobile"),b=group.filter(r=>APP_NAMES[r.app_key]===d.benchmark);const gap=100*(p.filter(r=>r.rating<=2).length/p.length-b.filter(r=>r.rating<=2).length/b.length);assert(Math.abs(gap-d.low_star_rate_difference_percentage_points)<0.0002,store+d.benchmark+" independent gap");assert($("comparisons").children[i].textContent.includes(d.benchmark),store+" benchmark label")});
 assert($("themeBody").children.length===11,store+" eleven topics");
 Object.keys(DATA.theme_names).forEach((theme,index)=>APP_KEYS.forEach((key,col)=>{const rows=group.filter(r=>r.app_key===key),hit=rows.filter(r=>r.themes.includes(theme)),td=$("themeBody").children[index].children[col+1];assert(td.firstChild.textContent===hit.length+" / "+rows.length+" · "+(rows.length?(100*hit.length/rows.length).toFixed(1)+"%":"N/A"),store+key+theme+" topic count and denominator")}));
 assert($("monthlyBody").children.length===7,store+" seven monthly buckets");
 for(let m=4;m<=10;m++)APP_KEYS.forEach((key,col)=>{const month="2026-"+String(m).padStart(2,"0"),rows=group.filter(r=>r.app_key===key&&r.review_time_hk.startsWith(month)),low=rows.filter(r=>r.rating<=2).length,td=$("monthlyBody").children[m-4].children[col+1];assert(td.firstChild.textContent===(rows.length?(100*low/rows.length).toFixed(1)+"%":"N/A"),store+key+month+" monthly share")});
 // Traverse every unfiltered page and check each source field in the browser.
 const seen=[];do{const nodes=[...$("reviewList").querySelectorAll("article")];for(const node of nodes){const r=EXPECTED.find(x=>x.record_key===node.dataset.key);assert(!!r,store+" known ID");if(r){assert(node.querySelector(".review-body").textContent===r.text,r.record_key+" exact body");assert((node.querySelector(".review-title")?.textContent||"")===(r.title||""),r.record_key+" exact title");assert(node.querySelector("a").href===r.source_url,r.record_key+" source URL");assert(node.querySelector(".review-meta").textContent.includes(r.review_time_hk.replace("T"," ").replace("+08:00"," HKT")),r.record_key+" time");seen.push(r.record_key)}}if($("nextPage").disabled)break;$("nextPage").click()}while(seen.length<EXPECTED.length+25);
 assert(seen.join("|")===group.map(r=>r.record_key).join("|"),store+" all pages newest first without omissions");reset();
 for(const b of APP_KEYS){choose("bankFilter",b);checkView(store+" bank "+b)}reset();
 for(const r of ["1","2","3","4","5"]){choose("ratingFilter",r);checkView(store+" rating "+r)}reset();
 for(const s of ["negative","neutral","positive"]){choose("sentimentFilter",s);checkView(store+" sentiment "+s)}reset();
 for(const t of [...Object.keys(DATA.theme_names),"unclassified"]){choose("themeFilter",t);checkView(store+" topic "+t)}reset();
 for(const q of ["login","card","GOOD","no-match-unique-123456789"]){choose("searchFilter",q);checkView(store+" search "+q)}reset();
 choose("bankFilter","bochk");choose("sentimentFilter","negative");choose("themeFilter","login_authentication_access");choose("ratingFilter","1");checkView(store+" combined");reset();
 choose("searchFilter","no-match-unique-123456789");assert($("reviewList").querySelector(".empty")!==null,store+" empty message");assert($("prevPage").disabled&&$("nextPage").disabled,store+" empty page controls");reset();
 assert(document.documentElement.scrollWidth<=innerWidth,store+" desktop no horizontal overflow");
}
// Source comments are untrusted: markup must remain literal text.
const attack={...DATA.rows[0],record_key:"synthetic:escaping",text:'escaping-probe <img src=x onerror="window.__attack=1">',title:'<svg onload="window.__attack=1">',themes:[],theme_labels:[]};DATA.rows.unshift(attack);choose("storeFilter",attack.platform);choose("searchFilter","escaping-probe");assert($("reviewList").querySelector(".review-body").textContent===attack.text,"literal untrusted body");assert($("reviewList").querySelector(".review-title").textContent===attack.title,"literal untrusted title");assert(!$("reviewList").querySelector("img,svg,script")&&!window.__attack,"no injected elements or execution");DATA.rows.shift();reset();
assert(performance.getEntriesByType("resource").length===0,"zero network subresources");
}catch(error){failures.push(String(error.stack||error))}
const out=document.createElement("script");out.type="application/json";out.id="browserTestResults";out.textContent=JSON.stringify({passed:failures.length===0,assertions:count,failures,network_subresources:performance.getEntriesByType("resource").length});document.body.append(out);
'''


def main():
    browser = next((p for p in [Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")] if p.exists()), None)
    if browser is None:
        raise RuntimeError("Edge or Chrome required for a real-browser check")
    report = ROOT / "report_customer_feedback_v2.html"
    document = report.read_text(encoding="utf-8")
    expected = load(ROOT / "data/analysis/comment_labels.json")
    fields = ["record_key", "platform", "app_key", "rating", "title", "text", "review_time_hk", "source_url", "rating_sentiment", "themes"]
    encoded = json.dumps([{k:r.get(k) for k in fields} for r in expected], ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    folder = ROOT / "screenshots"
    folder.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hk_v2_browser_") as tmp:
        tmp = Path(tmp)
        base = [str(browser), "--headless=new", "--no-first-run", "--disable-extensions", "--disable-background-networking", "--disable-component-update", "--disable-sync", "--allow-file-access-from-files", "--window-size=1440,1150"]
        test = tmp / "browser_test.html"
        test.write_text(document.replace("</body>", "<script>const EXPECTED=" + encoded + ";\n" + HARNESS + "</script></body>"), encoding="utf-8")
        run = subprocess.run(base + ["--user-data-dir=" + str(tmp/"test_profile"), "--dump-dom", "--virtual-time-budget=2500", test.as_uri()], capture_output=True, timeout=55)
        output = run.stdout.decode("utf-8", errors="replace")
        match = re.search(r'<script type="application/json" id="browserTestResults">(.*?)</script>', output, re.S)
        if not match:
            dump(ROOT / "validation/browser_results.json", dict(passed=False, report_sha256=sha(report), exit_code=run.returncode, stderr=run.stderr.decode("utf-8",errors="replace")[-4000:], reason="No browser test result emitted"))
            raise RuntimeError("Browser did not emit test result")
        results = json.loads(match.group(1))
        results.update(checked_at_utc=now(), browser=str(browser), report_sha256=sha(report), screenshot_hashes={})
        for name, store, focus, width in [("google_play_overview", "Google Play", "overview",1440), ("apple_app_store_overview","Apple App Store","overview",1440), ("apple_comments","Apple App Store","reviews",1440), ("apple_topics","Apple App Store","topics",1440), ("narrow_google_play","Google Play","overview",600)]:
            script = '$("storeFilter").value='+json.dumps(store)+';renderStore();'
            if focus == "reviews":
                script += '$("bankFilter").value="bochk";renderReviews();document.querySelectorAll(".section").forEach(e=>{if(e.id!=="reviewSection")e.style.display="none"});document.querySelector("header").style.padding="16px 24px";'
            if focus == "topics":
                script += 'document.querySelectorAll(".section").forEach(e=>{if(e.id!=="themeSection"&&e.id!=="monthlySection")e.style.display="none"});document.querySelector("header").style.padding="16px 24px";'
            if width == 600:
                script += 'const narrow=document.createElement("script");narrow.id="narrowResults";narrow.type="application/json";narrow.textContent=JSON.stringify({innerWidth,scrollWidth:document.documentElement.scrollWidth});document.body.append(narrow);'
            variant = tmp / (name + ".html")
            variant.write_text(document.replace("</body>","<script>"+script+"</script></body>"),encoding="utf-8")
            image = folder / (name + ".png")
            snap = subprocess.run(base + ["--user-data-dir="+str(tmp/(name+"_profile")), "--window-size="+str(width)+",1150", "--hide-scrollbars", "--screenshot="+str(image), "--virtual-time-budget=2000", variant.as_uri()],capture_output=True,timeout=45)
            assert snap.returncode == 0 and image.exists() and image.stat().st_size > 10000, name
            results["screenshot_hashes"][image.relative_to(ROOT).as_posix()] = sha(image)
            if width == 600:
                narrow_run = subprocess.run(base + ["--user-data-dir="+str(tmp/"narrow_check_profile"), "--window-size=600,1150", "--dump-dom", "--virtual-time-budget=2000", variant.as_uri()],capture_output=True,timeout=45)
                narrow_match = re.search(r'<script id="narrowResults" type="application/json">(.*?)</script>', narrow_run.stdout.decode("utf-8",errors="replace"), re.S)
                assert narrow_match, "Narrow viewport result missing"
                narrow_result = json.loads(narrow_match.group(1))
                # Windows display scaling can make CSS viewport width differ
                # from the requested screenshot width. Validate measured layout.
                assert 320 <= narrow_result["innerWidth"] <= 800 and narrow_result["scrollWidth"] <= narrow_result["innerWidth"], narrow_result
                results["assertions"] += 1
                results["narrow_viewport"] = narrow_result
        # A 430-pixel Edge screenshot was clipped by Edge's minimum layout viewport;
        # replace that generated diagnostic with a measured narrow viewport.
        obsolete = folder / "mobile_google_play.png"
        if obsolete.exists():
            obsolete.unlink()
        dump(ROOT / "validation/browser_results.json", results)
        print(json.dumps(results, ensure_ascii=True), flush=True)
        assert results["passed"], "Real-browser assertion failed"


if __name__ == "__main__":
    main()

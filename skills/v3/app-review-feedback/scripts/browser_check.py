"""Verify combined V3 results and restored monthly chart in a real offline browser."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from feedback_io import dump, load, now, sha

HARNESS = r'''
let count=0,failures=[];
function assert(x,label){count++;if(!x)failures.push(label)}
function choose(id,value){$(id).value=value;$(id).dispatchEvent(new Event(id==="searchFilter"?"input":"change"))}
function reset(){$("resetFilters").click()}
function expected(){const st=$("storeFilter").value,b=$("bankFilter").value,s=$("sentimentFilter").value,r=$("ratingFilter").value,t=$("themeFilter").value,q=$("searchFilter").value.trim().toLowerCase();return EXPECTED.filter(x=>x.platform===st&&(!b||x.app_key===b)&&(!s||x.rating_sentiment===s)&&(!r||x.rating===Number(r))&&(!t||(t==="unclassified"?!x.themes.length:x.themes.includes(t)))&&(!q||((x.title||"")+"\n"+x.text).toLowerCase().includes(q)))}
function checkView(label){const e=expected(),a=[...$("reviewList").querySelectorAll("article")];assert(a.length===Math.min(25,e.length),label+" page size");assert($("resultCount").textContent.startsWith(e.length+" matching"),label+" count");assert(a.map(n=>n.dataset.key).join("|")===e.slice(0,25).map(r=>r.record_key).join("|"),label+" first-page IDs")}
function rate(rows){return rows.length?100*rows.filter(r=>r.rating<=2).length/rows.length:null}
function formatRate(rows){const x=rate(rows);return x===null?"N/A":x.toFixed(1)+"%"}
try{
assert(document.documentElement.lang==="en","English document");
assert(!$("languageFilter"),"No language filter");
assert(!document.querySelector(".language-counts,.language-tag"),"No split-language composition or badges");
assert(DATA.rows.length===EXPECTED.length&&EXPECTED.length===DATA.summary.included_records,"All selected source records embedded");
assert(!DATA.scopes&&!DATA.config.language_scopes,"No language scopes");
for(const name of ["groups","themes","monthly","deltas"])assert(DATA[name].every(r=>!Object.hasOwn(r,"language_scope")),name+" combined grouping");
const chartSignatures=[];
for(const store of ["Google Play","Apple App Store"]){
 reset();choose("storeFilter",store);
 const group=EXPECTED.filter(r=>r.platform===store),label=store;
 assert($("overviewTitle").textContent===store+" · Customer feedback overview",label+" heading");
 [...$("cards").children].forEach((card,i)=>{const key=APP_KEYS[i],rows=group.filter(r=>r.app_key===key),mean=rows.length?rows.reduce((a,r)=>a+r.rating,0)/rows.length:null;
  assert(card.querySelector(".review-count").textContent===rows.length+" reviews",label+key+" denominator");
  assert(card.querySelector(".score").firstChild.textContent===(mean===null?"N/A":mean.toFixed(2)),label+key+" mean");
  assert(card.querySelector(".measure strong").textContent===formatRate(rows),label+key+" low-star share");
 });
 assert($("comparisons").children.length===APP_KEYS.length-1,label+" configured benchmarks");
 DATA.apps.filter(a=>a.role==="benchmark").forEach((app,i)=>{const key=app.key,p=group.filter(r=>r.app_key===PRIMARY.key),b=group.filter(r=>r.app_key===key),gap=p.length&&b.length?rate(p)-rate(b):null,d=DATA.deltas.find(x=>x.platform===store&&x.benchmark_key===key);assert(gap===null?d.low_star_rate_difference_percentage_points===null:Math.abs(gap-d.low_star_rate_difference_percentage_points)<0.0003,label+key+" independent gap");assert($("comparisons").children[i].querySelector(".delta").textContent===(gap===null?"N/A":(gap>0?"+":"")+gap.toFixed(1)+" pp"),label+key+" displayed signed gap");assert($("comparisons").children[i].textContent.includes(APP_NAMES[key]),label+key+" benchmark name")});
 assert($("themeBody").children.length===11,label+" 11 topics");
 Object.keys(DATA.theme_names).forEach((theme,i)=>APP_KEYS.forEach((key,col)=>{const rows=group.filter(r=>r.app_key===key),hits=rows.filter(r=>r.themes.includes(theme)),td=$("themeBody").children[i].children[col+1];assert(td.firstChild.textContent===hits.length+" / "+rows.length+" · "+(rows.length?(100*hits.length/rows.length).toFixed(1)+"%":"N/A"),label+key+theme+" topic denominator");assert(td.querySelector("small").textContent===hits.filter(r=>r.rating<=2).length+" low-star mentions",label+key+theme+" topic low-star") }));
 const months=[...$("monthlyChart").querySelectorAll(".month-row")],buckets=DATA.monthly_totals.filter(m=>m.platform===store);
 assert(months.length===buckets.length,label+" dynamic V1 chart months");
 assert($("monthlyBody").children.length===buckets.length,label+" dynamic exact monthly rows");
 const maximum=Math.max(0,...months.map(node=>group.filter(r=>r.review_time_hk.startsWith(node.dataset.month)).length));
 chartSignatures.push(months.map(node=>node.querySelector(".month-total").textContent).join("|"));
 let chartTotal=0;
 for(let index=0;index<buckets.length;index++){
  const bucket=buckets[index].month_hk,members=group.filter(r=>r.review_time_hk.startsWith(bucket)),node=months[index],n=members.length;
  chartTotal+=n;
  assert(node.dataset.month===bucket,label+bucket+" chart month/order");
  assert(node.querySelector(".month-total").textContent===String(n),label+bucket+" total volume");
  assert(node.querySelector(".month-volume-track i").style.width===(maximum?100*n/maximum:0).toFixed(1).replace(/\.0$/,"")+"%",label+bucket+" V1 bar scaled to selected-store maximum");
  assert(node.querySelector(".month-volume-track").getAttribute("aria-label")===bucket+": "+n+" collected reviews",label+bucket+" accessible volume");
  assert(!!node.querySelector(".month-label small")===buckets[index].partial_calendar_month,label+bucket+" partial month marker");
  assert(node.querySelectorAll(".month-bank").length===APP_KEYS.length,label+bucket+" configured banks");
  APP_KEYS.forEach((key,col)=>{
   const rows=members.filter(r=>r.app_key===key),cell=node.querySelector('[data-bank="'+key+'"]'),td=$("monthlyBody").children[index].children[col+1];
   assert(cell.querySelector("b").textContent===APP_NAMES[key],label+key+bucket+" chart bank");
   assert(cell.querySelector(".month-bank-count").textContent===rows.length+" reviews",label+key+bucket+" chart bank count");
   assert(cell.querySelector(".month-bank-rate").textContent===formatRate(rows)+" low-star",label+key+bucket+" chart bank share");
   assert(td.firstChild.textContent===formatRate(rows),label+key+bucket+" exact monthly share");
   assert(td.querySelector("small").textContent.startsWith(rows.filter(r=>r.rating<=2).length+" / "+rows.length+" reviews"),label+key+bucket+" exact monthly denominator");
  });
 }
 assert(chartTotal===group.length,label+" monthly chart reconciles to store sample");
 checkView(label+" initial");
 for(const b of APP_KEYS){choose("bankFilter",b);checkView(label+b)}reset();
 for(const r of ["1","2","3","4","5"]){choose("ratingFilter",r);checkView(label+" rating "+r)}reset();
 for(const s of ["negative","neutral","positive"]){choose("sentimentFilter",s);checkView(label+s)}reset();
 for(const t of [...Object.keys(DATA.theme_names),"unclassified"]){choose("themeFilter",t);checkView(label+t)}reset();
 for(const q of ["login","登入","转账","閃退","GOOD","no-match-123456789"]){choose("searchFilter",q);checkView(label+" query "+q)}reset();
 choose("bankFilter",APP_KEYS.at(-1));choose("ratingFilter","1");choose("themeFilter","login_authentication_access");choose("sentimentFilter","negative");checkView(label+" combined filters");reset();
 choose("searchFilter","no-match-123456789");assert(!!$("reviewList").querySelector(".empty"),label+" empty message");assert($("prevPage").disabled&&$("nextPage").disabled,label+" empty controls");reset();
 const seen=[];
 do{
  for(const node of $("reviewList").querySelectorAll("article")){
   const r=EXPECTED.find(x=>x.record_key===node.dataset.key);assert(!!r,label+" known source ID");
   if(r){assert(node.querySelector(".review-body").textContent===r.text,r.record_key+" exact Unicode body");assert((node.querySelector(".review-title")?.textContent||"")===(r.title||""),r.record_key+" exact Unicode title");assert(node.querySelector("a").href===r.source_url,r.record_key+" source URL");assert(!node.querySelector(".language-tag"),r.record_key+" no language badge");assert(node.querySelector(".review-meta").textContent.includes(r.review_time_hk.replace("T"," ").replace("+08:00"," HKT")),r.record_key+" exact source time");seen.push(r.record_key)}
  }
  if($("nextPage").disabled)break;$("nextPage").click();
 }while(seen.length<EXPECTED.length+25);
 assert(seen.join("|")===group.map(r=>r.record_key).join("|"),label+" all combined comments paginated newest first");reset();
 assert(document.documentElement.scrollWidth<=innerWidth,label+" no page overflow");
}

const attack={...DATA.rows[0],record_key:"synthetic:escaping",text:'中文 literal <img src=x onerror="window.__attack=1">',title:'<svg onload="window.__attack=1">',themes:[],theme_labels:[]};
DATA.rows.unshift(attack);choose("storeFilter",attack.platform);choose("searchFilter","中文 literal");assert($("reviewList").querySelector(".review-body").textContent===attack.text,"literal untrusted body");assert($("reviewList").querySelector(".review-title").textContent===attack.title,"literal untrusted title");assert(!$("reviewList").querySelector("img,svg,script")&&!window.__attack,"source markup cannot execute");DATA.rows.shift();reset();
// Exercise zero denominators and all-zero monthly bars in memory, without changing source data.
const saved=DATA.groups.find(x=>x.platform==="Google Play"&&x.app_key===APP_KEYS[0]),old={...saved};Object.assign(saved,{review_count:0,mean_rating:null,negative_rate_rating_1_2:null,negative_count_rating_1_2:0,positive_count_rating_4_5:0});choose("storeFilter","Google Play");assert($("cards").firstChild.querySelector(".score").firstChild.textContent==="N/A","empty mean N/A");assert($("cards").firstChild.querySelector(".measure strong").textContent==="N/A","empty share N/A");Object.assign(saved,old);
const oldMonths=DATA.monthly_totals;DATA.monthly_totals=oldMonths.map(m=>({...m,review_count:0,...Object.fromEntries(APP_KEYS.flatMap(k=>[[k+"_review_count",0],[k+"_low_star_rate",null]]))}));renderMonthly();assert([...$("monthlyChart").querySelectorAll(".month-volume-track i")].every(n=>n.style.width==="0%"),"all-zero months have safe zero-width bars");assert([...$("monthlyChart").querySelectorAll(".month-bank-rate")].every(n=>n.textContent==="N/A low-star"),"empty monthly rates N/A");DATA.monthly_totals=oldMonths;renderStore();
assert(performance.getEntriesByType("resource").length===0,"No network subresources");
}catch(e){failures.push(String(e.stack||e))}
const out=document.createElement("script");out.type="application/json";out.id="browserTestResults";out.textContent=JSON.stringify({passed:!failures.length,assertions:count,failures,network_subresources:performance.getEntriesByType("resource").length});document.body.append(out);
'''


def extract(stdout, element_id):
    match = re.search(r'<script[^>]*id="' + element_id + r'"[^>]*>(.*?)</script>', stdout.decode("utf-8", errors="replace"), re.S)
    assert match, f"Missing browser output: {element_id}"
    return json.loads(match.group(1))


def run(root, browser_path=None):
    root = Path(root).resolve()
    assert not (root / "manifest.json").exists(), "Finalized batch is immutable; use a new audit batch for new browser evidence"
    browser = Path(browser_path) if browser_path else Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    assert browser.is_file(), "Supply an installed Chromium/Edge/Chrome executable with --browser"
    report = root / "report_customer_feedback.html"
    document = report.read_text(encoding="utf-8")
    fields = ["record_key", "platform", "app_key", "rating", "title", "text", "review_time_hk", "source_url", "rating_sentiment", "themes", "analysis_language"]
    expected = json.dumps([{k: r.get(k) for k in fields} for r in load(root / "data/analysis/comment_labels.json")], ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    folder = root / "screenshots"
    folder.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hk_feedback_browser_") as temp:
        temp = Path(temp)
        base = [str(browser), "--headless=new", "--no-first-run", "--disable-extensions", "--disable-background-networking", "--disable-component-update", "--disable-sync", "--allow-file-access-from-files"]
        test = temp / "browser_test.html"
        test.write_text(document.replace("</body>", "<script>const EXPECTED=" + expected + ";\n" + HARNESS + "</script></body>"), encoding="utf-8")
        process = subprocess.run(base + ["--user-data-dir=" + str(temp / "test_profile"), "--window-size=1440,1150", "--dump-dom", "--virtual-time-budget=2500", test.as_uri()], capture_output=True, timeout=55)
        try:
            results = extract(process.stdout, "browserTestResults")
        except Exception:
            dump(root / "validation/browser_results.json", dict(passed=False, report_sha256=sha(report), reason="No browser result", stderr=process.stderr.decode("utf-8", errors="replace")[-3000:]))
            raise
        results.update(checked_at_utc=now(), browser=str(browser), report_sha256=sha(report), screenshot_hashes={})
        dump(root / "validation/browser_results.json", results)
        assert results["passed"], results["failures"][:20]
        print(json.dumps(dict(passed=True, assertions=results["assertions"])), flush=True)
        views = [
            ("google_play_combined", "Google Play", "overview", 1440),
            ("apple_combined", "Apple App Store", "overview", 1440),
            ("google_monthly_feedback", "Google Play", "monthly", 1440),
            ("apple_monthly_feedback", "Apple App Store", "monthly", 1440),
            ("combined_comments", "Apple App Store", "reviews", 1440),
            ("narrow_google_play", "Google Play", "overview", 600),
            ("narrow_monthly_feedback", "Google Play", "monthly", 600),
        ]
        for name, store, focus, width in views:
            script = '$("storeFilter").value=' + json.dumps(store) + ';renderStore();'
            if focus in {"monthly", "reviews"}:
                section = "monthlySection" if focus == "monthly" else "reviewSection"
                script += 'document.querySelectorAll(".section").forEach(e=>{if(e.id!==' + json.dumps(section) + ')e.style.display="none"});document.querySelector("header").style.padding="16px 24px";'
            script += 'const n=document.createElement("script");n.id="layoutResults";n.type="application/json";n.textContent=JSON.stringify({innerWidth,scrollWidth:document.documentElement.scrollWidth,chartRows:$("monthlyChart").querySelectorAll(".month-row").length,commentKeys:[...$("reviewList").querySelectorAll("article")].map(n=>n.dataset.key)});document.body.append(n);'
            variant = temp / (name + ".html")
            variant.write_text(document.replace("</body>", "<script>" + script + "</script></body>"), encoding="utf-8")
            picture = folder / (name + ".png")
            snap = subprocess.run(base + ["--user-data-dir=" + str(temp / (name + "_profile")), f"--window-size={width},1150", "--hide-scrollbars", "--screenshot=" + str(picture), "--dump-dom", "--virtual-time-budget=2000", variant.as_uri()], capture_output=True, timeout=45)
            assert snap.returncode == 0 and picture.stat().st_size > 10000, name
            layout = extract(snap.stdout, "layoutResults")
            assert layout["scrollWidth"] <= layout["innerWidth"], (name, layout)
            expected_months = sum(m["platform"] == store for m in load(root / "data/analysis/monthly_feedback_monitoring.json"))
            assert layout["chartRows"] == expected_months
            results.setdefault("layouts", {})[name] = layout
            results["assertions"] += 1
            results["screenshot_hashes"][picture.relative_to(root).as_posix()] = sha(picture)
            print("Saved screenshot " + name, flush=True)
        dump(root / "validation/browser_results.json", results)
        print(json.dumps(dict(passed=True, assertions=results["assertions"], screenshots=len(results["screenshot_hashes"]))))
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--browser")
    args = parser.parse_args()
    run(args.root, args.browser)

"""Test the actual report JS in a clean, headless local Edge/Chrome profile.

No package installation, server, scraping or website navigation is required.
The temporary test copy adds assertions; the deliverable is never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report_customer_feedback_2026-10-19.html"
OUTPUT = ROOT / "data/checkpoint_D_analysis_2026-10-19"

HARNESS = r"""
<script>
(function() {
  const checks = [];
  function check(name, condition, detail) {
    checks.push({name:name, passed:Boolean(condition), detail:detail || ''});
  }
  function set(id, value) {
    const el = document.getElementById(id);
    el.value = value;
    el.dispatchEvent(new Event('input', {bubbles:true}));
  }
  function reset() {
    ['search','appFilter','ratingFilter','sentimentFilter','themeFilter'].forEach(id => set(id, ''));
  }
  function rows() { return Array.from(document.querySelectorAll('#commentRows tr')); }
  function keys() { return rows().map(row => row.dataset.recordKey); }
  function compareVisible(name, expected) {
    check(name, JSON.stringify(keys()) === JSON.stringify(expected.slice(0,60).map(r => r.record_key)));
    check(name + ' count', document.getElementById('resultCount').textContent.includes('/ ' + expected.length + ' 条'));
  }
  try {
    check('actual browser runtime', typeof DATA === 'object' && DATA.comments.length === 311);
    check('monthly bars', document.querySelectorAll('.month-row').length === 7);
    check('theme table populated', document.querySelector('#themes tbody').textContent.includes('28 (28.57%)'));
    check('initial 60 comments', rows().length === 60);
    check('initial pagination', document.getElementById('prevPage').disabled && !document.getElementById('nextPage').disabled);
    check('11 theme filter options', document.getElementById('themeFilter').options.length === 12);
    check('not split by platform', !document.getElementById('platformFilter'));
    const visited = [];
    let page = 0;
    do {
      rows().forEach(row => {
        const expected = DATA.comments[visited.length];
        visited.push(row.dataset.recordKey);
        check('original text ' + visited.length, row.querySelector('.comment-text').textContent === (expected.title || '') + expected.text);
        check('source URL ' + visited.length, row.cells[6].querySelector('a').getAttribute('href') === expected.source_url);
        check('evidence URL ' + visited.length, row.cells[6].querySelectorAll('a')[1].getAttribute('href') === expected.raw_response_workspace_path);
        check('timestamp ' + visited.length, row.querySelector('time').getAttribute('datetime') === expected.review_time_hk);
      });
      page++;
      if (document.getElementById('nextPage').disabled) break;
      document.getElementById('nextPage').click();
    } while (page < 10);
    check('six pages cover all 311', page === 6 && visited.length === 311 && new Set(visited).size === 311);
    check('newest-to-oldest page order', visited.every((key,index) => key === DATA.comments[index].record_key));
    check('last page has 11 rows', rows().length === 11);
    document.getElementById('prevPage').click();
    check('previous page works', rows().length === 60 && keys()[0] === DATA.comments[240].record_key);
    reset();
    for (const app of ['', 'sc_mobile', 'hsbc_hk']) {
      set('appFilter', app);
      const appRows = DATA.comments.filter(r => !app || r.app_key === app);
      compareVisible('app ' + app, appRows);
      check('independent app sample ' + app, appRows.length === (app === 'sc_mobile' ? 98 : app === 'hsbc_hk' ? 213 : 311));
      for (const rating of ['1','2','3','4','5']) {
        set('ratingFilter', rating);
        compareVisible('rating ' + app + '/' + rating, appRows.filter(r => r.rating === Number(rating)));
      }
      set('ratingFilter', '');
      for (const sentiment of ['negative','neutral','positive']) {
        set('sentimentFilter', sentiment);
        const ratings = sentiment === 'negative' ? [1,2] : sentiment === 'neutral' ? [3] : [4,5];
        compareVisible('sentiment ' + app + '/' + sentiment, appRows.filter(r => ratings.includes(r.rating)));
      }
      set('sentimentFilter', '');
      const themes = Array.from(document.getElementById('themeFilter').options).map(o => o.value).filter(Boolean);
      for (const theme of themes) {
        set('themeFilter', theme);
        compareVisible('theme ' + app + '/' + theme, appRows.filter(r => r.themes.includes(theme)));
      }
      set('themeFilter', '');
    }
    reset();
    for (const word of ['crash','verification','transfer','Faster & Easy','THE APP','App stability / performance']) {
      set('search', word);
      const expected = DATA.comments.filter(r => [r.title || '',r.text].concat(r.theme_labels).join(' ').toLowerCase().includes(word.toLowerCase()));
      compareVisible('search ' + word, expected);
    }
    reset();
    set('appFilter', 'sc_mobile'); set('ratingFilter', '1'); set('sentimentFilter', 'negative');
    set('themeFilter','app_stability_performance'); set('search','crash');
    compareVisible('all filters combined', DATA.comments.filter(r => r.app_key === 'sc_mobile' && r.rating === 1 && r.themes.includes('app_stability_performance') && [r.title || '',r.text].join(' ').toLowerCase().includes('crash')));
    set('sentimentFilter','positive');
    check('contradictory filters empty state', rows().length === 0 && !document.getElementById('empty').hidden && document.getElementById('prevPage').disabled && document.getElementById('nextPage').disabled);
    reset();
    set('search', 'zz_no_such_review_827419');
    check('no search results', rows().length === 0 && !document.getElementById('empty').hidden);
    reset();
    check('clear restores first page', rows().length === 60 && keys()[0] === DATA.comments[0].record_key && document.getElementById('prevPage').disabled);
    const specimen = '<img src=x onerror=alert(1)> & "quoted"';
    const escaped = document.createElement('div'); escaped.innerHTML = esc(specimen);
    check('HTML escaping', escaped.childElementCount === 0 && escaped.textContent === specimen);
    check('no report resource downloads', performance.getEntriesByType('resource').length === 0);
    check('desktop no horizontal page overflow', document.documentElement.scrollWidth <= window.innerWidth + 1);
  } catch (error) {
    check('uncaught test/runtime error', false, String(error.stack || error));
  }
  const result = {checks_run: checks.length, passed: checks.filter(c => c.passed).length, failed: checks.filter(c => !c.passed), viewport: {width:innerWidth,height:innerHeight}, mode:'local file, clean headless browser profile', checks:checks};
  const out = document.createElement('script'); out.id = 'browserTestResults'; out.type = 'application/json'; out.textContent = JSON.stringify(result); document.body.appendChild(out);
})();
</script>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", type=Path, default=Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"))
    args = parser.parse_args()
    if not args.browser.is_file():
        parser.error(f"Browser not found: {args.browser}")
    html_doc = REPORT.read_text(encoding="utf-8")
    cache_root = ROOT / ".cache"
    cache_root.mkdir(exist_ok=True)
    # All generated browser state stays in a uniquely named task directory.
    with tempfile.TemporaryDirectory(prefix="checkpoint_E_browser_", dir=cache_root) as temp:
        temp_path = Path(temp).resolve()
        if not temp_path.is_relative_to(cache_root.resolve()):
            raise ValueError("Browser scratch directory escaped intended cache root")
        harness_path = temp_path / "test.html"
        harness_path.write_text(html_doc.replace("</body>", HARNESS + "</body>"), encoding="utf-8")
        common = [str(args.browser), "--headless=new", "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--disable-background-networking", "--disable-component-update", "--disable-sync", "--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=1440,1000", f"--user-data-dir={temp_path / 'profile'}"]
        process = subprocess.run(common + ["--dump-dom", "--virtual-time-budget=2000", harness_path.as_uri()], capture_output=True, timeout=45)
        dom = process.stdout.decode("utf-8", errors="replace")
        match = re.search(r'<script id="browserTestResults" type="application/json">(.*?)</script>', dom, re.S)
        if not match:
            raise RuntimeError(f"Browser produced no test result (exit {process.returncode}): {process.stderr.decode('utf-8', errors='replace')[-2500:]}")
        results = json.loads(match.group(1))
        results["browser"] = str(args.browser)
        results["browser_exit_code"] = process.returncode
        results["report_sha256"] = hashlib.sha256(REPORT.read_bytes()).hexdigest()
        results["browser_version"] = "See executable product version in Checkpoint E"
        screenshots = OUTPUT / "report_test_screenshots"
        screenshots.mkdir(exist_ok=True)
        results["screenshots"] = []
        for name, section in (("desktop_overview.png", ""), ("desktop_themes.png", "themes"), ("desktop_comments.png", "comments")):
            target = screenshots / name
            screenshot_page = REPORT
            if section:
                # Headless screenshots after scrolling can miss composited
                # content. Preview the unmodified section at the top of an
                # equivalent temporary page by hiding its sibling sections.
                screenshot_page = temp_path / f"screenshot_{section}.html"
                focus_style = "<style>header,nav,footer,main>section:not(#" + section + "){display:none!important}</style>"
                screenshot_page.write_text(html_doc.replace("</head>", focus_style + "</head>"), encoding="utf-8")
            shot = subprocess.run(common + [f"--screenshot={target}", "--virtual-time-budget=2000", screenshot_page.as_uri()], capture_output=True, timeout=40)
            results["screenshots"].append({"file": str(target.relative_to(ROOT)), "saved": target.is_file() and target.stat().st_size > 0, "exit_code": shot.returncode})
        result_path = OUTPUT / "report_browser_test_results.json"
        result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key:value for key,value in results.items() if key != "checks"}, ensure_ascii=False, indent=2))
        if results["failed"] or process.returncode != 0 or not all(item["saved"] and item["exit_code"] == 0 for item in results["screenshots"]):
            raise SystemExit(1)


if __name__ == "__main__":
    main()

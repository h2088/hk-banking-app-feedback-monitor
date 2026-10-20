// Local integrity and viewer-JavaScript checks, using only Node's standard library.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = process.argv[2];
const probe = process.argv[3];
if (!root || !probe) throw new Error('Usage: node verify_review_export.cjs FINAL_DIR PROBE_DIR');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const all = read('all_languages_fetched.json');
const english = read('english_as_of_2026-10-19.json');
const windowReviews = read('english_six_months.json');
const report = read('collection_report.json');
const source = fs.readFileSync(path.join(root, 'review_browser.html'), 'utf8');
const embedded = JSON.parse(source.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
assert.deepEqual(embedded.reviews, english);
const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script, {filename: 'review_browser.html:inline.js'});
assert.equal(all.length, 4278);
assert.equal(windowReviews.length, 140);
for (let i = 1; i < all.length; i++) {
  assert.ok(all[i - 1].review_timestamp_seconds >= all[i].review_timestamp_seconds);
}
for (const r of windowReviews) {
  assert.equal(r.language_status, 'english');
  assert.ok(r.review_timestamp_seconds >= Date.parse('2026-04-19T00:00:00+08:00') / 1000);
  assert.ok(r.review_timestamp_seconds < Date.parse('2026-10-20T00:00:00+08:00') / 1000);
}
const localeChecks = [];
for (const [key, appId] of [['sc_mobile', 'com.scb.breezebanking.hk'], ['hsbc_hk', 'hk.com.hsbc.hsbchkmobilebanking']]) {
  const tested = fs.readFileSync(path.join(probe, key, 'reviews_fetched.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  const primary = fs.readFileSync(path.join(root, key, 'reviews_fetched.jsonl'), 'utf8').trim().split('\n').map(JSON.parse).slice(0, tested.length);
  const canonical = rows => rows.map(r => [r.review_id, r.text, r.rating, r.review_timestamp_seconds]);
  const same = JSON.stringify(canonical(primary)) === JSON.stringify(canonical(tested));
  assert.ok(same, 'English locale comparison differs for ' + key);
  localeChecks.push({app_id: appId, compared_reviews: tested.length, same_ordered_ids_text_ratings_timestamps: same,
                     primary_language: primary[0].request_language, probe_language: tested[0].request_language});
}
assert.equal(report.verification.errors.length, 0);
const result = {all_records: all.length, english_all_fetched: english.length,
  english_six_months: windowReviews.length, html_javascript_syntax: 'passed', embedded_data_matches_export: true,
  locale_comparison: localeChecks, statistics: report.statistics};
fs.writeFileSync(path.join(root, 'independent_checks.json'), JSON.stringify(result, null, 2) + '\n', 'utf8');
console.log(JSON.stringify(result, null, 2));

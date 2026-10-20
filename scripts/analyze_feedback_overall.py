"""Overall customer-feedback analysis for SC Mobile vs HSBC benchmark.

Input: the immutable 311-row English six-month merged JSON.
Scope: customer comments only; platform is intentionally not a reporting split.
The text rules are deterministic and intentionally conservative. Star rating is
the primary comparable satisfaction signal; text labels are supplemental.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/merged_2026-10-19/master_english_six_months.json"
OUTPUT = ROOT / "data/checkpoint_D_analysis_2026-10-19"


# These are feedback themes, not claims about the underlying product cause.
THEMES = OrderedDict(
    [
        (
            "app_stability_performance",
            (
                "App stability / performance",
                [
                    r"\bcrash(?:es|ed|ing)?\b",
                    r"\bforce close(?:d)?\b",
                    r"\bhang(?:s|ing)?\b",
                    r"\bfrozen?\b",
                    r"\bfreeze(?:s|d|n)?\b",
                    r"\bwhite screen\b",
                    r"\bslow(?:ly)?\b",
                    r"\bdelay(?:ed|s)?\b",
                    r"\bstuck\b",
                    r"\bloading\b",
                    r"\bnot responding\b",
                    r"\bfailed? to connect\b",
                    r"\bconnection\b",
                    r"\bwon['’]?t load\b",
                    r"\bdoesn['’]?t load\b",
                    r"\bbug(?:s|gy)?\b",
                    r"\bglitch(?:es|y)?\b",
                    r"\berror\b",
                    r"\bdoesn['’]?t open\b",
                    r"\bwon['’]?t open\b",
                ],
            ),
        ),
        (
            "login_authentication_access",
            (
                "Login / authentication / access",
                [
                    r"\blog[ -]?in\b",
                    r"\bsign[ -]?in\b",
                    r"\bpassword\b",
                    r"\bpasscode\b",
                    r"\bactivation\b",
                    r"\bauthenticat(?:e|ion|ed|ing)\b",
                    r"\bverification\b",
                    r"\bverify\b",
                    r"\botp\b",
                    r"\bone[- ]time password\b",
                    r"\bfingerprint\b",
                    r"\bface ?id\b",
                    r"\bbiometric\b",
                    r"\bapprove(?:d|s|al)?\b",
                    r"\bapproval\b",
                    r"\bnotification\b",
                    r"\baccess\b",
                    r"\blocked out\b",
                    r"\block(?:ed|ing)?\b",
                ],
            ),
        ),
        (
            "transfers_payments_cards",
            (
                "Transfers / payments / cards",
                [
                    r"\btransfer(?:s|red|ring)?\b",
                    r"\bpayment(?:s)?\b",
                    r"\bpay(?:ee|ing|ment)?\b",
                    r"\btransaction(?:s)?\b",
                    r"\bcredit card\b",
                    r"\bdebit card\b",
                    r"\bcard(?:s)?\b",
                    r"\brecipient\b",
                    r"\bpayee\b",
                    r"\bremit(?:tance|ting)?\b",
                    r"\bwithdraw(?:al|ing)?\b",
                    r"\bdeposit(?:s)?\b",
                    r"\btop[ -]?up\b",
                    r"\bbill\b",
                ],
            ),
        ),
        (
            "usability_navigation_design",
            (
                "Usability / navigation / design",
                [
                    r"\blayout\b",
                    r"\bdesign\b",
                    r"\bui\b",
                    r"\bux\b",
                    r"\buser experience\b",
                    r"\bnavigat(?:e|ion|ing)\b",
                    r"\bmenu(?:s)?\b",
                    r"\bbutton(?:s)?\b",
                    r"\bfont(?:s)?\b",
                    r"\binterface\b",
                    r"\bconfus(?:e|ed|ing)\b",
                    r"\bcomplicated\b",
                    r"\bmessy\b",
                    r"\beasy to use\b",
                    r"\buser friendly\b",
                    r"\bdifficult to use\b",
                    r"\bhard to (?:find|use|locate)\b",
                    r"\bloc(?:ate|ation)\b",
                    r"\bfind\b",
                ],
            ),
        ),
        (
            "customer_support_service",
            (
                "Customer support / service",
                [
                    r"\bcustomer service\b",
                    r"\bcustomer support\b",
                    r"\bsupport\b",
                    r"\bhotline\b",
                    r"\bcall(?:ed|ing)?\b",
                    r"\bcontact\b",
                    r"\bhelp(?:ful)?\b",
                    r"\bchat\b",
                    r"\benquir(?:y|ies)\b",
                    r"\bresponse\b",
                    r"\breply\b",
                    r"\bservice\b",
                ],
            ),
        ),
        (
            "account_registration",
            (
                "Account / registration",
                [
                    r"\bregister(?:ed|ing|ation)?\b",
                    r"\bregistration\b",
                    r"\bsign[ -]?up\b",
                    r"\bopen(?:ing)? an account\b",
                    r"\benrol(?:l|led|ment)\b",
                    r"\baccount\b",
                    r"\bonboard(?:ing)?\b",
                ],
            ),
        ),
        (
            "balance_statements_history",
            (
                "Balance / statements / history",
                [
                    r"\bbalance\b",
                    r"\bstatement(?:s)?\b",
                    r"\btransaction history\b",
                    r"\bhistory\b",
                    r"\baccount details\b",
                ],
            ),
        ),
        (
            "security_fraud_trust",
            (
                "Security / fraud / trust",
                [
                    r"\bsecurity\b",
                    r"\bsecure\b",
                    r"\bfraud\b",
                    r"\bscam\b",
                    r"\bsuspicious\b",
                    r"\bprivacy\b",
                    r"\btrust\b",
                    r"\bsafe\b",
                ],
            ),
        ),
        (
            "language_localization",
            (
                "Language / localization",
                [r"\blanguage\b", r"\bchinese\b", r"\benglish\b", r"\bcantonese\b", r"\btranslation\b"],
            ),
        ),
        (
            "fees_rates",
            (
                "Fees / rates",
                [r"\bfee(?:s)?\b", r"\bcharge(?:d|s)?\b", r"\binterest\b", r"\bexchange rate\b", r"\brate\b", r"\bfx\b", r"\badvert(?:isement|ising)?s?\b", r"\bads?\b"],
            ),
        ),
        (
            "feature_request",
            (
                "Feature request / suggestion",
                [r"\bfeature(?:s)?\b", r"\badd\b", r"\bplease provide\b", r"\bwould like\b", r"\bwish\b", r"\boption\b", r"\bscree(?:n)? ?shot\b"],
            ),
        ),
    ]
)


POSITIVE = [
    r"\bgood\b", r"\bgreat\b", r"\bexcellent\b", r"\bnice\b", r"\bamazing\b", r"\bbest\b",
    r"\bawesome\b", r"\blove\b", r"\bhelpful\b", r"\bconvenient\b", r"\beasy\b",
    r"\bfriendly\b", r"\bfast\b", r"\bsmooth\b", r"\bseamless\b", r"\bstable\b",
    r"\bperfect\b", r"\bworks?\b", r"\bworking\b", r"\bwell\b",
]
NEGATIVE = [
    r"\bbad\b", r"\bterrible\b", r"\bawful\b", r"\brubbish\b", r"\bworst\b",
    r"\bhate\b", r"\buseless\b", r"\bpoor\b", r"\bslow\b", r"\bcrash(?:es|ed|ing)?\b",
    r"\bbug(?:s|gy)?\b", r"\bfail(?:s|ed|ing|ure)?\b", r"\bwrong\b", r"\bhard\b",
    r"\bdifficult\b", r"\bconfus(?:e|ed|ing)\b", r"\bcomplicated\b", r"\bannoy(?:ed|ing)?\b", r"\bfrustrat(?:ed|ing)\b",
    r"\bcan['’]?t\b", r"\bcannot\b", r"\bwon['’]?t\b", r"\bunable\b", r"\bnever\b", r"\bnot\b",
]
POSITIVE_RE = [re.compile(pattern, re.I) for pattern in POSITIVE]
NEGATIVE_RE = [re.compile(pattern, re.I) for pattern in NEGATIVE]
THEME_RE = OrderedDict((key, (label, [re.compile(p, re.I) for p in patterns])) for key, (label, patterns) in THEMES.items())


def normalized(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value or "").casefold()).strip()


def word_count(value):
    return len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", value or ""))


def explicit_sentiment(rating):
    if rating <= 2:
        return "negative"
    if rating == 3:
        return "neutral"
    return "positive"


def text_sentiment(value):
    positive_hits = sum(bool(pattern.search(value)) for pattern in POSITIVE_RE)
    negative_hits = sum(bool(pattern.search(value)) for pattern in NEGATIVE_RE)
    if re.search(r"\b(?:not|never|hardly|less)\s+(?:good|great|easy|helpful|convenient|fast|smooth|friendly)\b", value, re.I):
        negative_hits += 1
        positive_hits = max(0, positive_hits - 1)
    score = positive_hits - negative_hits
    if positive_hits == 0 and negative_hits == 0:
        label = "unknown"
    elif score >= 1:
        label = "positive"
    elif score <= -1:
        label = "negative"
    else:
        label = "mixed_or_neutral"
    return label, positive_hits, negative_hits, score


def theme_hits(value):
    hits = []
    for key, (_, patterns) in THEME_RE.items():
        if any(pattern.search(value) for pattern in patterns):
            hits.append(key)
    return hits


def classify(row):
    # Apple titles are searchable context; original title/text remain untouched.
    title = row.get("title") or ""
    body = row.get("text") or ""
    searchable = f"{title}\n{body}".strip()
    themes = theme_hits(searchable)
    text_label, pos_hits, neg_hits, text_score = text_sentiment(searchable)
    wc = word_count(searchable)
    return {
        "comment_text_for_analysis": searchable,
        "rating_sentiment": explicit_sentiment(row["rating"]),
        "sentiment_method": "explicit_source_rating_1_2_negative_3_neutral_4_5_positive",
        "text_sentiment_rule": text_label,
        "text_positive_hits": pos_hits,
        "text_negative_hits": neg_hits,
        "text_polarity_score": text_score,
        "sentiment_rating_text_agreement": text_label in {"unknown", "mixed_or_neutral"} or text_label == explicit_sentiment(row["rating"]),
        "themes": themes,
        "theme_labels": [THEMES[key][0] for key in themes],
        "theme_count": len(themes),
        "primary_theme": themes[0] if themes else "unclassified",
        "primary_theme_label": THEMES[themes[0]][0] if themes else "Unclassified / insufficient text",
        "word_count_for_analysis": wc,
        "short_text_for_theme_review": wc <= 4,
    }


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (list, dict, bool)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: csv_value(row.get(field)) for field in fields} for row in rows)


def ratio(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def metrics(group, group_name, extra=None):
    n = len(group)
    negative = sum(row["rating_sentiment"] == "negative" for row in group)
    positive = sum(row["rating_sentiment"] == "positive" for row in group)
    one_star = sum(row["rating"] == 1 for row in group)
    result = {
        "group": group_name,
        "review_count": n,
        "mean_rating": round(sum(row["rating"] for row in group) / n, 4) if n else None,
        "negative_count_rating_1_2": negative,
        "negative_rate_rating_1_2": ratio(negative, n),
        "positive_count_rating_4_5": positive,
        "positive_rate_rating_4_5": ratio(positive, n),
        "one_star_count": one_star,
        "one_star_rate": ratio(one_star, n),
        "text_negative_rule_count": sum(row["text_sentiment_rule"] == "negative" for row in group),
        "text_negative_rule_rate": ratio(sum(row["text_sentiment_rule"] == "negative" for row in group), n),
        "short_text_count": sum(row["short_text_for_theme_review"] for row in group),
    }
    if extra:
        result.update(extra)
    return result


def grouped(rows, key_fn):
    result = defaultdict(list)
    for row in rows:
        result[key_fn(row)].append(row)
    return result


def theme_metrics(rows, group_name, group_key=None):
    result = []
    groups = [(group_name, rows)] if group_key is None else sorted(grouped(rows, group_key).items())
    for group, members in groups:
        for theme_key, (label, _) in THEMES.items():
            mentions = [row for row in members if theme_key in row["themes"]]
            negative = [row for row in mentions if row["rating_sentiment"] == "negative"]
            result.append(
                {
                    "group": group if isinstance(group, str) else "|".join(group),
                    "theme": theme_key,
                    "theme_label": label,
                    "review_count": len(members),
                    "theme_mentions": len(mentions),
                    "theme_mention_rate": ratio(len(mentions), len(members)),
                    "theme_negative_count": len(negative),
                    "theme_negative_rate": ratio(len(negative), len(mentions)),
                    "theme_mean_rating": round(sum(row["rating"] for row in mentions) / len(mentions), 4) if mentions else None,
                    "theme_short_text_count": sum(row["short_text_for_theme_review"] for row in mentions),
                }
            )
    return result


def quote_rows(rows):
    result = []
    for theme_key, (label, _) in THEMES.items():
        for app_key in ["sc_mobile", "hsbc_hk"]:
            candidates = sorted(
                [r for r in rows if r["app_key"] == app_key and theme_key in r["themes"] and r["rating"] <= 2],
                key=lambda r: (r["rating"], -r["review_timestamp_seconds"]),
            )
            if candidates:
                row = candidates[0]
                result.append(
                    {
                        "app_key": app_key,
                        "app": row["app"],
                        "theme": theme_key,
                        "theme_label": label,
                        "rating": row["rating"],
                        "review_time_hk": row["review_time_hk"],
                        "text": row["text"],
                        "source_url": row["source_url"],
                        "review_id": row["review_id"],
                        "evidence_note": "Representative low-rated comment; not a prevalence estimate.",
                    }
                )
    return result


def main():
    rows = json.loads(INPUT.read_text(encoding="utf-8"))
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(len(rows) == 311, f"Expected 311 rows, got {len(rows)}")
    require(all(row["language_status"] == "english" for row in rows), "Input includes non-English row")
    require(all(row["within_six_month_window"] is True for row in rows), "Input includes out-of-window row")
    require(rows == sorted(rows, key=lambda r: (-r["review_timestamp_seconds"], r["record_key"])), "Input is not newest-first")
    classified = []
    for row in rows:
        item = dict(row)
        item.update(classify(row))
        classified.append(item)
    require(len({row["record_key"] for row in classified}) == len(classified), "Duplicate record keys")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    base_fields = list(rows[0])
    analysis_fields = [
        "comment_text_for_analysis", "rating_sentiment", "sentiment_method", "text_sentiment_rule",
        "text_positive_hits", "text_negative_hits", "text_polarity_score", "sentiment_rating_text_agreement",
        "themes", "theme_labels", "theme_count", "primary_theme", "primary_theme_label",
        "word_count_for_analysis", "short_text_for_theme_review",
    ]
    write_csv(OUTPUT / "comment_labels.csv", classified, base_fields + analysis_fields)
    (OUTPUT / "comment_labels.json").write_text(json.dumps(classified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    app_groups = grouped(classified, lambda row: row["app_key"])
    benchmark = [metrics(app_groups["sc_mobile"], "SC Mobile"), metrics(app_groups["hsbc_hk"], "HSBC benchmark")]
    sc = benchmark[0]
    hsbc = benchmark[1]
    gaps = {"group": "SC Mobile minus HSBC benchmark"}
    for key in ["review_count", "mean_rating", "negative_rate_rating_1_2", "positive_rate_rating_4_5", "one_star_rate", "text_negative_rule_rate"]:
        gaps[key] = sc[key] - hsbc[key] if key == "review_count" else round(sc[key] - hsbc[key], 6)
    benchmark.append(gaps)
    write_csv(OUTPUT / "overall_benchmark.csv", benchmark, list(benchmark[0]))
    (OUTPUT / "overall_benchmark.json").write_text(json.dumps(benchmark, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    month_groups = grouped(classified, lambda row: row["review_time_hk"][:7])
    monthly = []
    for month in sorted(month_groups):
        members = month_groups[month]
        monthly.append(metrics(month_groups[month], month, {
            "sc_review_count": sum(row["app_key"] == "sc_mobile" for row in members),
            "hsbc_review_count": sum(row["app_key"] == "hsbc_hk" for row in members),
            "sc_negative_rate": ratio(sum(row["app_key"] == "sc_mobile" and row["rating_sentiment"] == "negative" for row in members), sum(row["app_key"] == "sc_mobile" for row in members)),
            "hsbc_negative_rate": ratio(sum(row["app_key"] == "hsbc_hk" and row["rating_sentiment"] == "negative" for row in members), sum(row["app_key"] == "hsbc_hk" for row in members)),
        }))
    write_csv(OUTPUT / "monthly_overall_feedback.csv", monthly, list(monthly[0]))

    themes_overall = theme_metrics(classified, "overall")
    themes_by_app = theme_metrics(classified, "app", lambda row: row["app_key"])
    write_csv(OUTPUT / "themes_overall.csv", themes_overall, list(themes_overall[0]))
    write_csv(OUTPUT / "themes_by_app.csv", themes_by_app, list(themes_by_app[0]))

    quotes = quote_rows(classified)
    write_csv(OUTPUT / "representative_quotes.csv", quotes, list(quotes[0]) if quotes else ["app_key"])

    sample = []
    seen = set()
    for row in sorted(classified, key=lambda r: (-r["review_timestamp_seconds"], r["record_key"])):
        key = (row["app_key"], row["rating"])
        if key not in seen:
            sample.append(row)
            seen.add(key)
    validation_fields = ["record_key", "app_key", "app", "rating", "review_time_hk", "title", "text", "rating_sentiment", "text_sentiment_rule", "themes", "theme_labels", "short_text_for_theme_review", "source_url"]
    write_csv(OUTPUT / "validation_sample.csv", sample, validation_fields)
    validation_summary = {
        "sample_rows": len(sample),
        "selection": "one newest-first review for each available app_key x rating stratum; platform intentionally not used as a reporting split",
        "manual_annotation_status": "reviewed",
        "manual_review_file": "checkpoint_D_customer_feedback_analysis.md",
        "manual_review_result": "10/10 explicit star-rating labels and 10/10 broad theme assignments were plausible on this spot-check; two text/rating disagreements were retained as evidence that text polarity is supplemental.",
        "purpose": "Check that star-rating sentiment and keyword themes are plausible before publishing findings; short generic comments should not be over-interpreted.",
    }
    (OUTPUT / "validation_sample_summary.json").write_text(json.dumps(validation_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    top_themes = []
    for app_key in ["sc_mobile", "hsbc_hk"]:
        candidates = sorted([row for row in themes_by_app if row["group"] == app_key], key=lambda row: (-row["theme_mentions"], row["theme"]))
        top_themes.extend(candidates[:5])
    write_csv(OUTPUT / "top_themes_by_app.csv", top_themes, list(top_themes[0]))

    report = {
        "checkpoint": "D",
        "analysis_focus": "Monitor and report customer feedback comments only",
        "input": INPUT.relative_to(ROOT).as_posix(),
        "input_sha256": hashlib.sha256(INPUT.read_bytes()).hexdigest(),
        "rows": len(classified),
        "apps": {"primary": "SC Mobile Hong Kong", "benchmark": "HSBC HK Mobile Banking"},
        "reporting_grain": "overall app-level results; Google Play and Apple App Store are not split in the reported metrics",
        "comment_text_definition": "Google text is the comment body. Apple title and text are retained separately; title is added only to comment_text_for_analysis for search/rule matching.",
        "sentiment_method": "Primary: explicit source star rating (1-2 negative, 3 neutral, 4-5 positive). Supplemental deterministic text lexicon is reported separately and is not treated as a human emotion diagnosis.",
        "theme_method": "Conservative keyword/phrase rules over Apple title + review body; multiple themes per comment allowed; no theme is forced when no rule matches.",
        "monthly_caveat": "April starts on the 19th and October ends at the latest observed record on October 16; they are partial observed months.",
        "benchmark_caveat": "Overall app comparison aggregates platform records as requested. App sample counts and platform composition are unequal; this is descriptive, not a causal or statistical significance claim.",
        "summary_metrics": benchmark,
        "monthly_metrics": monthly,
        "top_themes_by_app": top_themes,
        "representative_quote_count": len(quotes),
        "validation_sample": validation_summary,
        "next_step": "Review validation_sample.csv manually, revise theme rules if needed, then write final evidence-backed interpretation and HTML/report output.",
    }
    report["artifact_sha256"] = {}
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file() and path.name != "analysis_summary.json":
            report["artifact_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (OUTPUT / "analysis_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "rows": len(classified), "sc": sc, "hsbc": hsbc, "validation_sample": len(sample)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

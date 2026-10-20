"""Original English banking-feedback rules. See references/methods.md for limits."""
import re
import unicodedata
from collections import Counter, OrderedDict, defaultdict

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

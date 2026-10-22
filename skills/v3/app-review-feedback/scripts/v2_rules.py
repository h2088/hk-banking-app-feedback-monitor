"""Explicit V2 additions for identity-verification and suggestion wording.

The V1 helper file is unchanged. Matching remains a multi-label keyword screen.
"""
import re
import theme_rules as original

ADDITIONS = {
    "login_authentication_access": [r"\bface recognition\b", r"\bfacial recognition\b", r"\b(?:scan|scanning)\s+(?:my\s+)?HKID\b", r"\bID\s+or\s+email\s+checking\b"],
    "feature_request": [r"\bsuggest(?:ion|ions)?\b", r"\bcan consider\b", r"\bshould be combined\b"],
}
for key, patterns in ADDITIONS.items():
    label, old = original.THEMES[key]
    original.THEMES[key] = (label, old + patterns)
    original.THEME_RE[key] = (label, [re.compile(p, re.I) for p in old + patterns])

THEMES = original.THEMES
classify = original.classify
metrics = original.metrics
normalized = original.normalized
theme_metrics = original.theme_metrics

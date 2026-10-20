"""Google RPC parser and deterministic English detection; langdetect loads lazily."""
import json
import re

def nested(value, indexes, default=None):
    try:
        for index in indexes:
            value = value[index]
        return value
    except (IndexError, TypeError, KeyError):
        return default


def language(text):
    """Conservative English subset; uncertain short text remains available."""
    from langdetect import DetectorFactory, detect_langs
    from langdetect.lang_detect_exception import LangDetectException
    DetectorFactory.seed = 0
    cjk = bool(re.search(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
    if not text.strip():
        return "und", "uncertain", "empty", {}
    if cjk:
        return "mixed" if len(words) >= 3 else "zh/ja/ko", "mixed" if len(words) >= 3 else "non_english", "script_check", {}
    short_english = {
        "good", "great", "excellent", "nice", "bad", "terrible", "awful", "amazing",
        "app", "apps", "very", "easy", "use", "to", "the", "best", "worst", "slow",
        "useless", "helpful", "convenient", "awesome", "perfect", "useful", "user",
        "friendly", "super", "really", "fast", "love", "it", "not", "working",
    }
    if words and len(words) <= 4 and all(w.lower() in short_english for w in words):
        return "en", "english", "short_english_word_list", {"en": None}
    if len("".join(words)) < 10 and not re.search(r"[^\x00-\x7f]", text):
        return "und", "uncertain", "short_text", {}
    try:
        probabilities = {item.lang: round(item.prob, 6) for item in detect_langs(text)}
    except LangDetectException:
        return "und", "uncertain", "langdetect_no_features", {}
    best = max(probabilities, key=probabilities.get)
    if best == "en" and probabilities[best] >= 0.80:
        status = "english"
    elif best != "en" and probabilities[best] >= 0.80:
        status = "non_english"
    else:
        status = "uncertain"
    return best, status, "langdetect_1.0.9_seed_0", probabilities


def parse_rpc(text):
    payload = text.split("\n", 1)[1].strip() if text.startswith(")]}'") else text.strip()
    try:
        frames = json.loads(payload)
    except json.JSONDecodeError:
        frames = []
        for line in payload.splitlines():
            if line.startswith("["):
                frames.extend(json.loads(line))
    frame = next((f for f in frames if isinstance(f, list) and len(f) > 2 and f[1] == "oCPfdb"), None)
    if frame is None or not isinstance(frame[2], str):
        raise ValueError("No oCPfdb review frame; response preserved for inspection")
    decoded = json.loads(frame[2])
    items = decoded[0] or [] if decoded else []
    token = nested(decoded, [-2, -1])
    return items, token if isinstance(token, str) and token else None, decoded

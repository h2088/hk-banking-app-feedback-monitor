"""Public Apple JSON/Atom parsing, extracted without source-specific configuration."""
import json
from xml.etree import ElementTree

def entries_from_feed(decoded):
    entries = decoded.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    return [(index, entry) for index, entry in enumerate(entries) if "im:rating" in entry]


def parse_feed(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        root = ElementTree.fromstring(text)
        def key(tag):
            if tag.startswith("{http://itunes.apple.com/rss}"):
                return "im:" + tag.split("}", 1)[1]
            return tag.split("}", 1)[-1]
        def convert(element):
            result = {"attributes": dict(element.attrib)} if element.attrib else {}
            if len(element) == 0:
                result["label"] = element.text or ""
            else:
                for child in element:
                    name = key(child.tag)
                    value = convert(child)
                    if name in ("entry", "link"):
                        result.setdefault(name, []).append(value)
                    elif name in result:
                        old = result[name]
                        result[name] = old + [value] if isinstance(old, list) else [old, value]
                    else:
                        result[name] = value
            return result
        if key(root.tag) != "feed":
            raise ValueError("Response is neither a JSON feed nor an Atom feed")
        return {"feed": convert(root)}


def entry_label(entry, key, default=""):
    value = entry.get(key, {})
    if isinstance(value, list):
        # Atom can include both text and HTML content; preserve the text version.
        value = next((part for part in value if part.get("attributes", {}).get("type") == "text"), value[0])
    return value.get("label", default)

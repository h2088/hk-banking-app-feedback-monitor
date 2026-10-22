"""Package the skill directory, excluding runtime caches and customer artifacts."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def package(source, output):
    source, output = source.resolve(), output.resolve()
    if not (source / "SKILL.md").is_file() or output.is_relative_to(source):
        raise ValueError("Need a skill folder and output outside that folder")
    if output.exists() or output.with_suffix(".manifest.json").exists():
        raise ValueError("Package target already exists; choose a new filename")
    selected = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if not path.is_file() or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink() or relative.parts[0] not in {"SKILL.md", "agents", "assets", "scripts", "references"}:
            raise ValueError("Unexpected package input: " + str(relative))
        if path.suffix == ".md":
            content = path.read_text(encoding="utf-8")
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
                if not link.startswith(("http:", "https:", "#")) and not (path.parent / link).is_file():
                    raise ValueError("Missing documentation link: " + link)
        selected.append(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    with ZipFile(output, "x", ZIP_DEFLATED) as archive:
        for path in selected:
            relative = path.relative_to(source).as_posix()
            archive.write(path, source.name + "/" + relative)
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {"skill": source.name, "package": output.name, "files": len(hashes), "file_sha256": hashes,
        "package_sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "excludes_customer_data_and_caches": True}
    output.with_suffix(".manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "file_sha256"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.source, args.output)

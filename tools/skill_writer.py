"""
skill_writer.py

Manages generated crush Skill files under ./crushes/{slug}/.

Actions:
  list     — List all existing crush profiles
  create   — Create a new crush profile directory with starter files
  save     — Write or overwrite specific files in a crush profile
  validate — Check that all required files exist in a profile

Usage:
  python3 skill_writer.py --action list [--base-dir ./crushes]
  python3 skill_writer.py --action create --slug <slug> [--name <display_name>]
  python3 skill_writer.py --action save --slug <slug> --file <filename> --content-file <path>
  python3 skill_writer.py --action validate --slug <slug>
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REQUIRED_FILES = ["SKILL.md", "persona.md", "memory.md"]
META_FILE = "meta.json"


def list_skills(base_dir: str) -> None:
    base = Path(base_dir)
    if not base.exists():
        print(f"No crushes directory found at: {base_dir}")
        print("Run /create-crush to create your first profile.")
        return

    profiles = []
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            meta_path = d / META_FILE
            display_name = d.name
            created_at = ""
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    display_name = meta.get("name", d.name)
                    created_at = meta.get("created_at", "")
                except Exception:
                    pass
            skill_size = (d / "SKILL.md").stat().st_size
            profiles.append((d.name, display_name, skill_size, created_at))

    if not profiles:
        print("No crush profiles found.")
        print("Run /create-crush to create your first profile.")
        return

    print(f"{'Slug':<20} {'Name':<20} {'SKILL.md':<12} {'Created'}")
    print("-" * 70)
    for slug, name, size, created in profiles:
        print(f"{slug:<20} {name:<20} {size:<12} {created}")
    print(f"\nTotal: {len(profiles)} profile(s)")


def create_skill(slug: str, display_name: str, base_dir: str) -> None:
    profile_dir = Path(base_dir) / slug
    if profile_dir.exists():
        print(f"Profile already exists: {profile_dir}")
        sys.exit(1)

    profile_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "slug": slug,
        "name": display_name or slug,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0.0",
    }
    with open(profile_dir / META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    skill_content = f"""---
name: {slug}
description: Crush profile for {display_name or slug}
version: 1.0.0
---

# {display_name or slug}

> Profile created on {meta['created_at']}.

## Persona

*(Not yet generated. Run the intake flow to build the persona.)*

## Memory

*(Not yet generated.)*
"""
    with open(profile_dir / "SKILL.md", "w", encoding="utf-8") as f:
        f.write(skill_content)

    for fname in ("persona.md", "memory.md"):
        with open(profile_dir / fname, "w", encoding="utf-8") as f:
            f.write(f"# {fname.replace('.md', '').title()}\n\n*(Not yet generated.)*\n")

    print(f"Profile created: {profile_dir}")
    print(f"Files: {', '.join(f.name for f in profile_dir.iterdir())}")


def save_file(slug: str, filename: str, content_file: str, base_dir: str) -> None:
    profile_dir = Path(base_dir) / slug
    profile_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    if safe_name != filename:
        print(f"Error: filename must not contain path separators: {filename}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(content_file):
        print(f"Error: content file not found: {content_file}", file=sys.stderr)
        sys.exit(1)

    with open(content_file, "r", encoding="utf-8") as f:
        content = f.read()

    target_path = profile_dir / safe_name
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)

    meta_path = profile_dir / META_FILE
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    print(f"Saved: {target_path} ({len(content)} chars)")


def validate_skill(slug: str, base_dir: str) -> None:
    profile_dir = Path(base_dir) / slug
    if not profile_dir.exists():
        print(f"Profile not found: {profile_dir}", file=sys.stderr)
        sys.exit(1)

    all_ok = True
    for fname in REQUIRED_FILES:
        fpath = profile_dir / fname
        if fpath.exists():
            print(f"  OK  {fname} ({fpath.stat().st_size} bytes)")
        else:
            print(f"  MISSING  {fname}")
            all_ok = False

    for fname in (META_FILE,):
        fpath = profile_dir / fname
        status = "OK" if fpath.exists() else "optional"
        print(f"  {status}  {fname}")

    if all_ok:
        print(f"\nProfile '{slug}' is complete.")
    else:
        print(f"\nProfile '{slug}' is incomplete.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Crush Skill file manager")
    parser.add_argument(
        "--action", required=True,
        choices=["list", "create", "save", "validate"],
        help="Action to perform",
    )
    parser.add_argument("--slug",         help="Crush profile slug")
    parser.add_argument("--name",         help="Display name (for create)")
    parser.add_argument("--file",         help="Filename to save (for save)")
    parser.add_argument("--content-file", help="Source content file path (for save)")
    parser.add_argument("--base-dir",     default="./crushes", help="Base directory")
    args = parser.parse_args()

    if args.action == "list":
        list_skills(args.base_dir)
    elif args.action == "create":
        if not args.slug:
            print("Error: --slug required", file=sys.stderr); sys.exit(1)
        create_skill(args.slug, args.name or args.slug, args.base_dir)
    elif args.action == "save":
        if not all([args.slug, args.file, args.content_file]):
            print("Error: --slug, --file, --content-file required", file=sys.stderr); sys.exit(1)
        save_file(args.slug, args.file, args.content_file, args.base_dir)
    elif args.action == "validate":
        if not args.slug:
            print("Error: --slug required", file=sys.stderr); sys.exit(1)
        validate_skill(args.slug, args.base_dir)


if __name__ == "__main__":
    main()

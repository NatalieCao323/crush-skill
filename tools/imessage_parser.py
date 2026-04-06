"""
imessage_parser.py

Parse iMessage / SMS exports for crush.skill.

Supported formats:
  - iMazing CSV export (iMessage)
  - iPhone Backup Extractor CSV
  - iExplorer text export
  - SMS Backup & Restore XML (Android)
  - Plain text copy-paste

Usage:
  python3 imessage_parser.py --file <path> --target <name> --output <output_path>
  python3 imessage_parser.py --file <path> --target <name> --output <output_path> --format auto
"""

import argparse
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()

    if ext == ".xml":
        return "sms_backup_xml"

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            sample = f.read(2000)
    except Exception:
        return "plaintext"

    # iMazing CSV: has "Sender","Date","Text" header
    if re.search(r"Sender.*Date.*Text|From.*Time.*Message", sample, re.IGNORECASE):
        return "imazing_csv"

    # SMS Backup & Restore XML (Android)
    if "<smses" in sample or "<sms " in sample:
        return "sms_backup_xml"

    # Bracket format: "[2024-01-15 22:30] sender: content"
    if re.search(r"\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\]", sample):
        return "bracket_txt"

    return "plaintext"


# ---------------------------------------------------------------------------
# Format-specific parsers
# ---------------------------------------------------------------------------

def parse_imazing_csv(file_path: str, target_name: str) -> dict:
    """Parse iMazing CSV export."""
    messages = []
    try:
        with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            headers = [h.lower().strip() for h in (reader.fieldnames or [])]

            # Map common column name variations
            sender_col  = next((h for h in headers if "sender" in h or "from" in h), None)
            content_col = next((h for h in headers if "text" in h or "message" in h or "body" in h), None)
            time_col    = next((h for h in headers if "date" in h or "time" in h), None)

            if not content_col:
                return parse_plaintext(file_path, target_name)

            for row in reader:
                row_lower = {k.lower().strip(): v for k, v in row.items()}
                sender  = row_lower.get(sender_col, "unknown") if sender_col else "unknown"
                content = row_lower.get(content_col, "")
                ts      = row_lower.get(time_col, "") if time_col else ""
                if content.strip():
                    messages.append({
                        "timestamp": ts,
                        "sender": sender.strip(),
                        "content": content.strip(),
                    })
    except Exception as e:
        return {
            "target_name": target_name,
            "total_messages": 0,
            "target_messages": 0,
            "user_messages": 0,
            "raw_text": "",
            "analysis": {"note": f"CSV parse error: {e}", "top_particles": [],
                         "top_emojis": [], "avg_message_length": 0,
                         "punctuation_habits": {}, "message_style": "error"},
            "sample_messages": [],
        }

    return analyze_messages(messages, target_name)


def parse_sms_backup_xml(file_path: str, target_name: str) -> dict:
    """Parse SMS Backup & Restore XML (Android)."""
    messages = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        for sms in root.findall(".//sms"):
            body    = sms.get("body", "").strip()
            address = sms.get("address", "")
            date_ms = sms.get("date", "")
            sms_type = sms.get("type", "1")  # 1=received, 2=sent

            if not body:
                continue

            # type 1 = received (from target), type 2 = sent (from user)
            sender = target_name if sms_type == "1" else "me"

            # Convert ms timestamp to readable string
            ts = ""
            if date_ms.isdigit():
                import datetime
                ts = datetime.datetime.fromtimestamp(
                    int(date_ms) / 1000
                ).strftime("%Y-%m-%d %H:%M:%S")

            messages.append({
                "timestamp": ts,
                "sender": sender,
                "content": body,
            })

        # Also handle MMS
        for mms in root.findall(".//mms"):
            for part in mms.findall(".//part"):
                text = part.get("text", "").strip()
                if text and text != "null":
                    mms_type = mms.get("msg_box", "1")
                    sender = target_name if mms_type == "1" else "me"
                    date_ms = mms.get("date", "")
                    ts = ""
                    if date_ms.isdigit():
                        import datetime
                        ts = datetime.datetime.fromtimestamp(
                            int(date_ms) / 1000
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    messages.append({
                        "timestamp": ts,
                        "sender": sender,
                        "content": text,
                    })

    except Exception as e:
        return {
            "target_name": target_name,
            "total_messages": 0,
            "target_messages": 0,
            "user_messages": 0,
            "raw_text": "",
            "analysis": {"note": f"XML parse error: {e}", "top_particles": [],
                         "top_emojis": [], "avg_message_length": 0,
                         "punctuation_habits": {}, "message_style": "error"},
            "sample_messages": [],
        }

    return analyze_messages(messages, target_name)


def parse_bracket_txt(file_path: str, target_name: str) -> dict:
    """Parse bracket-style txt format: [2024-01-15 22:30] sender: content"""
    messages = []
    line_re = re.compile(
        r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\]\s+(.+?):\s*(.*)$"
    )
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = line_re.match(line.strip())
            if m:
                ts, sender, content = m.groups()
                messages.append({
                    "timestamp": ts,
                    "sender": sender.strip(),
                    "content": content.strip(),
                })
    return analyze_messages(messages, target_name)


def parse_plaintext(file_path: str, target_name: str) -> dict:
    """Parse pasted plaintext: 'sender: content' per line."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    messages = []
    line_re = re.compile(r"^(.{1,20})[:：]\s*(.+)$")
    for line in content.splitlines():
        m = line_re.match(line.strip())
        if m:
            sender, msg_content = m.groups()
            messages.append({
                "timestamp": "",
                "sender": sender.strip(),
                "content": msg_content.strip(),
            })

    if len(messages) >= 3:
        return analyze_messages(messages, target_name)

    return {
        "target_name": target_name,
        "total_messages": 0,
        "target_messages": 0,
        "user_messages": 0,
        "raw_text": content,
        "analysis": {
            "note": "Unstructured format. Raw content preserved for direct analysis.",
            "top_particles": [], "top_emojis": [],
            "avg_message_length": 0, "punctuation_habits": {},
            "message_style": "raw",
        },
        "sample_messages": [],
    }


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze_messages(messages: list, target_name: str) -> dict:
    target_msgs = [m for m in messages if target_name in m.get("sender", "")]
    user_msgs   = [m for m in messages if target_name not in m.get("sender", "")]
    all_text    = " ".join(m["content"] for m in target_msgs if m.get("content"))

    particles = re.findall(r"[哈嗯哦噢嘿唉呜啊呀吧嘛呢吗么]+", all_text)
    particle_freq: dict = {}
    for p in particles:
        particle_freq[p] = particle_freq.get(p, 0) + 1
    top_particles = sorted(particle_freq.items(), key=lambda x: -x[1])[:10]

    emoji_re = re.compile(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
        r"\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
        re.UNICODE,
    )
    emojis = emoji_re.findall(all_text)
    emoji_freq: dict = {}
    for e in emojis:
        emoji_freq[e] = emoji_freq.get(e, 0) + 1
    top_emojis = sorted(emoji_freq.items(), key=lambda x: -x[1])[:10]

    lengths = [len(m["content"]) for m in target_msgs if m.get("content")]
    avg_length = round(sum(lengths) / len(lengths), 1) if lengths else 0

    reply_rate = (
        round(len(target_msgs) / len(user_msgs), 2) if user_msgs else None
    )

    late_night_count = 0
    for m in target_msgs:
        ts = m.get("timestamp", "")
        hour_match = re.search(r"(\d{2}):\d{2}", ts)
        if hour_match:
            hour = int(hour_match.group(1))
            if hour >= 22 or hour <= 3:
                late_night_count += 1

    return {
        "target_name": target_name,
        "total_messages": len(messages),
        "target_messages": len(target_msgs),
        "user_messages": len(user_msgs),
        "analysis": {
            "top_particles": top_particles,
            "top_emojis": top_emojis,
            "avg_message_length": avg_length,
            "punctuation_habits": {
                "period":      all_text.count("。"),
                "exclamation": all_text.count("!") + all_text.count("！"),
                "question":    all_text.count("?") + all_text.count("？"),
                "ellipsis":    all_text.count("...") + all_text.count("…"),
                "tilde":       all_text.count("~") + all_text.count("～"),
            },
            "message_style": "short_burst" if avg_length < 20 else "long_form",
            "reply_rate": reply_rate,
            "late_night_messages": late_night_count,
        },
        "sample_messages": [
            m["content"] for m in target_msgs[:50] if m.get("content")
        ],
    }


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def write_output(result: dict, output_path: str, fmt: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    target   = result.get("target_name", "unknown")
    analysis = result.get("analysis", {})

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# iMessage/SMS Analysis: {target}\n\n")
        f.write(f"Source format: {fmt}\n")
        f.write(f"Total messages: {result.get('total_messages', 'N/A')}\n")
        f.write(f"Messages from target: {result.get('target_messages', 'N/A')}\n")
        f.write(f"Messages from user: {result.get('user_messages', 'N/A')}\n")
        if analysis.get("reply_rate") is not None:
            f.write(f"Reply rate (target/user): {analysis['reply_rate']}\n")
        if analysis.get("late_night_messages"):
            f.write(f"Late-night messages (22:00-03:00): {analysis['late_night_messages']}\n")
        f.write("\n")

        if analysis.get("note"):
            f.write(f"> Note: {analysis['note']}\n\n")

        if result.get("raw_text"):
            f.write("## Raw Content\n\n```\n")
            f.write(result["raw_text"][:5000])
            f.write("\n```\n\n")

        if analysis.get("top_particles"):
            f.write("## Filler Particles\n\n")
            for word, count in analysis["top_particles"]:
                f.write(f"- `{word}`: {count}\n")
            f.write("\n")

        if analysis.get("top_emojis"):
            f.write("## Frequent Emoji\n\n")
            for emoji, count in analysis["top_emojis"]:
                f.write(f"- {emoji}: {count}\n")
            f.write("\n")

        f.write("## Message Style\n\n")
        f.write(f"- Average length: {analysis.get('avg_message_length', 0)} chars\n")
        f.write(f"- Style: {analysis.get('message_style', 'unknown')}\n\n")

        if result.get("sample_messages"):
            f.write("## Sample Messages (target)\n\n")
            for i, msg in enumerate(result["sample_messages"], 1):
                f.write(f"{i}. {msg}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="iMessage/SMS chat log parser for crush.skill"
    )
    parser.add_argument("--file",   required=True, help="Input file path")
    parser.add_argument("--target", required=True, help="Target person's name")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument(
        "--format", default="auto",
        help="Format: auto / imazing_csv / sms_backup_xml / bracket_txt / plaintext",
    )
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    fmt = args.format
    if fmt == "auto":
        fmt = detect_format(args.file)
        print(f"Detected format: {fmt}")

    dispatch = {
        "imazing_csv":    parse_imazing_csv,
        "sms_backup_xml": parse_sms_backup_xml,
        "bracket_txt":    parse_bracket_txt,
        "plaintext":      parse_plaintext,
    }
    parse_fn = dispatch.get(fmt, parse_plaintext)
    result = parse_fn(args.file, args.target)

    write_output(result, args.output, fmt)
    print(f"Analysis complete. Output: {args.output}")
    print(
        f"Target messages: {result.get('target_messages', 'N/A')} "
        f"/ Total: {result.get('total_messages', 'N/A')}"
    )


if __name__ == "__main__":
    main()

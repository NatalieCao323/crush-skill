"""
screenshot_parser.py

Extract chat messages from WeChat / iMessage / SMS screenshots.

This tool uses two strategies:
  1. Claude Vision (via OpenAI-compatible API) — best accuracy, requires API key
  2. Tesseract OCR (offline fallback) — requires tesseract + pytesseract installed

Output: a structured Markdown file compatible with wechat_parser.py output format,
        ready for downstream bayesian_tagger.py analysis.

Usage:
  # Single screenshot
  python3 screenshot_parser.py --file chat_screenshot.png --target 小明 --output out.md

  # Batch: all images in a directory
  python3 screenshot_parser.py --dir ./screenshots/ --target 小明 --output out.md

  # Force offline OCR (no API key needed)
  python3 screenshot_parser.py --file chat.png --target 小明 --output out.md --mode ocr

Requirements:
  - For Vision mode (default): set OPENAI_API_KEY env var
  - For OCR mode: pip3 install pytesseract Pillow && brew install tesseract (macOS)
                  or: apt-get install tesseract-ocr (Linux)
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".heic", ".heif", ".webp", ".bmp"}


# ---------------------------------------------------------------------------
# Strategy 1: Claude Vision via API
# ---------------------------------------------------------------------------

VISION_PROMPT = """You are a chat log extractor. The image shows a WeChat / iMessage / SMS conversation screenshot.

Extract ALL visible messages in order. For each message, identify:
1. The sender (left-side bubbles are usually from the other person; right-side bubbles are usually from "me")
2. The message text content
3. Approximate time if visible

Output ONLY a JSON array in this exact format, no other text:
[
  {"sender": "小明", "content": "要是你在就好了", "time": "22:30"},
  {"sender": "me", "content": "我也想你啊", "time": "22:31"},
  ...
]

Rules:
- Use the actual name/nickname visible in the chat header for the other person
- Use "me" for the right-side (user's own) messages
- If no time is visible, use ""
- Include sticker/emoji descriptions like "[sticker: 笑哭]" if visible
- Skip system messages like "以下为新消息" or "对方正在输入"
- If the image is not a chat screenshot, return []
"""


def extract_via_vision(image_path: str) -> list:
    """Call Claude/GPT Vision API to extract chat messages from a screenshot."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. "
            "Set it with: export OPENAI_API_KEY=your_key\n"
            "Or use --mode ocr for offline extraction."
        )

    try:
        import urllib.request
        import urllib.error

        # Read and encode image
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower().lstrip(".")
        mime_map = {"jpg": "jpeg", "heic": "jpeg", "heif": "jpeg"}
        mime = f"image/{mime_map.get(ext, ext)}"

        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{img_data}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 2000,
        }).encode("utf-8")

        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        text = result["choices"][0]["message"]["content"].strip()

        # Extract JSON array from response
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return []

    except Exception as e:
        raise RuntimeError(f"Vision API call failed: {e}")


# ---------------------------------------------------------------------------
# Strategy 2: Tesseract OCR (offline fallback)
# ---------------------------------------------------------------------------

def extract_via_ocr(image_path: str) -> list:
    """Use Tesseract OCR to extract text from a screenshot."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "pytesseract and Pillow are required for OCR mode.\n"
            "Install: pip3 install pytesseract Pillow\n"
            "Also install Tesseract: brew install tesseract (macOS) "
            "or apt-get install tesseract-ocr (Linux)"
        )

    img = Image.open(image_path)

    # Try Chinese + English OCR
    try:
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
    except Exception:
        # Fallback to English only if Chinese language pack not installed
        text = pytesseract.image_to_string(img, lang="eng")

    # Parse extracted text into messages
    # OCR output is raw text; try to find "name: content" patterns
    messages = []
    line_re = re.compile(r"^(.{1,20})[:：]\s*(.+)$")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = line_re.match(line)
        if m:
            sender, content = m.groups()
            messages.append({
                "sender": sender.strip(),
                "content": content.strip(),
                "time": "",
            })
        elif len(line) > 2:
            # Unstructured line — append as continuation or raw
            if messages:
                messages[-1]["content"] += " " + line
            else:
                messages.append({"sender": "unknown", "content": line, "time": ""})

    return messages


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_image(image_path: str, target_name: str, mode: str) -> list:
    """Extract messages from a single image file."""
    print(f"  Processing: {Path(image_path).name} ({mode} mode)")

    if mode == "vision":
        try:
            messages = extract_via_vision(image_path)
            print(f"    → {len(messages)} messages extracted via Vision API")
            return messages
        except RuntimeError as e:
            print(f"    ⚠ Vision failed: {e}")
            print("    → Falling back to OCR mode")
            try:
                messages = extract_via_ocr(image_path)
                print(f"    → {len(messages)} messages extracted via OCR")
                return messages
            except RuntimeError as e2:
                print(f"    ✗ OCR also failed: {e2}")
                return []

    elif mode == "ocr":
        try:
            messages = extract_via_ocr(image_path)
            print(f"    → {len(messages)} messages extracted via OCR")
            return messages
        except RuntimeError as e:
            print(f"    ✗ OCR failed: {e}")
            return []

    return []


def analyze_extracted(all_messages: list, target_name: str) -> dict:
    """Analyze extracted messages for stylistic features."""
    target_msgs = [
        m for m in all_messages
        if target_name in m.get("sender", "") or
        (target_name.lower() in m.get("sender", "").lower())
    ]
    user_msgs = [m for m in all_messages if m not in target_msgs]

    all_text = " ".join(m.get("content", "") for m in target_msgs)

    # Filler particles
    particles = re.findall(r"[哈嗯哦噢嘿唉呜啊呀吧嘛呢吗么]+", all_text)
    particle_freq: dict = {}
    for p in particles:
        particle_freq[p] = particle_freq.get(p, 0) + 1
    top_particles = sorted(particle_freq.items(), key=lambda x: -x[1])[:10]

    # Emoji
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

    lengths = [len(m.get("content", "")) for m in target_msgs]
    avg_length = round(sum(lengths) / len(lengths), 1) if lengths else 0

    return {
        "target_name": target_name,
        "total_messages": len(all_messages),
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
        },
        "sample_messages": [
            m.get("content", "") for m in target_msgs[:50]
        ],
        "_source": "screenshot",
    }


def write_output(result: dict, all_messages: list, output_path: str) -> None:
    """Write analysis result to Markdown."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    target = result.get("target_name", "unknown")
    analysis = result.get("analysis", {})

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Screenshot Chat Analysis: {target}\n\n")
        f.write(f"Source: screenshot extraction\n")
        f.write(f"Total messages: {result.get('total_messages', 0)}\n")
        f.write(f"Messages from target: {result.get('target_messages', 0)}\n")
        f.write(f"Messages from user: {result.get('user_messages', 0)}\n\n")

        # Full extracted conversation
        f.write("## Extracted Conversation\n\n")
        for m in all_messages:
            sender = m.get("sender", "?")
            content = m.get("content", "")
            time = m.get("time", "")
            time_str = f" [{time}]" if time else ""
            f.write(f"**{sender}**{time_str}: {content}\n\n")

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
        description="Extract chat messages from WeChat/iMessage screenshots"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Single screenshot image path")
    group.add_argument("--dir",  help="Directory containing multiple screenshots")
    parser.add_argument("--target", required=True, help="Target person's name/nickname")
    parser.add_argument("--output", required=True, help="Output Markdown file path")
    parser.add_argument(
        "--mode", default="vision", choices=["vision", "ocr"],
        help="Extraction mode: vision (Claude/GPT API) or ocr (Tesseract, offline)",
    )
    args = parser.parse_args()

    # Collect image files
    image_files = []
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        image_files = [args.file]
    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"Error: directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)
        image_files = sorted(
            str(p) for p in Path(args.dir).iterdir()
            if p.suffix.lower() in IMAGE_EXTS
        )
        if not image_files:
            print(f"No image files found in: {args.dir}", file=sys.stderr)
            sys.exit(1)

    print(f"Found {len(image_files)} image(s). Extracting with {args.mode} mode...")

    # Process all images
    all_messages = []
    for img_path in image_files:
        msgs = process_image(img_path, args.target, args.mode)
        all_messages.extend(msgs)

    if not all_messages:
        print("⚠ No messages extracted. Check image quality or try --mode ocr.")
        sys.exit(1)

    result = analyze_extracted(all_messages, args.target)
    write_output(result, all_messages, args.output)

    print(f"\nDone. {len(all_messages)} messages extracted.")
    print(f"Output: {args.output}")
    print(f"Target messages: {result['target_messages']} / Total: {result['total_messages']}")
    print(f"\nNext step: run bayesian_tagger.py on the output file.")


if __name__ == "__main__":
    main()

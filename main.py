"""
main.py - Command-line version.

Usage:
    python main.py
    python main.py --name "Acme Corp" --url https://acme.com --pages 15
"""

import argparse
import os
import re

from scraper import crawl
from report import build_report


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "company"


def run(name: str, url: str, pages: int = 10, out_dir: str = "reports") -> str:
    os.makedirs(out_dir, exist_ok=True)
    print(f"\nScraping {name} ({url}) ...")
    data = crawl(url, max_pages=pages)
    out_path = os.path.join(out_dir, f"{safe_filename(name)}_report.docx")
    build_report(name, data, out_path)
    print(f"\nDone! {len(data['pages'])} pages scanned.")
    print(f"Emails: {len(data['emails'])}  Phones: {len(data['phones'])}  "
          f"Socials: {len(data['socials'])}")
    print(f"Word file saved: {out_path}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Company website -> Word report")
    ap.add_argument("--name", help="Company name")
    ap.add_argument("--url", help="Company website link")
    ap.add_argument("--pages", type=int, default=10, help="Max pages to crawl (default 10)")
    args = ap.parse_args()

    name = args.name or input("Company name: ").strip()
    url = args.url or input("Company website link: ").strip()
    run(name, url, args.pages)

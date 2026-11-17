"""
scraper.py - Fetch a company website and extract useful information.

Crawls the home page plus internal pages (About, Contact, Services, etc.)
up to a page limit, and collects:
  - page titles, meta descriptions, keywords
  - headings and paragraph text
  - emails, phone numbers, addresses-like lines
  - social media links
  - internal pages visited
"""

import re
import time
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)\d{3,4}[\s.-]?\d{3,4}")

SOCIAL_DOMAINS = {
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "linkedin.com": "LinkedIn",
    "twitter.com": "Twitter / X",
    "x.com": "Twitter / X",
    "youtube.com": "YouTube",
    "tiktok.com": "TikTok",
    "pinterest.com": "Pinterest",
    "github.com": "GitHub",
    "wa.me": "WhatsApp",
}

# Pages we prefer to visit first when crawling
PRIORITY_WORDS = ["about", "contact", "service", "product", "team",
                  "company", "career", "solution", "pricing", "faq"]

SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf", ".zip",
            ".mp4", ".mp3", ".doc", ".docx", ".xls", ".xlsx", ".css", ".js")


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def fetch(url: str, timeout: int = 15):
    """Download a page (like curl). Returns (final_url, html) or (url, None)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        ctype = resp.headers.get("Content-Type", "")
        if resp.status_code == 200 and "html" in ctype.lower():
            resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.url, resp.text
        print(f"  [skip] {url} -> HTTP {resp.status_code} ({ctype})")
    except requests.RequestException as e:
        print(f"  [error] {url}: {e}")
    return url, None


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_page(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # contact info from raw text + mailto/tel links (before removing tags)
    emails, phones = set(), set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            emails.add(href[7:].split("?")[0].strip())
        elif href.lower().startswith("tel:"):
            phones.add(href[4:].strip())

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    body_text = clean_text(soup.get_text(" "))
    emails.update(e for e in EMAIL_RE.findall(body_text)
                  if not e.lower().endswith((".png", ".jpg", ".webp", ".gif")))
    for p in PHONE_RE.findall(body_text):
        digits = re.sub(r"\D", "", p)
        if 9 <= len(digits) <= 15:
            phones.add(p.strip())

    title = clean_text(soup.title.string) if soup.title and soup.title.string else ""

    def meta(name):
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        return clean_text(tag.get("content", "")) if tag else ""

    headings = []
    for level in ("h1", "h2", "h3"):
        for h in soup.find_all(level):
            t = clean_text(h.get_text(" "))
            if t and t not in headings:
                headings.append(t)

    paragraphs = []
    for p in soup.find_all(["p", "li"]):
        t = clean_text(p.get_text(" "))
        if len(t) >= 40 and t not in paragraphs:
            paragraphs.append(t)

    # address-like lines
    addresses = []
    for tag in soup.find_all(["address"]):
        t = clean_text(tag.get_text(" "))
        if t:
            addresses.append(t)

    links, socials = [], {}
    for a in soup.find_all("a", href=True):
        full = urldefrag(urljoin(url, a["href"]))[0]
        host = urlparse(full).netloc.lower().replace("www.", "")
        for dom, label in SOCIAL_DOMAINS.items():
            if host == dom or host.endswith("." + dom):
                socials.setdefault(label, full)
        links.append(full)

    return {
        "url": url,
        "title": title,
        "description": meta("description") or meta("og:description"),
        "keywords": meta("keywords"),
        "headings": headings,
        "paragraphs": paragraphs,
        "emails": sorted(emails),
        "phones": sorted(phones),
        "addresses": addresses,
        "socials": socials,
        "links": links,
    }


def crawl(start_url: str, max_pages: int = 10, delay: float = 0.5) -> dict:
    """Crawl the site (same domain only) and merge all extracted data."""
    start_url = normalize_url(start_url)
    final_url, html = fetch(start_url)
    if html is None:
        raise RuntimeError(f"Could not download {start_url}. Check the link and your internet.")

    base_host = urlparse(final_url).netloc.lower().replace("www.", "")
    visited, pages = set(), []
    queue = deque([(final_url, html)])

    while queue and len(pages) < max_pages:
        url, html = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        if html is None:
            url, html = fetch(url)
            if html is None:
                continue
            time.sleep(delay)
        print(f"  [ok] {url}")
        page = extract_page(url, html)
        pages.append(page)

        # queue internal links, priority pages first
        internal = []
        for link in page["links"]:
            p = urlparse(link)
            host = p.netloc.lower().replace("www.", "")
            if host != base_host or p.scheme not in ("http", "https"):
                continue
            if p.path.lower().endswith(SKIP_EXT):
                continue
            clean = link.split("?")[0].rstrip("/") or link
            if clean not in visited and clean not in [q[0] for q in queue]:
                internal.append(clean)
        internal.sort(key=lambda l: 0 if any(w in l.lower() for w in PRIORITY_WORDS) else 1)
        for link in internal:
            queue.append((link, None))

    # merge
    merged = {
        "home_url": final_url,
        "title": pages[0]["title"] if pages else "",
        "description": next((p["description"] for p in pages if p["description"]), ""),
        "keywords": next((p["keywords"] for p in pages if p["keywords"]), ""),
        "emails": sorted({e for p in pages for e in p["emails"]}),
        "phones": sorted({ph for p in pages for ph in p["phones"]}),
        "addresses": list(dict.fromkeys(a for p in pages for a in p["addresses"])),
        "socials": {},
        "pages": pages,
    }
    for p in pages:
        for k, v in p["socials"].items():
            merged["socials"].setdefault(k, v)
    return merged

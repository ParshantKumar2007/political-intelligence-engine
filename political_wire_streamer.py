#!/usr/bin/env python3
import os
import sys
import json
import gzip
import time
import hashlib
import subprocess
import urllib.request
import urllib.error
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

from political_entity_db import analyze_political_headline

# Optional Google News URL Decoder
try:
    from googlenewsdecoder import gnewsdecoder
    HAS_GNEWS_DECODER = True
except ImportError:
    HAS_GNEWS_DECODER = False

GITHUB_USER = "ParshantKumar2007"
MANIFEST_FILE = "vault_rollover_manifest.json"

POLITICAL_FEEDS = [
    {"source": "PIB Cabinet & Government Decisions", "url": "https://news.google.com/rss/search?q=site:pib.gov.in+when:3d&hl=en-IN&gl=IN&ceid=IN:en"},
    {"source": "PIB Union Cabinet & CCEA Decisions", "url": "https://news.google.com/rss/search?q=site:pib.gov.in+Cabinet+OR+CCEA+when:7d&hl=en-IN&gl=IN&ceid=IN:en"},
    {"source": "PIB Prime Minister Office (PMO)", "url": "https://news.google.com/rss/search?q=site:pib.gov.in+%22Prime+Minister%22+OR+%22PMO%22+when:3d&hl=en-IN&gl=IN&ceid=IN:en"},
    {"source": "The Indian Express Political Pulse", "url": "https://indianexpress.com/section/political-pulse/feed/"},
    {"source": "The Indian Express National", "url": "https://indianexpress.com/section/india/feed/"},
    {"source": "Hindustan Times India News", "url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"},
    {"source": "Times of India National Politics", "url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"},
    {"source": "NDTV India & Politics Wire", "url": "https://feeds.feedburner.com/ndtvnews-india-news"},
    {"source": "PRS Legislative Research (Parliament)", "url": "https://news.google.com/rss/search?q=site:prsindia.org+when:30d&hl=en-IN&gl=IN&ceid=IN:en"},
    {"source": "Economic Times Politics & Nation", "url": "https://economictimes.indiatimes.com/news/politics-and-nation/rssfeeds/1052732854.cms"},
    {"source": "Livemint Politics & Governance", "url": "https://www.livemint.com/rss/politics"},
    {"source": "Business Standard Economy & Policy", "url": "https://www.business-standard.com/rss/economy-policy-103.rss"},
    {"source": "The Hindu National Wire", "url": "https://www.thehindu.com/news/national/feeder/default.rss"},
    {"source": "Google News India Politics", "url": "https://news.google.com/rss/headlines/section/topic/NATION?hl=en-IN&gl=IN&ceid=IN:en"},
    {"source": "Politico US Policy & Congress", "url": "https://rss.politico.com/politics-news.xml"},
    {"source": "AP News World Politics", "url": "https://news.google.com/rss/search?q=source:%22Associated+Press%22+politics+when:1d&hl=en-US&gl=US&ceid=US:en"},
    {"source": "Reuters World Politics", "url": "https://news.google.com/rss/search?q=when:1h+source:reuters+politics&hl=en-US&gl=US&ceid=US:en"},
    {"source": "Bloomberg Government & Politics", "url": "https://news.google.com/rss/search?q=when:1h+source:bloomberg+politics&hl=en-US&gl=US&ceid=US:en"},
    {"source": "Al Jazeera World Geopolitics", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"source": "The Guardian Politics", "url": "https://www.theguardian.com/politics/rss"},
    {"source": "Global Geopolitics & Diplomacy", "url": "https://news.google.com/rss/search?q=when:1h+geopolitics+OR+sanctions+OR+diplomacy&hl=en-US&gl=US&ceid=US:en"},
    {"source": "BBC World Politics", "url": "https://feeds.bbci.co.uk/news/politics/rss.xml"}
]

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

def safe_git(cmd, cwd):
    for attempt in range(3):
        try:
            return subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT).decode().strip()
        except subprocess.CalledProcessError as e:
            err = e.output.decode() if e.output else str(e)
            print(f"[GIT-WARN] Attempt {attempt+1} failed: {err}")
            time.sleep(2)
    raise RuntimeError(f"Git failed: {' '.join(cmd)}")

def hash_str(s):
    return hashlib.md5(s.encode("utf-8", errors="ignore")).hexdigest()

def get_dir_size_mb(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total / (1024 * 1024)

def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "stream_id": "political-wire",
        "github_user": GITHUB_USER,
        "base_vault_name": "political-wire-vault",
        "active_vault": "political-wire-vault-1",
        "active_index": 1,
        "max_size_mb": 450,
        "max_articles": 400000,
        "rollover_history": [
            {
                "vault": "political-wire-vault-1",
                "index": 1,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "ACTIVE"
            }
        ]
    }

def save_manifest(manifest):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def github_api_request(endpoint, pat, method="GET", data=None):
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Political-Intelligence-Harvester"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", errors="ignore"))
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        print(f"[GH-API-WARN] {endpoint} error: {e}")
        return 500, {}

def ensure_vault_exists(vault_name, pat):
    status, _ = github_api_request(f"repos/{GITHUB_USER}/{vault_name}", pat, method="GET")
    if status == 200:
        return True
    print(f"[ROLLOVER-PROVISION] Creating new private vault: {vault_name} on GitHub...")
    payload = {
        "name": vault_name,
        "private": True,
        "description": f"Automated Political Intelligence Partition Vault: {vault_name}"
    }
    status, _ = github_api_request("user/repos", pat, method="POST", data=payload)
    if status in (200, 201):
        print(f"[ROLLOVER-PROVISION] Successfully created private vault {vault_name}!")
        time.sleep(3)
        return True
    print(f"[ROLLOVER-ERROR] Failed to create repo {vault_name}, status: {status}")
    return False

def clean_rss_description(raw_desc):
    if not raw_desc:
        return ""
    try:
        soup = BeautifulSoup(raw_desc, "html.parser")
        for tag in soup(["script", "style", "font"]):
            tag.decompose()
        txt = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", txt).strip()
    except Exception:
        clean = re.sub(r"<[^>]+>", " ", raw_desc)
        return re.sub(r"\s+", " ", clean).strip()

def resolve_real_url(url):
    if "news.google.com" in url and HAS_GNEWS_DECODER:
        try:
            res = gnewsdecoder(url, timeout=4.0)
            if isinstance(res, dict) and res.get("success") and res.get("decoded_url"):
                return res["decoded_url"]
        except Exception:
            pass
    return url

def extract_article_body(url, timeout=5.0):
    resolved = resolve_real_url(url)
    try:
        req = urllib.request.Request(resolved, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "svg", "noscript", "button", "iframe"]):
                tag.decompose()

            def is_valid_paragraph(p_text):
                t_low = p_text.lower()
                if len(p_text.strip()) < 35:
                    return False
                if any(b in t_low for b in [
                    "click here for", "subscribe to", "newsletter", "follow us on",
                    "telegram channel", "all rights reserved", "terms of service", "cookie settings"
                ]):
                    return False
                return True

            for sel in ['article', '[itemprop="articleBody"]', 'div[class*="storycontent"]', 'div[class*="storydetail"]', 'div[class*="article-body"]', 'div[class*="arttext"]', 'div[class*="content-inner"]', 'div[class*="post-content"]', 'div[class*="entry-content"]']:
                container = soup.select_one(sel)
                if container:
                    ps = [p.get_text(separator=" ", strip=True) for p in container.find_all("p") if is_valid_paragraph(p.get_text(strip=True))]
                    if len(ps) >= 2:
                        body = "\n\n".join(ps)
                        wc = len(body.split())
                        if wc >= 50:
                            return True, body, wc, resolved

            ps = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p") if is_valid_paragraph(p.get_text(strip=True))]
            if len(ps) >= 2:
                body = "\n\n".join(ps)
                wc = len(body.split())
                if wc >= 50:
                    return True, body, wc, resolved
    except Exception:
        pass
    return False, None, 0, resolved

def fetch_feed(feed_info):
    name = feed_info["source"]
    url = feed_info["url"]
    items_out = []
    try:
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)

            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                pubDate = item.find("pubDate")
                desc = item.find("description")

                t_text = title.text.strip() if title is not None and title.text else ""
                l_text = link.text.strip() if link is not None and link.text else ""
                d_text = desc.text.strip() if desc is not None and desc.text else ""
                p_text = pubDate.text.strip() if pubDate is not None and pubDate.text else ""

                if t_text and (l_text or d_text):
                    clean_sum = clean_rss_description(d_text)
                    art_id = hash_str(f"{t_text}_{l_text}")
                    analysis = analyze_political_headline(t_text)

                    items_out.append({
                        "id": art_id,
                        "source": name,
                        "title": t_text,
                        "url": l_text,
                        "resolved_url": l_text,
                        "clean_summary": clean_sum,
                        "raw_summary": d_text,
                        "full_text": None,
                        "has_full_text": False,
                        "word_count": len(clean_sum.split()) if clean_sum else 0,
                        "published_at": p_text,
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                        "political_institutions": analysis["institutions"],
                        "political_parties": analysis["parties"],
                        "event_category": analysis["events"],
                        "impacted_sectors": analysis["impacted_sectors"],
                        "urgency": analysis["urgency"]
                    })
    except Exception as e:
        print(f"  [WARN] Failed to fetch {name}: {e}")
    return items_out

def check_and_perform_rollover(manifest, current_vault, temp_dir, ckpt, pat, seen_hashes):
    size_mb = get_dir_size_mb(temp_dir)
    articles_ingested = ckpt.get("articles_ingested", 0)
    max_mb = manifest.get("max_size_mb", 450)
    max_arts = manifest.get("max_articles", 400000)

    if size_mb < max_mb and articles_ingested < max_arts:
        return manifest, current_vault, temp_dir, ckpt

    print(f"\n[ROLLOVER-TRIGGER] Vault {current_vault} reached {size_mb:.2f} MB / {articles_ingested:,} articles!")
    next_index = manifest.get("active_index", 1) + 1
    next_vault = f"{manifest.get('base_vault_name', 'political-wire-vault')}-{next_index}"

    ckpt["rollover_status"] = "ARCHIVED_FULL"
    ckpt["next_vault"] = next_vault
    ckpt["archived_at"] = datetime.now(timezone.utc).isoformat()
    ckpt_path = os.path.join(temp_dir, "checkpoint.json")
    with open(ckpt_path, "w", encoding="utf-8") as f:
        json.dump(ckpt, f, indent=2)

    safe_git(["git", "config", "user.name", "PoliticalBot"], cwd=temp_dir)
    safe_git(["git", "config", "user.email", "bot@intelligence.internal"], cwd=temp_dir)
    safe_git(["git", "add", "-A"], cwd=temp_dir)
    safe_git(["git", "commit", "-m", f"[ROLLOVER-ARCHIVE] Archive {current_vault} [skip ci]"], cwd=temp_dir)
    safe_git(["git", "push", "origin", "main"], cwd=temp_dir)

    ensure_vault_exists(next_vault, pat)
    temp_next = f"temp_{next_vault}"
    if os.path.exists(temp_next):
        subprocess.run(["rm", "-rf", temp_next])

    remote_next = f"https://x-access-token:{pat}@github.com/{GITHUB_USER}/{next_vault}.git"
    safe_git(["git", "clone", "--depth", "1", remote_next, temp_next], cwd=".")

    new_ckpt = {
        "vault": next_vault,
        "vault_index": next_index,
        "previous_vault": current_vault,
        "articles_ingested": 0,
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    with open(os.path.join(temp_next, "checkpoint.json"), "w", encoding="utf-8") as f:
        json.dump(new_ckpt, f, indent=2)

    with open(os.path.join(temp_next, "seen_hashes.json"), "w", encoding="utf-8") as f:
        json.dump(list(seen_hashes)[-50000:], f)

    safe_git(["git", "config", "user.name", "PoliticalBot"], cwd=temp_next)
    safe_git(["git", "config", "user.email", "bot@intelligence.internal"], cwd=temp_next)
    safe_git(["git", "add", "-A"], cwd=temp_next)
    safe_git(["git", "commit", "-m", f"[INIT-VAULT] Initialize active political partition {next_vault} [skip ci]"], cwd=temp_next)
    safe_git(["git", "push", "origin", "main"], cwd=temp_next)

    manifest["active_vault"] = next_vault
    manifest["active_index"] = next_index
    manifest["rollover_history"].append({
        "vault": next_vault,
        "index": next_index,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "ACTIVE"
    })
    save_manifest(manifest)
    subprocess.run(["rm", "-rf", temp_dir])
    return manifest, next_vault, temp_next, new_ckpt

def main():
    pat = os.environ.get("VAULT_PAT")
    if not pat:
        print("[ERROR] VAULT_PAT not set!")
        sys.exit(1)

    manifest = load_manifest()
    current_vault = manifest.get("active_vault", "political-wire-vault-1")
    print(f"[INIT] Active Political Partition: {current_vault} (Account: {GITHUB_USER})")

    remote = f"https://x-access-token:{pat}@github.com/{GITHUB_USER}/{current_vault}.git"
    temp_dir = f"temp_{current_vault}"
    if os.path.exists(temp_dir):
        subprocess.run(["rm", "-rf", temp_dir])

    safe_git(["git", "clone", "--depth", "1", remote, temp_dir], cwd=".")

    ckpt_path = os.path.join(temp_dir, "checkpoint.json")
    with open(ckpt_path, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    seen_path = os.path.join(temp_dir, "seen_hashes.json")
    seen_hashes = set()
    if os.path.exists(seen_path):
        try:
            with open(seen_path, "r", encoding="utf-8") as f:
                seen_hashes = set(json.load(f))
        except Exception:
            pass

    manifest, current_vault, temp_dir, ckpt = check_and_perform_rollover(manifest, current_vault, temp_dir, ckpt, pat, seen_hashes)

    size_mb = get_dir_size_mb(temp_dir)
    print(f"[STATUS] Active: {current_vault} | Ingested: {ckpt.get('articles_ingested', 0):,} | Size: {size_mb:.2f} MB | Seen Cache: {len(seen_hashes):,}")

    new_articles = []
    print(f"\n[STREAM] Polling {len(POLITICAL_FEEDS)} real-time political & policy feeds...")
    for feed in POLITICAL_FEEDS:
        t0 = time.time()
        feed_items = fetch_feed(feed)
        dt = time.time() - t0

        fresh_in_feed = 0
        for item in feed_items:
            h = item["id"]
            if h not in seen_hashes:
                seen_hashes.add(h)
                new_articles.append(item)
                fresh_in_feed += 1

        print(f"  ✓ {feed['source']:32} : {len(feed_items):2d} items ({fresh_in_feed} fresh) in {dt:.2f}s")

    print(f"\n[SUMMARY] Discovered {len(new_articles):,} fresh political stories in this cycle!")

    if new_articles:
        print(f"[BODY-PARSER] Running second-stage full-text parser for {len(new_articles)} political articles...")
        full_text_count = 0
        snippet_count = 0

        def enrich_item(item):
            success, body, wc, resolved = extract_article_body(item["url"], timeout=5.0)
            item["resolved_url"] = resolved
            if success and body:
                item["full_text"] = body
                item["has_full_text"] = True
                item["word_count"] = wc
                return True
            else:
                item["full_text"] = None
                item["has_full_text"] = False
                item["word_count"] = len(item["clean_summary"].split()) if item["clean_summary"] else 0
                return False

        t_start = time.time()
        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_item = {executor.submit(enrich_item, it): it for it in new_articles}
            for fut in as_completed(future_to_item):
                if fut.result():
                    full_text_count += 1
                else:
                    snippet_count += 1

        enrich_time = time.time() - t_start
        print(f"  ✓ Full-Text Enriched: {full_text_count}/{len(new_articles)} articles in {enrich_time:.2f}s | Snippets: {snippet_count}")

        now = datetime.now(timezone.utc)
        day_dir = os.path.join(temp_dir, "data", now.strftime("%Y-%m-%d"))
        os.makedirs(day_dir, exist_ok=True)

        chunk_file = f"politics_{now.strftime('%H-%M-%S')}.json.gz"
        chunk_path = os.path.join(day_dir, chunk_file)

        comp = gzip.compress(json.dumps(new_articles, ensure_ascii=False, indent=2).encode("utf-8"))
        with open(chunk_path, "wb") as f:
            f.write(comp)

        total_ingested = ckpt.get("articles_ingested", 0) + len(new_articles)
        full_text_total = ckpt.get("full_text_articles", 0) + full_text_count
        new_size_mb = get_dir_size_mb(temp_dir)

        ckpt["articles_ingested"] = total_ingested
        ckpt["full_text_articles"] = full_text_total
        ckpt["vault_size_mb"] = round(new_size_mb, 2)
        ckpt["last_stream_time"] = now.isoformat()
        ckpt["sources_monitored"] = len(POLITICAL_FEEDS)

        ckpt_path = os.path.join(temp_dir, "checkpoint.json")
        with open(ckpt_path, "w", encoding="utf-8") as f:
            json.dump(ckpt, f, indent=2)

        trimmed_hashes = list(seen_hashes)[-50000:]
        with open(seen_path, "w", encoding="utf-8") as f:
            json.dump(trimmed_hashes, f)

        safe_git(["git", "config", "user.name", "PoliticalBot"], cwd=temp_dir)
        safe_git(["git", "config", "user.email", "political@intelligence.internal"], cwd=temp_dir)
        safe_git(["git", "add", "-A"], cwd=temp_dir)

        commit_msg = f"[POLITICAL-WIRE] Ingest +{len(new_articles):,} items ({full_text_count} FullText) | Vault: {current_vault} (Total: {total_ingested:,}) [skip ci]"
        safe_git(["git", "commit", "-m", commit_msg], cwd=temp_dir)

        print(f"[PUSH] Pushing to {current_vault} on {GITHUB_USER}...")
        safe_git(["git", "push", "origin", "main"], cwd=temp_dir)
        print(f"[SUCCESS] {commit_msg}")
    else:
        print("[INFO] No new breaking political stories in this cycle.")

    subprocess.run(["rm", "-rf", temp_dir])

if __name__ == "__main__":
    main()

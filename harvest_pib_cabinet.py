#!/usr/bin/env python3
"""
Sovereign PIB & Cabinet Decision Deep Archive Harvester
Extracts, structures, and vaults official Press Information Bureau releases,
Cabinet Committee on Economic Affairs (CCEA) decisions, and PMO directives.
"""

import os
import sys
import json
import gzip
import time
import subprocess
import urllib.request
import urllib.error
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

from political_entity_db import analyze_political_headline

GITHUB_USER = "ParshantKumar2007"
VAULT_PREFIX = "pib-cabinet-archive-vault"
MANIFEST_FILE = "pib_vault_rollover_manifest.json"

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

def github_api_request(endpoint, pat, method="GET", data=None):
    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PIB-Cabinet-Harvester"
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
        "description": f"Automated PIB Cabinet Archive Partition Vault: {vault_name}"
    }
    status, _ = github_api_request("user/repos", pat, method="POST", data=payload)
    if status in (200, 201):
        print(f"[ROLLOVER-PROVISION] Successfully created private vault {vault_name}!")
        time.sleep(3)
        return True
    print(f"[ROLLOVER-ERROR] Failed to create repo {vault_name}, status: {status}")
    return False

def load_manifest():
    if os.path.exists(MANIFEST_FILE):
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "stream_id": "pib-cabinet-archive",
        "github_user": GITHUB_USER,
        "base_vault_name": VAULT_PREFIX,
        "active_vault": f"{VAULT_PREFIX}-1",
        "active_index": 1,
        "max_size_mb": 450,
        "max_articles": 400000,
        "rollover_history": [
            {
                "vault": f"{VAULT_PREFIX}-1",
                "index": 1,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "ACTIVE"
            }
        ]
    }

def save_manifest(manifest):
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def fetch_pib_release(prid, timeout=6.0):
    url = f"https://pib.gov.in/PressReleasePage.aspx?PRID={prid}"
    try:
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            html = resp.read().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")

            min_div = soup.find("div", class_="MinistryNameSubhead")
            title_div = soup.find("div", class_="event-heading-background")
            date_div = soup.find("div", class_="ReleaseDateSubHeaddateTime")
            content_div = soup.find("div", class_="innner-page-main-about-us-content-right-part") or soup.find("div", class_="ReleaseContentText")

            ministry = min_div.get_text(strip=True) if min_div else "Government of India"
            title = title_div.get_text(strip=True) if title_div else ""
            date_text = date_div.get_text(strip=True) if date_div else ""

            if not title:
                h2 = soup.find("h2")
                if h2:
                    title = h2.get_text(strip=True)

            if not title:
                return None

            # Check if there is an English translation link if title is in non-English
            english_prid = None
            rl_div = soup.find("div", class_="ReleaseLang")
            if rl_div:
                for a in rl_div.find_all("a"):
                    if "english" in a.get_text(strip=True).lower():
                        m = re.search(r"PRID=(\d+)", a.get("href", ""))
                        if m:
                            english_prid = int(m.group(1))

            # Extract paragraphs
            paragraphs = []
            if content_div:
                for p in content_div.find_all(["p", "div"]):
                    txt = p.get_text(strip=True)
                    if len(txt) > 30 and not any(skip in txt.lower() for skip in ["विज्ञप्ति को इन भाषाओं", "visitors counter", "share on", "facebook", "twitter"]):
                        paragraphs.append(txt)

            # Deduplicate paragraphs preserving order
            seen_p = set()
            clean_paragraphs = []
            for p in paragraphs:
                if p not in seen_p:
                    seen_p.add(p)
                    clean_paragraphs.append(p)

            body_text = "\n\n".join(clean_paragraphs)
            word_count = len(body_text.split())

            # Entity analysis
            analysis = analyze_political_headline(f"{ministry}: {title}")

            return {
                "prid": prid,
                "url": url,
                "ministry": ministry,
                "title": title,
                "posted_date": date_text,
                "has_full_text": word_count > 30,
                "word_count": word_count,
                "full_text": body_text if word_count > 30 else None,
                "english_prid": english_prid,
                "political_institutions": analysis["institutions"],
                "political_parties": analysis["parties"],
                "event_category": analysis["events"],
                "impacted_sectors": analysis["impacted_sectors"],
                "urgency": analysis["urgency"],
                "harvested_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception:
        return None

def check_and_perform_rollover(manifest, current_vault, temp_dir, ckpt, pat):
    size_mb = get_dir_size_mb(temp_dir)
    articles_ingested = ckpt.get("articles_ingested", 0)
    max_mb = manifest.get("max_size_mb", 450)
    max_arts = manifest.get("max_articles", 400000)

    if size_mb < max_mb and articles_ingested < max_arts:
        return manifest, current_vault, temp_dir, ckpt

    print(f"\n[PIB-ROLLOVER] Vault {current_vault} reached {size_mb:.2f} MB / {articles_ingested:,} releases!")
    next_index = manifest.get("active_index", 1) + 1
    next_vault = f"{manifest.get('base_vault_name', VAULT_PREFIX)}-{next_index}"

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
        "current_prid": ckpt.get("current_prid", 2336045),
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    with open(os.path.join(temp_next, "checkpoint.json"), "w", encoding="utf-8") as f:
        json.dump(new_ckpt, f, indent=2)

    safe_git(["git", "config", "user.name", "PoliticalBot"], cwd=temp_next)
    safe_git(["git", "config", "user.email", "bot@intelligence.internal"], cwd=temp_next)
    safe_git(["git", "add", "-A"], cwd=temp_next)
    safe_git(["git", "commit", "-m", f"[INIT-VAULT] Initialize active PIB archive {next_vault} [skip ci]"], cwd=temp_next)
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

def harvest_pib_batch(start_prid, count=250, workers=8):
    prids_to_fetch = list(range(start_prid, start_prid - count, -1))
    results = []

    print(f"[PIB-HARVEST] Fetching {len(prids_to_fetch)} PRIDs (from {start_prid} down to {start_prid - count + 1}) with {workers} workers...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_prid = {executor.submit(fetch_pib_release, pid): pid for pid in prids_to_fetch}
        for fut in as_completed(future_to_prid):
            res = fut.result()
            if res:
                results.append(res)

    dt = time.time() - t0
    print(f"[PIB-HARVEST] Successfully structured {len(results)}/{count} releases in {dt:.2f}s ({len(results)/dt:.1f} rel/s)")
    results.sort(key=lambda x: x["prid"], reverse=True)
    return results, start_prid - count

def main():
    pat = os.environ.get("VAULT_PAT")
    if not pat:
        print("[ERROR] VAULT_PAT not set!")
        sys.exit(1)

    manifest = load_manifest()
    current_vault = manifest.get("active_vault", f"{VAULT_PREFIX}-1")
    print(f"[INIT] Active PIB Archive Partition: {current_vault} (Account: {GITHUB_USER})")

    remote = f"https://x-access-token:{pat}@github.com/{GITHUB_USER}/{current_vault}.git"
    temp_dir = f"temp_{current_vault}"
    if os.path.exists(temp_dir):
        subprocess.run(["rm", "-rf", temp_dir])

    safe_git(["git", "clone", "--depth", "1", remote, temp_dir], cwd=".")

    ckpt_path = os.path.join(temp_dir, "checkpoint.json")
    with open(ckpt_path, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    manifest, current_vault, temp_dir, ckpt = check_and_perform_rollover(manifest, current_vault, temp_dir, ckpt, pat)

    current_prid = ckpt.get("current_prid", 2336045)
    print(f"[STATUS] Vault: {current_vault} | Ingested: {ckpt.get('articles_ingested', 0):,} | Current PRID cursor: {current_prid}")

    # Harvest a batch of 250 releases
    batch_releases, next_prid = harvest_pib_batch(current_prid, count=250, workers=8)

    if batch_releases:
        now = datetime.now(timezone.utc)
        data_dir = os.path.join(temp_dir, "data", now.strftime("%Y-%m"))
        os.makedirs(data_dir, exist_ok=True)

        chunk_file = f"pib_{batch_releases[-1]['prid']}_{batch_releases[0]['prid']}.json.gz"
        chunk_path = os.path.join(data_dir, chunk_file)

        comp = gzip.compress(json.dumps(batch_releases, ensure_ascii=False, indent=2).encode("utf-8"))
        with open(chunk_path, "wb") as f:
            f.write(comp)

        total_ingested = ckpt.get("articles_ingested", 0) + len(batch_releases)
        full_text_count = sum(1 for r in batch_releases if r.get("has_full_text"))
        new_size_mb = get_dir_size_mb(temp_dir)

        ckpt["articles_ingested"] = total_ingested
        ckpt["full_text_articles"] = ckpt.get("full_text_articles", 0) + full_text_count
        ckpt["current_prid"] = next_prid
        ckpt["vault_size_mb"] = round(new_size_mb, 2)
        ckpt["last_harvest_time"] = now.isoformat()

        with open(ckpt_path, "w", encoding="utf-8") as f:
            json.dump(ckpt, f, indent=2)

        safe_git(["git", "config", "user.name", "PoliticalBot"], cwd=temp_dir)
        safe_git(["git", "config", "user.email", "pib@intelligence.internal"], cwd=temp_dir)
        safe_git(["git", "add", "-A"], cwd=temp_dir)

        commit_msg = f"[PIB-ARCHIVE] Ingest +{len(batch_releases)} releases ({full_text_count} FullText) | PRIDs {next_prid+1}-{current_prid} (Total: {total_ingested:,}) [skip ci]"
        safe_git(["git", "commit", "-m", commit_msg], cwd=temp_dir)

        print(f"[PUSH] Pushing batch to {current_vault} on {GITHUB_USER}...")
        safe_git(["git", "push", "origin", "main"], cwd=temp_dir)
        print(f"[SUCCESS] {commit_msg}")
    else:
        print("[INFO] No releases found in current PRID range.")

    subprocess.run(["rm", "-rf", temp_dir])

if __name__ == "__main__":
    main()

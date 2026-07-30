"""
scrape_foundational_trials.py

Scrapes https://criticalcarereviews.com/collections/foundational-trials
and saves each trial as structured JSON under trials_database/{System}/{Name}.json
"""

import argparse
import json
import os
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://criticalcarereviews.com"
LISTING_URL = f"{BASE_URL}/collections/foundational-trials"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trials_database")
DELAY = 1.0
VALID_SYSTEMS = {
    "Neuro", "Circulatory", "Resuscitation", "Airway", "Respiratory",
    "Gastrointestinal", "Nutrition", "Liver", "Renal", "Haematology",
    "Sepsis", "Trauma", "Endocrine", "Miscellaneous",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def sanitize_filename(name):
    name = name.strip().replace(" ", "_")
    name = re.sub(r'[<>:"/\\|?*]', "-", name)
    name = re.sub(r"-+", "-", name)
    name = name.strip("-")
    return name if name else "untitled"


def fetch_soup(url):
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_listing(soup):
    sections = []
    for h2 in soup.find_all("h2"):
        section_id = h2.get("id")
        if section_id not in VALID_SYSTEMS:
            continue

        grid = h2.find_next("div", class_=lambda c: c and "uk-child-width-1-" in (c or ""))
        if not grid:
            continue

        trials = []
        for card in grid.find_all("div", class_="el-item"):
            a_tag = card.find("a", href=True)
            h3 = card.find("h3")
            p_tag = card.find("p")

            name = h3.get_text(strip=True) if h3 else ""
            href = a_tag["href"] if a_tag else None
            description = p_tag.get_text(strip=True) if p_tag else ""

            if href and not href.startswith("http"):
                href = BASE_URL + href

            trials.append({
                "name": name,
                "url": href,
                "description": description,
            })

        sections.append((section_id, trials))
    return sections


def extract_list_items(ul_tag, indent=0):
    prefix = "  " * indent
    lines = []
    for li in ul_tag.find_all("li", recursive=False):
        bullet_grid = li.find("div", class_="ccr-bullet-grid")
        if bullet_grid:
            lines.extend(extract_bullet_grid(bullet_grid, indent))
        else:
            text = li.get_text(strip=True)
            if text:
                lines.append(f"{prefix}- {text}")
        sublist = li.find("ul", class_="ccr-sublist")
        if sublist:
            lines.extend(extract_list_items(sublist, indent + 1))
    return lines


def extract_bullet_grid(div, indent=0):
    prefix = "  " * indent
    lines = []
    for label in div.find_all("div", class_="ccr-bullet-label"):
        value_div = label.find_next_sibling("div")
        if value_div:
            sublist = value_div.find("ul", class_="ccr-sublist")
            if sublist:
                flat = " ".join(value_div.stripped_strings)
                lines.append(f"{prefix}{label.get_text(strip=True)}: {flat.strip()}")
                lines.extend(extract_list_items(sublist, indent + 1))
            else:
                lines.append(
                    f"{prefix}{label.get_text(strip=True)}: "
                    f"{value_div.get_text(' ', strip=True)}"
                )
        else:
            lines.append(f"{prefix}{label.get_text(strip=True)}")
    return lines


def extract_table(table):
    lines = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all(["th", "td"])]
        lines.append(" | ".join(cells))
    return lines


def extract_section_text(elements):
    lines = []
    for el in elements:
        if not isinstance(el, Tag):
            continue
        classes = el.get("class", [])
        if el.name == "ul" and "ccr-list" in classes:
            lines.extend(extract_list_items(el, 0))
        elif el.name == "div" and "ccr-bullet-grid" in classes:
            lines.extend(extract_bullet_grid(el))
        elif el.name == "table" and "ccr-table" in classes:
            lines.extend(extract_table(el))
        elif el.name == "p":
            text = el.get_text(strip=True)
            if text:
                lines.append(text)
        elif el.name == "div" and "ccr-black-box" in classes:
            lines.append("")
            h3 = el.find("h3")
            if h3:
                lines.append(h3.get_text(strip=True))
            for sub in el.children:
                if isinstance(sub, Tag):
                    if sub.name == "p":
                        lines.append(sub.get_text(strip=True))
                    elif sub.name == "ul":
                        lines.extend(extract_list_items(sub, 1))
            lines.append("")
    return "\n".join(lines).strip()


def parse_trial_detail(soup):
    result = {}
    cit_div = soup.find("div", id="Citation")
    if cit_div:
        a_tag = cit_div.find("a")
        if a_tag:
            href = a_tag.get("href", "")
            if href and not href.startswith("http"):
                href = BASE_URL + href
            result["doi"] = href
        result["citation"] = cit_div.get_text(" ", strip=True)

    full_name_h2 = soup.find("h2", class_="uk-heading-medium")
    if full_name_h2:
        a_tag = full_name_h2.find("a")
        if a_tag:
            a_tag.extract()
        text = full_name_h2.get_text(strip=True)
        if text:
            result["full_name"] = text

    wrap = soup.find("div", class_="ccr-wrap")
    if wrap:
        section_map = {}
        current_id = None
        current_els = []
        for child in wrap.children:
            if not isinstance(child, Tag):
                continue
            if child.name == "h2" and "ccr-h2" in child.get("class", []):
                if current_id:
                    section_map[current_id] = extract_section_text(current_els)
                raw = child.get("id", "") or child.get_text(strip=True)
                current_id = raw.lower().replace(" ", "_").replace("&", "and")
                current_els = []
            elif child.name == "div" and "ccr-rule" in child.get("class", []):
                continue
            elif current_id:
                current_els.append(child)
        if current_id:
            section_map[current_id] = extract_section_text(current_els)
        result["sections"] = section_map
    return result


def save_trial(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_existing_trial_names():
    """Build a set of lowercase trial names already in trials_database/."""
    names = set()
    for root, _dirs, files in os.walk(OUTPUT_DIR):
        for f in files:
            if not f.endswith(".json"):
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                name = data.get("name", "").strip().lower()
                if name:
                    names.add(name)
            except Exception:
                pass
    return names


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape foundational trials from criticalcarereviews.com"
    )
    parser.add_argument(
        "--newtrials",
        action="store_true",
        help="Only scrape trials not yet in the database (skip existing ones)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("Fetching listing page...")
    soup = fetch_soup(LISTING_URL)
    sections = parse_listing(soup)
    print(f"Found {len(sections)} system sections")

    existing_names = get_existing_trial_names() if args.newtrials else set()

    total = sum(len(tr) for _, tr in sections)
    done = 0
    errors = []
    skipped = 0

    for system_name, trials in sections:
        system_dir = os.path.join(OUTPUT_DIR, system_name)
        os.makedirs(system_dir, exist_ok=True)

        if args.newtrials:
            new_in_system = [t for t in trials if t["name"].strip().lower() not in existing_names]
            old_in_system = [t for t in trials if t["name"].strip().lower() in existing_names]
            if old_in_system:
                print(f"\n  {system_name}: {len(new_in_system)} new, {len(old_in_system)} already exist")
            else:
                print(f"\n  {system_name} ({len(new_in_system)} new)")
            trials_to_process = new_in_system
        else:
            trials_to_process = trials
            print(f"\n{'='*60}")
            print(f"  {system_name} ({len(trials)} trials)")
            print(f"{'='*60}")

        for trial in trials_to_process:
            done += 1
            name = trial["name"]
            base = sanitize_filename(name)
            fname = base + ".json"
            fpath = os.path.join(system_dir, fname)
            counter = 1
            while os.path.exists(fpath):
                fname = f"{base}_{counter}.json"
                fpath = os.path.join(system_dir, fname)
                counter += 1

            data = {
                "id": sanitize_filename(name),
                "name": name,
                "system": system_name,
                "citation_text": trial["description"],
                "url": trial["url"],
                "scraped_at": datetime.now().isoformat(),
            }

            if trial["url"]:
                print(f"  [{done}/{total}] {name} ...", end=" ", flush=True)
                try:
                    detail_soup = fetch_soup(trial["url"])
                    detail = parse_trial_detail(detail_soup)
                    data.update(detail)
                    save_trial(fpath, data)
                    print("OK")
                except Exception as e:
                    msg = f"{name} ({trial['url']}): {e}"
                    errors.append(msg)
                    print(f"FAILED - {e}")
                    save_trial(fpath, data)
                time.sleep(DELAY)
            else:
                print(f"  [{done}/{total}] {name} (no detail page)")
                save_trial(fpath, data)

    print(f"\n{'='*60}")
    print(f"  Complete! {done} trials saved under {OUTPUT_DIR}")
    if args.newtrials:
        skipped = sum(
            1 for _, tr in sections
            for t in tr if t["name"].strip().lower() in existing_names
        )
        print(f"  Skipped (already exist): {skipped}")
    if errors:
        print(f"  Errors ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

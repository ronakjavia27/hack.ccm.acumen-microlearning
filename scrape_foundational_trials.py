"""
scrape_foundational_trials.py

Scrapes https://criticalcarereviews.com/collections/foundational-trials
and saves each trial as structured JSON under trials_database/{System}/{Name}.json
"""

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


def main():
    print("Fetching listing page...")
    soup = fetch_soup(LISTING_URL)
    sections = parse_listing(soup)
    print(f"Found {len(sections)} system sections")

    total = sum(len(tr) for _, tr in sections)
    done = 0
    errors = []

    for system_name, trials in sections:
        system_dir = os.path.join(OUTPUT_DIR, system_name)
        os.makedirs(system_dir, exist_ok=True)
        print(f"\n{'='*60}")
        print(f"  {system_name} ({len(trials)} trials)")
        print(f"{'='*60}")

        for trial in trials:
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
    if errors:
        print(f"  Errors ({len(errors)}):")
        for e in errors:
            print(f"    - {e}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

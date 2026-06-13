"""
TENDER SNIPER - LPSE SCRAPER
Target: LPSE Provinsi Jawa Timur (spse.inaproc.id/jatimprov)
Filter: Pagu < Rp 200.000.000, Kategori: Barang/Jasa Lainnya/Konstruksi
Output: List of dictionaries
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time

# CONFIGURATION
LPSE_BASE_URL = "https://spse.inaproc.id/jatimprov"
LELANG_LIST_URL = f"{LPSE_BASE_URL}/lelang"
MAX_PAGU = 200_000_000  # Rp 200 juta
ALLOWED_KATEGORI = [
    "Barang",
    "Jasa Lainnya", 
    "Pekerjaan Konstruksi",
    "Jasa Konsultansi Badan Usaha Konstruksi",
    "Jasa Konsultansi Badan Usaha Non Konstruksi"
]
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1'
}

def parse_rupiah(text):
    """Parse 'Rp. 170,000,000.00' -> 170000000 integer"""
    if not text:
        return 0
    # Remove Rp, dots, spaces, 'Rp.'
    cleaned = re.sub(r'[Rp.\s]', '', text)
    # Remove everything after comma if exists
    cleaned = cleaned.split(',')[0] if ',' in cleaned else cleaned
    try:
        return int(cleaned)
    except:
        return 0

def parse_tanggal(text):
    """Parse '25-05-2026 11:00 s/d 07-07-2026 15:59' -> return tanggal tutup"""
    if not text:
        return "N/A"
    # Extract second date (tutup)
    match = re.search(r's/d\s+(\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2})', text)
    if match:
        return match.group(1)
    # Fallback: try to find any date pattern
    dates = re.findall(r'\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}', text)
    return dates[-1] if dates else text.strip()

def scrape_tender_jatim():
    """
    Scrape tender list from LPSE Jatim
    Returns list of dict: {judul, nilai_pagu, link_detail, tanggal_tutup, kategori, satuan_kerja}
    """
    tenders = []

    try:
        print(f"[SNIPER] Fetching: {LELANG_LIST_URL}")
        resp = requests.get(LELANG_LIST_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # LPSE SPSE 4.5 structure: table with class or specific row pattern
        # Try multiple selectors as LPSE layouts vary
        rows = []

        # Strategy 1: Look for table rows with tender data
        tables = soup.find_all('table')
        for table in tables:
            tbody = table.find('tbody')
            if tbody:
                rows.extend(tbody.find_all('tr'))
            else:
                rows.extend(table.find_all('tr'))

        # Strategy 2: If no table rows, look for div-based cards
        if not rows:
            rows = soup.find_all('div', class_=re.compile(r'lelang|tender|paket', re.I))

        print(f"[SNIPER] Found {len(rows)} potential rows/cards")

        for row in rows:
            try:
                # Extract all text from row for analysis
                row_text = row.get_text(separator=' ', strip=True)

                # Check if this is actually a tender row (contains Rp. or kode lelang)
                if 'Rp.' not in row_text and 'HPS' not in row_text:
                    continue

                # Extract cells
                cells = row.find_all(['td', 'div'])
                cell_texts = [c.get_text(strip=True) for c in cells]

                # Find pagu value
                pagu_text = None
                for text in cell_texts:
                    if 'Rp.' in text or 'HPS' in text:
                        pagu_text = text
                        break

                if not pagu_text:
                    # Try regex on full row text
                    pagu_match = re.search(r'Rp\.?\s*[\d.,]+', row_text)
                    if pagu_match:
                        pagu_text = pagu_match.group(0)

                pagu = parse_rupiah(pagu_text)

                # FILTER 1: Pagu < 200 juta
                if pagu >= MAX_PAGU or pagu == 0:
                    continue

                # Extract title
                title = "Unknown"
                links = row.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if text and len(text) > 10 and 'lelang' in href:
                        title = text
                        detail_link = href if href.startswith('http') else f"{LPSE_BASE_URL}{href}"
                        break

                # Fallback title extraction
                if title == "Unknown":
                    # Look for longest text in cells as title
                    longest = max(cell_texts, key=len, default="")
                    if len(longest) > 15:
                        title = longest

                # Extract kategori
                kategori = "Unknown"
                for text in cell_texts:
                    for allowed in ALLOWED_KATEGORI:
                        if allowed.lower() in text.lower():
                            kategori = allowed
                            break
                    if kategori != "Unknown":
                        break

                # Extract tanggal
                tanggal_tutup = "N/A"
                for text in cell_texts:
                    if re.search(r'\d{2}-\d{2}-\d{4}', text):
                        tanggal_tutup = parse_tanggal(text)
                        break

                # Extract satuan kerja
                satker = "N/A"
                for text in cell_texts:
                    if 'Dinas' in text or 'Satuan' in text or 'SKPD' in text:
                        satker = text
                        break

                # Build detail link if not found
                if 'detail_link' not in locals():
                    detail_link = LELANG_LIST_URL

                tender = {
                    "judul": title,
                    "nilai_pagu": pagu,
                    "nilai_pagu_formatted": f"Rp {pagu:,.0f}".replace(",", "."),
                    "link_detail": detail_link,
                    "tanggal_tutup": tanggal_tutup,
                    "kategori": kategori,
                    "satuan_kerja": satker,
                    "scraped_at": datetime.now().isoformat(),
                    "source": "LPSE Provinsi Jawa Timur"
                }

                tenders.append(tender)
                print(f"[HIT] {title[:50]}... | Rp {pagu:,.0f} | {kategori}")

            except Exception as e:
                print(f"[SKIP] Row error: {e}")
                continue

        # Strategy 3: If table scraping failed, try JSON API endpoint
        if not tenders:
            print("[SNIPER] Table scraping empty, trying JSON API fallback...")
            tenders = scrape_json_api()

        print(f"\n[SNIPER] Total tenders filtered: {len(tenders)}")
        return tenders

    except Exception as e:
        print(f"[ERROR] Scrape failed: {e}")
        return []

def scrape_json_api():
    """Fallback: Try to find JSON API endpoint if available"""
    tenders = []
    try:
        # Some LPSE expose JSON endpoints
        json_url = f"{LPSE_BASE_URL}/lelang/ajax"
        resp = requests.get(json_url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                pagu = parse_rupiah(item.get('hps', '0'))
                if 0 < pagu < MAX_PAGU:
                    tenders.append({
                        "judul": item.get('nama_paket', 'Unknown'),
                        "nilai_pagu": pagu,
                        "nilai_pagu_formatted": f"Rp {pagu:,.0f}".replace(",", "."),
                        "link_detail": f"{LPSE_BASE_URL}/lelang/{item.get('kode', '')}",
                        "tanggal_tutup": item.get('tgl_tutup', 'N/A'),
                        "kategori": item.get('kategori', 'Unknown'),
                        "satuan_kerja": item.get('satuan_kerja', 'N/A'),
                        "scraped_at": datetime.now().isoformat(),
                        "source": "LPSE Provinsi Jawa Timur (API)"
                    })
    except:
        pass
    return tenders

def save_results(tenders, filename="tenders_jatim.json"):
    """Save to JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tenders, f, ensure_ascii=False, indent=2)
    print(f"[SAVE] Saved {len(tenders)} tenders to {filename}")

if __name__ == "__main__":
    results = scrape_tender_jatim()
    save_results(results)

    # Print summary
    print("\n" + "="*60)
    print("TENDER SNIPER - HASIL SCRAPE")
    print("="*60)
    for t in results[:5]:
        print(f"\n📋 {t['judul'][:60]}")
        print(f"   💰 {t['nilai_pagu_formatted']} | ⏰ Tutup: {t['tanggal_tutup']}")
        print(f"   🏗️  {t['kategori']} | 🔗 {t['link_detail'][:60]}")

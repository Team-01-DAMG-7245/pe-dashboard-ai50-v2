"""
Lab 1 — Scrape & Store
Scrapes company website pages and stores raw HTML and clean text versions.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class CompanyPageScraper:
    """Scrapes company website pages and stores them locally."""
    
    def __init__(self, data_dir: str = "../../data/raw", run_type: str = "initial"):
        """
        Initialize the scraper.
        
        Args:
            data_dir: Base directory for storing scraped data
            run_type: "initial" or "daily" to organize runs
        """
        self.data_dir = Path(data_dir)
        self.run_type = run_type
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Page types to scrape
        self.page_types = {
            'homepage': ['', '/'],
            'about': ['/about', '/about-us', '/aboutus', '/company'],
            'product': ['/product', '/products', '/platform', '/platforms', '/solutions'],
            'careers': ['/careers', '/career', '/jobs', '/join-us', '/team'],
            'blog': ['/blog', '/blogs', '/news', '/press', '/press-release', '/articles']
        }
    
    def load_companies(self, seed_file: str) -> List[Dict]:
        """Load companies from the seed JSON file."""
        seed_path = Path(seed_file)
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
        
        with open(seed_path, 'r', encoding='utf-8') as f:
            companies = json.load(f)
        
        return companies
    
    def get_company_id(self, company_name: str) -> str:
        """Generate a safe company ID from company name."""
        # Convert to lowercase, replace spaces with underscores, remove special chars
        company_id = company_name.lower()
        company_id = re.sub(r'[^a-z0-9\s]', '', company_id)
        company_id = re.sub(r'\s+', '_', company_id.strip())
        return company_id
    
    def clean_text(self, html_content: str) -> str:
        """Extract clean text from HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript", "meta", "link"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def find_page_url(self, base_url: str, paths: List[str]) -> Optional[str]:
        """Try to find a valid page URL by checking multiple path options."""
        parsed_base = urlparse(base_url)
        
        for path in paths:
            full_url = urljoin(base_url, path)
            
            try:
                response = self.session.head(full_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    return response.url  # Return final URL after redirects
            except:
                continue
        
        return None
    
    def scrape_page(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Scrape a single page and return HTML and clean text."""
        try:
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            html_content = response.text
            clean_text_content = self.clean_text(html_content)
            
            return html_content, clean_text_content
        except Exception as e:
            print(f"    ✗ Error scraping {url}: {e}")
            return None, None
    
    def scrape_company(self, company: Dict) -> Dict:
        """Scrape all pages for a single company."""
        company_name = company.get('company_name', 'Unknown')
        website = company.get('website')
        
        if not website:
            print(f"⚠️  No website URL for {company_name}, skipping...")
            return {}
        
        company_id = self.get_company_id(company_name)
        company_dir = self.data_dir / company_id / self.run_type
        company_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n[{company_name}]")
        print(f"  Company ID: {company_id}")
        print(f"  Base URL: {website}")
        
        scraped_pages = []
        
        # Scrape each page type
        for page_type, paths in self.page_types.items():
            print(f"  Scraping {page_type}...", end=' ')
            
            # Find valid URL for this page type
            page_url = self.find_page_url(website, paths)
            
            if not page_url:
                print(f"✗ Page not found")
                continue
            
            # Scrape the page
            html_content, clean_text = self.scrape_page(page_url)
            
            if not html_content:
                print(f"✗ Failed to scrape")
                continue
            
            # Save files
            timestamp = datetime.now(timezone.utc).isoformat()
            page_id = page_url.replace('/', '_').replace(':', '_').replace('?', '_').replace('&', '_')
            # Limit filename length
            if len(page_id) > 150:
                page_id = page_id[:150]
            
            # Save raw HTML
            html_file = company_dir / f"{page_type}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save clean text
            text_file = company_dir / f"{page_type}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(clean_text)
            
            # Create metadata
            metadata = {
                "company_name": company_name,
                "company_id": company_id,
                "page_type": page_type,
                "source_url": page_url,
                "crawled_at": timestamp,
                "content_length": len(html_content),
                "text_length": len(clean_text)
            }
            
            # Save metadata
            metadata_file = company_dir / f"{page_type}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            scraped_pages.append(metadata)
            print(f"✓ Saved ({len(html_content)} bytes HTML, {len(clean_text)} chars text)")
            
            # Be respectful - small delay between pages
            time.sleep(1)
        
        return {
            "company_id": company_id,
            "company_name": company_name,
            "website": website,
            "pages_scraped": len(scraped_pages),
            "pages": scraped_pages
        }
    
    def scrape_all(self, companies: List[Dict]) -> Dict:
        """Scrape all companies."""
        print(f"\n{'='*60}")
        print(f"Starting Lab 1 — Scrape & Store")
        print(f"Run Type: {self.run_type}")
        print(f"Total Companies: {len(companies)}")
        print(f"{'='*60}\n")
        
        results = {
            "run_type": self.run_type,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "total_companies": len(companies),
            "companies": []
        }
        
        successful = 0
        failed = 0
        
        for i, company in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}]", end=' ')
            
            try:
                result = self.scrape_company(company)
                if result.get('pages_scraped', 0) > 0:
                    results['companies'].append(result)
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"✗ Error processing {company.get('company_name', 'Unknown')}: {e}")
                failed += 1
            
            # Delay between companies
            time.sleep(2)
        
        results["completed_at"] = datetime.now(timezone.utc).isoformat()
        results["successful"] = successful
        results["failed"] = failed
        
        # Save summary
        summary_file = self.data_dir / f"scrape_summary_{self.run_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Summary saved to: {summary_file}")
        print(f"{'='*60}\n")
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape company website pages')
    parser.add_argument('--seed-file', default='../../data/forbes_ai50_seed.json',
                       help='Path to seed JSON file with company data')
    parser.add_argument('--data-dir', default='../../data/raw',
                       help='Base directory for storing scraped data')
    parser.add_argument('--run-type', default='initial', choices=['initial', 'daily'],
                       help='Type of run: initial or daily')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of companies to scrape (for testing)')
    
    args = parser.parse_args()
    
    scraper = CompanyPageScraper(data_dir=args.data_dir, run_type=args.run_type)
    
    # Load companies
    companies = scraper.load_companies(args.seed_file)
    
    if args.limit:
        companies = companies[:args.limit]
        print(f"⚠️  Limiting to first {args.limit} companies for testing")
    
    # Scrape all companies
    results = scraper.scrape_all(companies)
    
    return results


if __name__ == '__main__':
    main()


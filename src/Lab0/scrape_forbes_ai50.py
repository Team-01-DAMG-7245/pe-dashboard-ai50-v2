import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin
import re

class ForbesAI50Scraper:
    def __init__(self):
        self.base_url = "https://www.forbes.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def scrape_ai50_list(self) -> List[Dict]:
        """Scrape the main Forbes AI 50 list page"""
        url = "https://www.forbes.com/lists/ai50/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find Next.js data first
            companies = self._extract_from_next_data(soup)
            
            # Fallback to HTML parsing
            if not companies:
                companies = self._extract_from_html(soup)
            
            return companies
            
        except Exception as e:
            print(f"Error scraping main list: {e}")
            return []
    
    def _extract_from_next_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract from Next.js embedded data"""
        script = soup.find('script', id='__NEXT_DATA__')
        if not script:
            return []
        
        try:
            data = json.loads(script.string)
            companies = []
            
            # Navigate through the data structure
            props = data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Try different possible paths
            list_data = (
                page_props.get('listData', {}) or 
                page_props.get('list', {}) or
                page_props.get('data', {})
            )
            
            # Get items
            if isinstance(list_data, dict):
                items = (
                    list_data.get('items', []) or 
                    list_data.get('listItems', []) or
                    list_data.get('organizations', [])
                )
            else:
                items = []
            
            for item in items:
                company = self._parse_list_item(item)
                if company:
                    companies.append(company)
            
            return companies
            
        except Exception as e:
            print(f"Error parsing Next.js data: {e}")
            return []
    
    def _extract_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract from HTML structure - looks for the table format on Forbes AI 50 page"""
    companies = []
    
        # Look for links to company profiles - these are the most reliable
        # Pattern: /companies/companyname/?list=ai50
        profile_links = soup.find_all('a', href=re.compile(r'/companies/[^/]+/\?list=ai50'))
        seen_urls = set()
        
        for link in profile_links:
            href = link.get('href')
            if not href or href in seen_urls:
                continue
            seen_urls.add(href)
            
            # Extract company name from URL slug (most reliable)
            match = re.search(r'/companies/([^/]+)/', href)
            if match:
                company_slug = match.group(1)
                # Convert slug to readable name: "abridge" -> "Abridge", "figure-ai" -> "Figure AI"
                company_name = company_slug.replace('-', ' ').title()
                # Handle special cases
                company_name = company_name.replace('Ai', 'AI').replace('Hq', 'HQ')
                
                profile_url = urljoin(self.base_url, href)
                
                            companies.append({
                    'company_name': company_name,
                    'forbes_profile_url': profile_url,
                    'rank': len(companies) + 1
                })
                if len(companies) >= 50:
                    break
        
        # Fallback: Parse table structure if no links found
    if not companies:
        table = soup.find('table')
        if table:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                    if len(cells) >= 1:
                        first_cell = cells[0]
                        # Look for link in first cell
                        link = first_cell.find('a', href=re.compile(r'/companies/'))
                if link:
                            href = link.get('href')
                            match = re.search(r'/companies/([^/]+)/', href)
                            if match:
                                company_slug = match.group(1)
                                company_name = company_slug.replace('-', ' ').title().replace('Ai', 'AI')
                                profile_url = urljoin(self.base_url, href)
                                
                        companies.append({
                            'company_name': company_name,
                                    'forbes_profile_url': profile_url,
                                    'rank': len(companies) + 1
                        })
                        if len(companies) >= 50:
                            break
        
        return companies
    
    def _parse_list_item(self, item: Dict) -> Optional[Dict]:
        """Parse a single company item from JSON data"""
        try:
            # Extract profile URL
            profile_url = (
                item.get('uri') or
                item.get('url') or
                item.get('profileUrl') or
                item.get('link')
            )
            
            if profile_url and not profile_url.startswith('http'):
                profile_url = urljoin(self.base_url, profile_url)
            
            return {
                'company_name': (
                    item.get('name') or
                    item.get('organizationName') or
                    item.get('title')
                ),
                'forbes_profile_url': profile_url,
                'rank': item.get('rank') or item.get('position')
            }
        except Exception as e:
            print(f"Error parsing list item: {e}")
            return None
    
    def _parse_html_element(self, elem) -> Optional[Dict]:
        """Parse company from HTML element"""
        # Find company name
        name = None
        name_selectors = ['h2', 'h3', 'h4', 'a[class*="name"]', '[class*="title"]']
        for selector in name_selectors:
            name_elem = elem.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True)
                break
    
        # Find profile URL
        profile_url = None
        for link in elem.find_all('a', href=True):
            href = link['href']
            if '/lists/ai50/' in href and len(href.split('/')) > 4:
                profile_url = urljoin(self.base_url, href)
                break
        
        # Find rank if visible
        rank = None
        rank_elem = elem.select_one('[class*="rank"]') or elem.select_one('[class*="position"]')
        if rank_elem:
            rank_text = rank_elem.get_text(strip=True)
            rank_match = re.search(r'\d+', rank_text)
            if rank_match:
                rank = int(rank_match.group())
        
        if name or profile_url:
            return {
                'company_name': name,
                'forbes_profile_url': profile_url,
                'rank': rank
            }
        return None
    
    def scrape_company_profile(self, profile_url: str) -> Dict:
        """Scrape detailed information from a company's Forbes profile page"""
        if not profile_url:
            return {}
        
        try:
            print(f"  Scraping: {profile_url}")
            response = self.session.get(profile_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
            details = {}
            
            # Find the Stats section - look for "Stats" heading or "As of" text
            stats_container = None
            
            # Try finding by "Stats" heading
            stats_heading = soup.find(['h1', 'h2', 'h3', 'h4'], text=re.compile(r'Stats|As of', re.I))
            if stats_heading:
                # Get the next sibling or parent that contains the data
                stats_container = stats_heading.find_next(['div', 'section', 'dl', 'ul'])
                if not stats_container:
                    stats_container = stats_heading.find_parent(['div', 'section'])
            
            # If not found, look for elements containing "Industry", "Founded", "Headquarters" near each other
            if not stats_container:
                industry_elem = soup.find(text=re.compile(r'^Industry$', re.I))
                if industry_elem:
                    # Get parent that likely contains all stats
                    parent = industry_elem.find_parent(['div', 'section', 'dl', 'ul'])
                    if parent:
                        # Check if it also contains other stats
                        parent_text = parent.get_text()
                        if 'Founded' in parent_text and 'Headquarters' in parent_text:
                            stats_container = parent
            
            # Extract stats from the container
            if stats_container:
                stats_text = stats_container.get_text(separator='|SEP|')
            else:
                # Fallback: use full page but be very careful with boundaries
                stats_text = soup.get_text(separator='|SEP|')
            
            # Helper function to extract field value - stops at next field or reasonable length
            def extract_field(pattern, text, max_length=50):
                match = re.search(pattern, text, re.IGNORECASE)
                if not match:
                    return None
                value = match.group(1).strip()
                # Stop at next common field name or separator
                value = re.split(r'\|SEP\||Founded|Headquarters|Country|CEO|Employees|Industry|Forbes Lists', value)[0].strip()
                # Clean up: remove extra whitespace, keep only reasonable length
                value = ' '.join(value.split())
                if value and len(value) <= max_length and len(value) > 0:
                    return value
                return None
            
            # Extract Industry/Category - be very specific to avoid matching navigation text
            # Look for "Industry" as a label followed by the actual industry value
            # Must not be part of "SAP BrandVoice" or other navigation items
            category_patterns = [
                # Pattern: "Industry|SEP|Clinical documentation platform"
                r'(?:^|\|SEP\|)Industry[:\s]*\|SEP\|\s*([^|]+?)(?:\|SEP\|(?:Founded|Headquarters|Country|CEO|Employees)|$)',
                # Fallback: "Industry:\s*Clinical documentation platform"
                r'Industry[:\s]+\s*([^\n|]+?)(?:\n|$|\|SEP\|(?:Founded|Headquarters))',
            ]
            for pattern in category_patterns:
                category_match = re.search(pattern, stats_text, re.IGNORECASE | re.MULTILINE)
                if category_match:
                    category = category_match.group(1).strip()
                    # Clean up
                    category = ' '.join(category.split())
                    # Skip if it's clearly navigation text
                    if category and len(category) <= 100 and 'BrandVoice' not in category and 'Paid Program' not in category:
                        details['category'] = category
                        break
            
            # Extract Founded Year
            founded_match = re.search(r'Founded[:\s]*\|SEP\|\s*(\d{4})', stats_text, re.IGNORECASE)
            if founded_match:
                details['year_founded'] = int(founded_match.group(1))
            
            # Extract Headquarters - get city and potentially state/country
            hq_match = re.search(r'Headquarters[:\s]*\|SEP\|\s*([^|]+)', stats_text, re.IGNORECASE)
            if hq_match:
                hq_text = hq_match.group(1).strip()
                # Split by comma
                parts = [p.strip() for p in hq_text.split(',')]
                if parts[0] and len(parts[0]) <= 50:
                    details['hq_city'] = parts[0]
                    # If there's a second part and it's reasonable, might be state or country
                    # But prefer Country/Territory field if available
                    if len(parts) > 1 and len(parts[-1]) <= 50:
                        # Check if Country/Territory exists separately first
                        country = extract_field(r'Country/Territory[:\s]*\|SEP\|\s*([^|]+)', stats_text, max_length=50)
                        if country:
                            details['hq_country'] = country
                        else:
                            # Use last part of HQ if it looks like a country
                            potential = parts[-1]
                            if len(potential) > 3 and not potential.isdigit():
                                details['hq_country'] = potential
            
            # Extract Country/Territory if not already found
            if not details.get('hq_country'):
                country = extract_field(r'Country/Territory[:\s]*\|SEP\|\s*([^|]+)', stats_text, max_length=50)
                if country:
                    details['hq_country'] = country
            
            # Try to find website and LinkedIn links on the page
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                
                # Find LinkedIn
                if not details.get('linkedin') and 'linkedin.com/company/' in href:
                    details['linkedin'] = href if href.startswith('http') else urljoin('https://', href.lstrip('/'))
                
                # Find website (external, not Forbes, not social media)
                if not details.get('website'):
                    if (href.startswith('http') and 
                        'forbes.com' not in href and 
                        'linkedin.com' not in href and
                        'twitter.com' not in href and
                        'facebook.com' not in href and
                        'instagram.com' not in href):
                        link_text = link.get_text(strip=True).lower()
                        # Prefer links labeled as website/homepage
                        if any(word in link_text for word in ['website', 'visit', 'homepage', 'official']):
                            details['website'] = href
                            break
            
            # Add delay to be respectful
            time.sleep(0.5)
            
            return details
            
        except Exception as e:
            print(f"  Error scraping profile {profile_url}: {e}")
            return {}
    
    def _extract_profile_from_json(self, data: Dict) -> Dict:
        """Extract profile details from Next.js JSON"""
        try:
            props = data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Company data might be nested
            company_data = (
                page_props.get('organization', {}) or
                page_props.get('profile', {}) or
                page_props.get('company', {}) or
                page_props
            )
            
            # Extract details
            details = {
                'website': self._find_website(company_data),
                'linkedin': self._find_linkedin(company_data),
                'hq_city': self._find_city(company_data),
                'hq_country': self._find_country(company_data),
                'category': self._find_category(company_data),
                'description': company_data.get('description') or company_data.get('bio')
            }
            
            # Clean up None values
            return {k: v for k, v in details.items() if v}
            
        except Exception as e:
            print(f"Error extracting from profile JSON: {e}")
            return {}
    
    def _extract_profile_from_html(self, soup: BeautifulSoup) -> Dict:
        """Extract profile details from HTML"""
        details = {}
        
        # Find all links on the page
        all_links = soup.find_all('a', href=True)
        
        # Extract website (non-Forbes, non-LinkedIn link)
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True).lower()
            
            # Look for website
            if not details.get('website'):
                if (href.startswith('http') and 
                    'forbes.com' not in href and 
                    'linkedin.com' not in href and
                    ('website' in text or 'visit' in text or link.get('rel') == ['nofollow'])):
                    details['website'] = href
            
            # Look for LinkedIn
            if not details.get('linkedin'):
                if 'linkedin.com/company/' in href:
                    details['linkedin'] = href
        
        # If website not found with label, try meta tags
        if not details.get('website'):
            og_url = soup.find('meta', property='og:url')
            if og_url and og_url.get('content'):
                content = og_url['content']
                if 'forbes.com' not in content:
                    details['website'] = content
        
        # Look for location information
        location_patterns = [
            r'Headquarters[:\s]+([^,\n]+),\s*([^\n]+)',
            r'Location[:\s]+([^,\n]+),\s*([^\n]+)',
            r'Based in[:\s]+([^,\n]+),\s*([^\n]+)',
            r'HQ[:\s]+([^,\n]+),\s*([^\n]+)'
        ]
        
        page_text = soup.get_text()
        for pattern in location_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                details['hq_city'] = match.group(1).strip()
                details['hq_country'] = match.group(2).strip()
                break
        
        # Look for category/industry
        category_selectors = [
            '[class*="category"]',
            '[class*="industry"]',
            '[class*="sector"]',
            'meta[property="article:section"]',
            'meta[name="category"]'
        ]
        
        for selector in category_selectors:
            if selector.startswith('meta'):
                elem = soup.select_one(selector)
                if elem and elem.get('content'):
                    details['category'] = elem['content']
                    break
            else:
                elem = soup.select_one(selector)
                if elem:
                    details['category'] = elem.get_text(strip=True)
                    break
        
        # Look for structured data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                ld_json = json.loads(script.string)
                if isinstance(ld_json, dict):
                    if 'location' in ld_json:
                        loc = ld_json['location']
                        if isinstance(loc, dict):
                            details['hq_city'] = loc.get('addressLocality') or details.get('hq_city')
                            details['hq_country'] = loc.get('addressCountry') or details.get('hq_country')
                    
                    if 'sameAs' in ld_json:
                        for url in ld_json['sameAs']:
                            if 'linkedin.com/company/' in url:
                                details['linkedin'] = url
                            elif not details.get('website') and 'forbes.com' not in url:
                                details['website'] = url
            except:
                continue
        
        return details
    
    def _find_website(self, data: Dict) -> Optional[str]:
        """Find website URL in various fields"""
        possible_keys = ['website', 'url', 'websiteUrl', 'homepage', 'companyUrl', 'siteUrl']
        for key in possible_keys:
            if key in data and data[key]:
                url = data[key]
                if isinstance(url, str) and url.startswith('http') and 'forbes.com' not in url:
                    return url
        
        # Check in nested objects
        if 'links' in data:
            links = data['links']
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, dict):
                        url = link.get('url') or link.get('href')
                        if url and 'linkedin.com' not in url and 'forbes.com' not in url:
                            return url
        
        return None
    
    def _find_linkedin(self, data: Dict) -> Optional[str]:
        """Find LinkedIn URL"""
        possible_keys = ['linkedin', 'linkedinUrl', 'linkedIn']
        for key in possible_keys:
            if key in data and data[key]:
                return data[key]
        
        # Check social media object
        if 'socialMedia' in data:
            social = data['socialMedia']
            if isinstance(social, dict):
                return social.get('linkedin') or social.get('linkedIn')
        
        # Check links array
        if 'links' in data:
            links = data['links']
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, str) and 'linkedin.com/company/' in link:
                        return link
                    elif isinstance(link, dict):
                        url = link.get('url') or link.get('href')
                        if url and 'linkedin.com/company/' in url:
                            return url
        
        return None
    
    def _find_city(self, data: Dict) -> Optional[str]:
        """Find headquarters city"""
        # Direct keys
        if 'hqCity' in data:
            return data['hqCity']
        if 'city' in data:
            return data['city']
        
        # Nested in headquarters
        if 'headquarters' in data:
            hq = data['headquarters']
            if isinstance(hq, dict):
                return hq.get('city')
            elif isinstance(hq, str):
                # Parse "City, Country" format
                parts = hq.split(',')
                if parts:
                    return parts[0].strip()
        
        # Nested in location
        if 'location' in data:
            loc = data['location']
            if isinstance(loc, dict):
                return loc.get('city') or loc.get('addressLocality')
            elif isinstance(loc, str):
                parts = loc.split(',')
                if parts:
                    return parts[0].strip()
        
        return None
    
    def _find_country(self, data: Dict) -> Optional[str]:
        """Find headquarters country"""
        # Direct keys
        if 'hqCountry' in data:
            return data['hqCountry']
        if 'country' in data:
            return data['country']
        
        # Nested in headquarters
        if 'headquarters' in data:
            hq = data['headquarters']
            if isinstance(hq, dict):
                return hq.get('country')
            elif isinstance(hq, str):
                parts = hq.split(',')
                if len(parts) > 1:
                    return parts[-1].strip()
        
        # Nested in location
        if 'location' in data:
            loc = data['location']
            if isinstance(loc, dict):
                return loc.get('country') or loc.get('addressCountry')
            elif isinstance(loc, str):
                parts = loc.split(',')
                if len(parts) > 1:
                    return parts[-1].strip()
        
        return None
    
    def _find_category(self, data: Dict) -> Optional[str]:
        """Find company category/industry"""
        possible_keys = ['category', 'industry', 'sector', 'vertical', 'focus']
        for key in possible_keys:
            if key in data and data[key]:
                return data[key]
        
        # Check in tags or topics
        if 'tags' in data and isinstance(data['tags'], list) and data['tags']:
            return data['tags'][0]
        if 'topics' in data and isinstance(data['topics'], list) and data['topics']:
            return data['topics'][0]
        
        return None
    
    def _find_website_and_linkedin(self, company_name: str, profile_url: str = None) -> Dict:
        """Try to find website and LinkedIn URLs dynamically"""
        result = {'website': None, 'linkedin': None}
        
        # Try Wikipedia to find company website
        try:
            wiki_url = f"https://en.wikipedia.org/wiki/{company_name.replace(' ', '_')}"
            response = self.session.get(wiki_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Look for official website link in infobox
                infobox = soup.find('table', class_='infobox')
                if infobox:
                    for link in infobox.find_all('a', href=True):
                        href = link['href']
                        text = link.get_text(strip=True).lower()
                        if 'website' in text or 'official' in text:
                            if href.startswith('http'):
                                result['website'] = href
                            elif href.startswith('//'):
                                result['website'] = 'https:' + href
                        if 'linkedin.com/company/' in href:
                            result['linkedin'] = href if href.startswith('http') else 'https:' + href
                except:
                    pass
        
        # If not found, try constructing LinkedIn URL
        if not result['linkedin']:
            linkedin_slug = company_name.lower().replace(' ', '-').replace('.', '').replace('&', 'and').replace('ai ', '').replace(' ai', '').replace('hq', '')
            result['linkedin'] = f"https://www.linkedin.com/company/{linkedin_slug}/"
        
        # If website not found, try common patterns
        if not result['website']:
            company_slug = company_name.lower().replace(' ', '-').replace('.', '').replace('&', 'and')
            # Try .com first
            result['website'] = f"https://{company_slug}.com"
        
        return result
    
    def scrape_all(self) -> List[Dict]:
        """Main method: scrape list and all company profiles"""
        print("Step 1: Scraping Forbes AI 50 list...")
        companies = self.scrape_ai50_list()
        
        if not companies:
            print("Failed to scrape company list. The page structure may have changed.")
            return []
        
        print(f"Found {len(companies)} companies on the list")
        
        print("\nStep 2: Scraping individual company profiles...")
        enriched_companies = []
        
        for i, company in enumerate(companies, 1):
            company_name = company.get('company_name', 'Unknown')
            print(f"\n[{i}/{len(companies)}] Processing: {company_name}")
            
            # Get profile details
            profile_url = company.get('forbes_profile_url')
            details = {}
            if profile_url:
                details = self.scrape_company_profile(profile_url)
            
            # Find website and LinkedIn if not found
            if not details.get('website') or not details.get('linkedin'):
                url_info = self._find_website_and_linkedin(company_name, profile_url)
                if not details.get('website'):
                    details['website'] = url_info['website']
                if not details.get('linkedin'):
                    details['linkedin'] = url_info['linkedin']
            
            # Build final company object with required structure
            final_company = {
                'company_name': company_name,
                'website': details.get('website'),
                'linkedin': details.get('linkedin'),
                'hq_city': details.get('hq_city'),
                'hq_country': details.get('hq_country'),
                'category': details.get('category')
            }
            
            enriched_companies.append(final_company)
            
            # Progress update
            if i % 10 == 0:
                print(f"\n--- Progress: {i}/{len(companies)} companies processed ---")
        
        return enriched_companies


def save_to_json(companies: List[Dict], filename: str = '../../data/forbes_ai50_seed.json'):
    """Save companies to JSON file"""
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(companies)} companies to {filename}")


def main():
    scraper = ForbesAI50Scraper()
    companies = scraper.scrape_all()
    
    if companies:
        save_to_json(companies)
        
        # Print summary
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        
        complete = sum(1 for c in companies if all([
            c.get('company_name'),
            c.get('website'),
            c.get('linkedin'),
            c.get('hq_city'),
            c.get('hq_country'),
            c.get('category')
        ]))
        
        print(f"Total companies: {len(companies)}")
        print(f"Complete profiles: {complete}")
        print(f"Missing data: {len(companies) - complete}")
        
        # Show sample
        print("\n" + "="*60)
        print("SAMPLE COMPANIES")
        print("="*60)
        for company in companies[:3]:
            print(json.dumps(company, indent=2))
            print("-" * 60)
    else:
        print("\n❌ No companies were scraped. Please check the Forbes page structure.")


if __name__ == "__main__":
    main()

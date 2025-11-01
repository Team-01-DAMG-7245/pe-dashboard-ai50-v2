"""
Lab 2 - Full Load Airflow DAG for Forbes AI 50
Scrapes all companies from the seed list and stores raw data
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import time
import logging

# Configure paths - works with your existing project structure
BASE_DIR = Path(__file__).parent.parent  # Project root (where src/ and dags/ are)
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
SEED_FILE = DATA_DIR / "forbes_ai50_seed.json"

# Default arguments for the DAG
default_args = {
    'owner': 'quanta-capital',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def load_company_list(**context):
    """Load the Forbes AI 50 seed list"""
    logging.info(f"Loading company list from {SEED_FILE}")
    
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found at {SEED_FILE}")
    
    with open(SEED_FILE, 'r') as f:
        companies = json.load(f)
    
    logging.info(f"Loaded {len(companies)} companies")
    
    # Push to XCom for downstream tasks
    context['task_instance'].xcom_push(key='companies', value=companies)
    return len(companies)


def generate_company_id(company_name):
    """Generate a clean company_id from company name"""
    return company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')


def scrape_company_pages(company_data, **context):
    """
    Scrape key pages for a single company
    
    Args:
        company_data: Dict with company info including 'company_name', 'website'
    """
    company_name = company_data.get('company_name', 'Unknown')
    base_url = company_data.get('website', '')
    company_id = generate_company_id(company_name)
    
    logging.info(f"Scraping company: {company_name} ({company_id})")
    
    # Create company directory structure
    company_dir = RAW_DIR / company_id / "initial"
    company_dir.mkdir(parents=True, exist_ok=True)
    
    # Pages to scrape - try multiple common paths
    pages_config = [
        {'path': '', 'name': 'homepage'},
        {'path': '/about', 'name': 'about'},
        {'path': '/about-us', 'name': 'about'},
        {'path': '/company', 'name': 'about'},
        {'path': '/product', 'name': 'product'},
        {'path': '/products', 'name': 'product'},
        {'path': '/platform', 'name': 'platform'},
        {'path': '/solutions', 'name': 'platform'},
        {'path': '/careers', 'name': 'careers'},
        {'path': '/jobs', 'name': 'careers'},
        {'path': '/blog', 'name': 'blog'},
        {'path': '/news', 'name': 'news'},
        {'path': '/newsroom', 'name': 'news'},
    ]
    
    results = {
        'company_name': company_name,
        'company_id': company_id,
        'base_url': base_url,
        'hq_city': company_data.get('hq_city', 'Not disclosed'),
        'hq_country': company_data.get('hq_country', 'Not disclosed'),
        'category': company_data.get('category', 'Not disclosed'),
        'linkedin': company_data.get('linkedin', 'Not disclosed'),
        'crawled_at': datetime.utcnow().isoformat() + 'Z',
        'pages_scraped': [],
        'errors': []
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    # Track which page types we've successfully scraped
    scraped_types = set()
    
    for page in pages_config:
        # Skip if we already got this page type
        if page['name'] in scraped_types:
            continue
            
        url = base_url.rstrip('/') + page['path']
        page_name = page['name']
        
        try:
            logging.info(f"  Fetching {page_name}: {url}")
            response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            
            if response.status_code == 200:
                # Save raw HTML
                html_file = company_dir / f"{page_name}_raw.html"
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                # Extract clean text
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                clean_text = soup.get_text(separator='\n', strip=True)
                
                # Save clean text
                text_file = company_dir / f"{page_name}_clean.txt"
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(clean_text)
                
                results['pages_scraped'].append({
                    'page': page_name,
                    'url': url,
                    'status': response.status_code,
                    'size_bytes': len(response.text),
                    'html_file': str(html_file.relative_to(RAW_DIR)),
                    'text_file': str(text_file.relative_to(RAW_DIR))
                })
                
                scraped_types.add(page_name)
                
                logging.info(f"  ✓ Saved {page_name} ({len(response.text)} bytes)")
            else:
                logging.warning(f"  ✗ {page_name} returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            logging.error(f"  ✗ Timeout fetching {page_name}")
            results['errors'].append({
                'page': page_name,
                'url': url,
                'error': 'Timeout'
            })
        except requests.exceptions.RequestException as e:
            logging.error(f"  ✗ Error scraping {page_name}: {str(e)}")
            results['errors'].append({
                'page': page_name,
                'url': url,
                'error': str(e)
            })
        except Exception as e:
            logging.error(f"  ✗ Unexpected error scraping {page_name}: {str(e)}")
            results['errors'].append({
                'page': page_name,
                'url': url,
                'error': str(e)
            })
        
        # Be respectful - rate limit
        time.sleep(2)
    
    # Save metadata
    metadata_file = company_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"Completed scraping {company_name}: {len(results['pages_scraped'])} pages, {len(results['errors'])} errors")
    
    return results


def store_raw_to_cloud(**context):
    """
    Store raw data to S3 cloud storage
    """
    from dotenv import load_dotenv
    import sys
    
    # Add project root to path for imports
    sys.path.insert(0, str(BASE_DIR))
    from src.s3_utils import S3Storage
    
    load_dotenv(BASE_DIR / '.env')
    
    task_instance = context['task_instance']
    
    logging.info("Uploading scraped data to S3...")
    
    s3 = S3Storage()
    
    scraped_count = 0
    error_count = 0
    total_pages = 0
    uploaded_files = 0
    
    for company_dir in RAW_DIR.iterdir():
        if company_dir.is_dir():
            initial_dir = company_dir / "initial"
            if initial_dir.exists():
                # Upload entire company directory to S3
                company_id = company_dir.name
                s3_prefix = f"ai50/raw/{company_id}/initial"
                
                uploaded = s3.upload_directory(initial_dir, s3_prefix)
                uploaded_files += uploaded
                
                # Read metadata for summary
                metadata_file = initial_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    scraped_count += 1
                    total_pages += len(metadata.get('pages_scraped', []))
                    
                    if metadata.get('errors'):
                        error_count += 1
    
    summary = {
        'companies_scraped': scraped_count,
        'companies_with_errors': error_count,
        'total_pages_scraped': total_pages,
        'files_uploaded_to_s3': uploaded_files,
        's3_bucket': s3.bucket_name,
        'completed_at': datetime.utcnow().isoformat() + 'Z'
    }
    
    logging.info(
        f"S3 Upload complete: {scraped_count} companies, "
        f"{total_pages} pages, {uploaded_files} files uploaded to s3://{s3.bucket_name}"
    )
    
    # Save summary locally and to S3
    summary_file = DATA_DIR / "full_load_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    s3.upload_file(summary_file, 'ai50/summaries/full_load_summary.json')
    
    return summary


# Define the DAG
with DAG(
    dag_id='ai50_full_ingest_dag',
    default_args=default_args,
    description='Full load ingestion for all Forbes AI 50 companies',
    schedule_interval='@once',  # Run once manually
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ai50', 'full-load', 'ingestion'],
) as dag:
    
    # Task 1: Load company list
    load_companies = PythonOperator(
        task_id='load_company_list',
        python_callable=load_company_list,
        provide_context=True,
    )
    
    # Task 2: Scrape companies (using TaskGroup for better organization)
    with TaskGroup(group_id='scrape_companies') as scrape_group:
        
        def create_scrape_task(company_index):
            """Factory function to create scrape tasks dynamically"""
            
            def scrape_wrapper(**context):
                # Pull companies from XCom
                companies = context['task_instance'].xcom_pull(
                    task_ids='load_company_list',
                    key='companies'
                )
                
                if company_index >= len(companies):
                    logging.warning(f"Company index {company_index} out of range")
                    return None
                
                company_data = companies[company_index]
                return scrape_company_pages(company_data, **context)
            
            return PythonOperator(
                task_id=f'scrape_company_{company_index:02d}',
                python_callable=scrape_wrapper,
                provide_context=True,
            )
        
        # Create tasks for each company (50 companies)
        scrape_tasks = [create_scrape_task(i) for i in range(50)]
    
    # Task 3: Store to cloud/validate
    store_data = PythonOperator(
        task_id='store_raw_to_cloud',
        python_callable=store_raw_to_cloud,
        provide_context=True,
    )
    
    # Define task dependencies
    load_companies >> scrape_group >> store_data
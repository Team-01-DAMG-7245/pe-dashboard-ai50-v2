"""
Lab 3 - Daily Refresh Airflow DAG for Forbes AI 50
Re-scrapes key pages daily and tracks changes
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
import hashlib

# Configure paths - works with your existing project structure
BASE_DIR = Path(__file__).parent.parent  # Project root
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
SEED_FILE = DATA_DIR / "forbes_ai50_seed.json"
PAYLOADS_DIR = DATA_DIR / "payloads"

# Default arguments for the DAG
default_args = {
    'owner': 'quanta-capital',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}


def load_company_list_for_refresh(**context):
    """Load the Forbes AI 50 seed list for daily refresh"""
    logging.info(f"Loading company list from {SEED_FILE}")
    
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found at {SEED_FILE}")
    
    with open(SEED_FILE, 'r') as f:
        companies = json.load(f)
    
    # Filter to only companies that need refresh
    # You can add logic here to check which companies have been updated recently
    companies_to_refresh = companies  # For now, refresh all
    
    logging.info(f"Loaded {len(companies_to_refresh)} companies for refresh")
    
    context['task_instance'].xcom_push(key='companies', value=companies_to_refresh)
    return len(companies_to_refresh)


def generate_company_id(company_name):
    """Generate a clean company_id from company name"""
    return company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')


def get_content_hash(text):
    """Generate hash of content to detect changes"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def refresh_company_pages(company_data, **context):
    """
    Refresh key pages for a single company (About, Careers, Blog)
    Creates subfolder for each run
    
    Args:
        company_data: Dict with company info
    """
    company_name = company_data.get('company_name', 'Unknown')
    base_url = company_data.get('website', '')
    company_id = generate_company_id(company_name)
    
    # Get execution date for folder naming
    execution_date = context['ds']  # Format: YYYY-MM-DD
    
    logging.info(f"Refreshing company: {company_name} ({company_id}) - {execution_date}")
    
    # Create dated subfolder for this run
    company_dir = RAW_DIR / company_id / execution_date
    company_dir.mkdir(parents=True, exist_ok=True)
    
    # Focus on pages that change frequently
    pages_config = [
        {'path': '/about', 'name': 'about'},
        {'path': '/about-us', 'name': 'about'},
        {'path': '/company', 'name': 'about'},
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
        'crawled_at': datetime.utcnow().isoformat() + 'Z',
        'execution_date': execution_date,
        'pages_refreshed': [],
        'changes_detected': [],
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
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            
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
                
                # Calculate content hash
                content_hash = get_content_hash(clean_text)
                
                # Check for changes by comparing with previous run
                changed = check_for_changes(company_id, page_name, content_hash)
                
                page_result = {
                    'page': page_name,
                    'url': url,
                    'status': response.status_code,
                    'size_bytes': len(response.text),
                    'content_hash': content_hash,
                    'changed': changed,
                    'html_file': str(html_file.relative_to(RAW_DIR)),
                    'text_file': str(text_file.relative_to(RAW_DIR))
                }
                
                results['pages_refreshed'].append(page_result)
                scraped_types.add(page_name)
                
                if changed:
                    results['changes_detected'].append(page_name)
                    logging.info(f"  ✓ {page_name} - CHANGED")
                else:
                    logging.info(f"  ✓ {page_name} - No change")
                    
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
            logging.error(f"  ✗ Error refreshing {page_name}: {str(e)}")
            results['errors'].append({
                'page': page_name,
                'url': url,
                'error': str(e)
            })
        except Exception as e:
            logging.error(f"  ✗ Unexpected error refreshing {page_name}: {str(e)}")
            results['errors'].append({
                'page': page_name,
                'url': url,
                'error': str(e)
            })
        
        # Be respectful - rate limit
        time.sleep(2)
    
    # Save metadata for this run
    metadata_file = company_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    # Update change tracking
    update_change_tracker(company_id, results)
    
    logging.info(
        f"Completed refresh for {company_name}: "
        f"{len(results['pages_refreshed'])} pages, "
        f"{len(results['changes_detected'])} changes, "
        f"{len(results['errors'])} errors"
    )
    
    return results


def check_for_changes(company_id, page_name, current_hash):
    """
    Check if content has changed since last run
    
    Returns:
        bool: True if content changed, False otherwise
    """
    tracker_file = RAW_DIR / company_id / "change_tracker.json"
    
    if not tracker_file.exists():
        # First run, consider it changed
        return True
    
    try:
        with open(tracker_file, 'r') as f:
            tracker = json.load(f)
        
        last_hash = tracker.get('hashes', {}).get(page_name)
        
        if last_hash is None:
            return True  # New page
        
        return current_hash != last_hash
        
    except Exception as e:
        logging.warning(f"Error checking changes: {e}")
        return True  # Assume changed on error


def update_change_tracker(company_id, results):
    """Update the change tracker with latest hashes"""
    tracker_file = RAW_DIR / company_id / "change_tracker.json"
    
    # Load existing tracker or create new
    if tracker_file.exists():
        with open(tracker_file, 'r') as f:
            tracker = json.load(f)
    else:
        tracker = {
            'company_id': company_id,
            'company_name': results['company_name'],
            'hashes': {},
            'history': []
        }
    
    # Update hashes
    for page in results['pages_refreshed']:
        tracker['hashes'][page['page']] = page['content_hash']
    
    # Add to history
    tracker['history'].append({
        'execution_date': results['execution_date'],
        'crawled_at': results['crawled_at'],
        'pages_checked': len(results['pages_refreshed']),
        'changes_detected': results['changes_detected'],
        'errors': len(results['errors'])
    })
    
    # Keep only last 30 days of history
    if len(tracker['history']) > 30:
        tracker['history'] = tracker['history'][-30:]
    
    # Save tracker
    with open(tracker_file, 'w', encoding='utf-8') as f:
        json.dump(tracker, f, indent=2)


def log_refresh_summary(**context):
    """
    Log summary of daily refresh
    Tracks success/failure per company
    """
    task_instance = context['task_instance']
    execution_date = context['ds']
    
    logging.info(f"=== Daily Refresh Summary for {execution_date} ===")
    
    summary = {
        'execution_date': execution_date,
        'completed_at': datetime.utcnow().isoformat() + 'Z',
        'companies_processed': 0,
        'total_pages_refreshed': 0,
        'total_changes_detected': 0,
        'companies_with_errors': 0,
        'company_details': []
    }
    
    # Aggregate results from all company tasks
    for company_dir in RAW_DIR.iterdir():
        if not company_dir.is_dir():
            continue
            
        dated_dir = company_dir / execution_date
        if not dated_dir.exists():
            continue
            
        metadata_file = dated_dir / "metadata.json"
        if not metadata_file.exists():
            continue
            
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        summary['companies_processed'] += 1
        summary['total_pages_refreshed'] += len(metadata.get('pages_refreshed', []))
        summary['total_changes_detected'] += len(metadata.get('changes_detected', []))
        
        if metadata.get('errors'):
            summary['companies_with_errors'] += 1
        
        summary['company_details'].append({
            'company_id': metadata['company_id'],
            'company_name': metadata['company_name'],
            'pages_refreshed': len(metadata.get('pages_refreshed', [])),
            'changes_detected': metadata.get('changes_detected', []),
            'errors': len(metadata.get('errors', []))
        })
    
    # Save summary
    summary_dir = DATA_DIR / "refresh_logs"
    summary_dir.mkdir(exist_ok=True)
    
    summary_file = summary_dir / f"summary_{execution_date}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(
        f"Processed {summary['companies_processed']} companies, "
        f"{summary['total_pages_refreshed']} pages, "
        f"{summary['total_changes_detected']} changes detected, "
        f"{summary['companies_with_errors']} companies with errors"
    )
    
    return summary


def update_payloads_for_app(**context):
    """
    Update payload directory and upload to S3 so the app can see latest data
    This creates a link between the DAG and the app
    """
    from dotenv import load_dotenv
    import sys
    
    # Add project root to path for imports
    sys.path.insert(0, str(BASE_DIR))
    from src.s3_utils import S3Storage
    
    load_dotenv(BASE_DIR / '.env')
    
    execution_date = context['ds']
    
    logging.info("Updating payloads directory and uploading to S3...")
    
    s3 = S3Storage()
    
    # Ensure payloads directory exists
    PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Upload all today's scraped data to S3
    uploaded_files = 0
    for company_dir in RAW_DIR.iterdir():
        if not company_dir.is_dir():
            continue
        
        dated_dir = company_dir / execution_date
        if dated_dir.exists():
            company_id = company_dir.name
            s3_prefix = f"ai50/raw/{company_id}/{execution_date}"
            
            uploaded = s3.upload_directory(dated_dir, s3_prefix)
            uploaded_files += uploaded
    
    # Create a manifest of available companies
    manifest = {
        'last_updated': datetime.utcnow().isoformat() + 'Z',
        'execution_date': execution_date,
        'companies': []
    }
    
    for company_dir in RAW_DIR.iterdir():
        if not company_dir.is_dir():
            continue
        
        company_id = company_dir.name
        
        # Check if we have data for this execution date
        dated_dir = company_dir / execution_date
        if dated_dir.exists():
            metadata_file = dated_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                manifest['companies'].append({
                    'company_id': company_id,
                    'company_name': metadata.get('company_name'),
                    'last_updated': metadata.get('crawled_at'),
                    'pages_available': len(metadata.get('pages_refreshed', []))
                })
    
    # Save manifest locally
    manifest_file = PAYLOADS_DIR / "manifest.json"
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    
    # Upload manifest to S3
    s3.upload_file(manifest_file, 'ai50/payloads/manifest.json')
    
    logging.info(
        f"Updated manifest with {len(manifest['companies'])} companies. "
        f"Uploaded {uploaded_files} files to S3."
    )
    
    return manifest


# Define the DAG
with DAG(
    dag_id='ai50_daily_refresh_dag',
    default_args=default_args,
    description='Daily refresh of Forbes AI 50 company data',
    schedule_interval='0 3 * * *',  # Run at 3 AM daily
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['ai50', 'daily-refresh', 'ingestion'],
) as dag:
    
    # Task 1: Load company list
    load_companies = PythonOperator(
        task_id='load_company_list_for_refresh',
        python_callable=load_company_list_for_refresh,
        provide_context=True,
    )
    
    # Task 2: Refresh companies (using TaskGroup)
    with TaskGroup(group_id='refresh_companies') as refresh_group:
        
        def create_refresh_task(company_index):
            """Factory function to create refresh tasks dynamically"""
            
            def refresh_wrapper(**context):
                companies = context['task_instance'].xcom_pull(
                    task_ids='load_company_list_for_refresh',
                    key='companies'
                )
                
                if company_index >= len(companies):
                    logging.warning(f"Company index {company_index} out of range")
                    return None
                
                company_data = companies[company_index]
                return refresh_company_pages(company_data, **context)
            
            return PythonOperator(
                task_id=f'refresh_company_{company_index:02d}',
                python_callable=refresh_wrapper,
                provide_context=True,
            )
        
        # Create tasks for each company (50 companies)
        refresh_tasks = [create_refresh_task(i) for i in range(50)]
    
    # Task 3: Log summary
    log_summary = PythonOperator(
        task_id='log_refresh_summary',
        python_callable=log_refresh_summary,
        provide_context=True,
    )
    
    # Task 4: Update payloads for app integration (Lab 11 requirement)
    update_app_payloads = PythonOperator(
        task_id='update_payloads_for_app',
        python_callable=update_payloads_for_app,
        provide_context=True,
    )
    
    # Define task dependencies
    load_companies >> refresh_group >> log_summary >> update_app_payloads
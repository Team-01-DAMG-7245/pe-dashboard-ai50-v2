"""
Phase 4 - Assignment 5: Daily Update DAG for Project ORBIT
Incremental updates of snapshots and vector DB for Forbes AI 50 companies
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import json
import os
import sys
import logging
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configure paths
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
STRUCTURED_DIR = DATA_DIR / "structured"
PAYLOADS_DIR = DATA_DIR / "payloads"
SEED_FILE = DATA_DIR / "forbes_ai50_seed.json"

# Default arguments
default_args = {
    'owner': 'quanta-capital',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
    'execution_timeout': timedelta(hours=2),  # 2 hours per task
}


def load_company_list_for_update(**context):
    """Load the Forbes AI 50 seed list for daily update"""
    logging.info(f"Loading company list from {SEED_FILE}")
    
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found at {SEED_FILE}")
    
    with open(SEED_FILE, 'r') as f:
        companies = json.load(f)
    
    logging.info(f"Loaded {len(companies)} companies for daily update")
    context['task_instance'].xcom_push(key='companies', value=companies)
    return len(companies)


def update_company_snapshot(company_data, **context):
    """
    Update snapshot data for a company from latest scraped data
    This creates/updates the structured snapshot
    """
    company_name = company_data.get('company_name', 'Unknown')
    company_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
    execution_date = context['ds']
    
    logging.info(f"Updating snapshot for: {company_name} ({company_id}) - {execution_date}")
    
    try:
        from src.lab5.structured_extraction import process_company  # Old lab - keep as is
    except ImportError as e:
        logging.error(f"Failed to import structured extraction: {str(e)}")
        return {
            'company_id': company_id,
            'status': 'error',
            'error': f'Import error: {str(e)}. Note: instructor requires Python >=3.10, but Airflow uses Python 3.8.'
        }
    
    try:
        # Process company to update structured data
        result = process_company(company_id)
        
        # Update payload if structured data exists
        structured_path = STRUCTURED_DIR / f"{company_id}.json"
        payload_path = PAYLOADS_DIR / f"{company_id}.json"
        
        if structured_path.exists():
            try:
                from src.lab5.models import Payload  # Old lab - keep as is
            except ImportError as e:
                logging.error(f"Failed to import Payload model: {str(e)}")
                return {
                    'company_id': company_id,
                    'status': 'error',
                    'error': f'Import error: {str(e)}'
                }
            
            with open(structured_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            payload = Payload.model_validate(data)
            
            PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)
            with open(payload_path, 'w', encoding='utf-8') as f:
                json.dump(payload.model_dump(mode='json'), f, indent=2, default=str)
            
            logging.info(f"✓ Snapshot updated for {company_id}")
            return {
                'company_id': company_id,
                'status': 'success',
                'updated_at': execution_date
            }
        else:
            logging.warning(f"No structured data to update for {company_id}")
            return {
                'company_id': company_id,
                'status': 'skipped',
                'reason': 'no_structured_data'
            }
            
    except Exception as e:
        logging.error(f"✗ Error updating snapshot for {company_id}: {str(e)}")
        return {
            'company_id': company_id,
            'status': 'error',
            'error': str(e)
        }


def update_vector_db(**context):
    """
    Update vector database with latest scraped data
    Re-indexes companies that have new data
    """
    execution_date = context['ds']
    logging.info(f"Updating vector database for {execution_date}...")
    
    try:
        from src.lab4.index_for_rag_all import main as index_all  # Old lab - keep as is
    except ImportError as e:
        logging.error(f"Failed to import vector DB indexing: {str(e)}")
        return {
            'status': 'error',
            'error': f'Import error: {str(e)}. Vector DB dependencies may not be installed.'
        }
    
    try:
        # Re-index all companies (incremental updates would check dates)
        index_all()
        logging.info("✓ Vector DB update complete")
        return {
            'status': 'success',
            'updated_at': execution_date
        }
    except Exception as e:
        logging.error(f"✗ Error updating vector DB: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


def generate_update_summary(**context):
    """Generate summary of daily update"""
    execution_date = context['ds']
    
    summary = {
        'execution_date': execution_date,
        'completed_at': datetime.utcnow().isoformat() + 'Z',
        'companies_updated': 0,
        'vector_db_updated': False
    }
    
    # Count updated payloads (simplified - would check timestamps in real scenario)
    if PAYLOADS_DIR.exists():
        payload_files = list(PAYLOADS_DIR.glob("*.json"))
        summary['companies_updated'] = len([f for f in payload_files if f.stem != 'manifest'])
    
    # Save summary
    summary_dir = DATA_DIR / "refresh_logs"
    summary_dir.mkdir(exist_ok=True)
    summary_file = summary_dir / f"update_summary_{execution_date}.json"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(f"Daily update summary: {summary}")
    return summary


# Define the DAG
with DAG(
    dag_id='orbit_daily_update_dag',
    default_args=default_args,
    description='Daily update of snapshots and vector DB for Forbes AI 50 companies',
    schedule_interval='0 3 * * *',  # Run at 3 AM daily
    start_date=datetime(2025, 1, 1),
    catchup=False,
    dagrun_timeout=timedelta(hours=4),  # 4 hours for entire DAG run
    max_active_runs=1,  # Only one DAG run at a time
    tags=['orbit', 'daily-update', 'snapshots', 'vector-db'],
) as dag:
    
    # Task 1: Load company list
    load_companies = PythonOperator(
        task_id='load_company_list_for_update',
        python_callable=load_company_list_for_update,
        provide_context=True,
    )
    
    # Task 2: Update snapshots (using TaskGroup)
    with TaskGroup(group_id='update_snapshots') as update_group:
        
        def create_update_task(company_index):
            """Factory function to create update tasks dynamically"""
            
            def update_wrapper(**context):
                companies = context['task_instance'].xcom_pull(
                    task_ids='load_company_list_for_update',
                    key='companies'
                )
                
                if company_index >= len(companies):
                    logging.warning(f"Company index {company_index} out of range")
                    return None
                
                company_data = companies[company_index]
                return update_company_snapshot(company_data, **context)
            
            return PythonOperator(
                task_id=f'update_company_{company_index:02d}',
                python_callable=update_wrapper,
                provide_context=True,
            )
        
        # Create tasks for each company (50 companies)
        update_tasks = [create_update_task(i) for i in range(50)]
    
    # Task 3: Update vector DB
    update_vector = PythonOperator(
        task_id='update_vector_db',
        python_callable=update_vector_db,
        provide_context=True,
    )
    
    # Task 4: Generate summary
    generate_summary_task = PythonOperator(
        task_id='generate_update_summary',
        python_callable=generate_update_summary,
        provide_context=True,
    )
    
    # Define task dependencies
    load_companies >> update_group >> update_vector >> generate_summary_task


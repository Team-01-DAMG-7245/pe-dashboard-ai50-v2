"""
Phase 4 - Assignment 5: Initial Load DAG for Project ORBIT
Initial data load and payload assembly for all Forbes AI 50 companies
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
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),  # 2 hours per task
}


def load_company_list(**context):
    """Load the Forbes AI 50 seed list"""
    logging.info(f"Loading company list from {SEED_FILE}")
    
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found at {SEED_FILE}")
    
    with open(SEED_FILE, 'r') as f:
        companies = json.load(f)
    
    logging.info(f"Loaded {len(companies)} companies")
    context['task_instance'].xcom_push(key='companies', value=companies)
    return len(companies)


def extract_structured_data(company_data, **context):
    """
    Extract structured data from raw scraped data for a company
    This calls the structured extraction pipeline
    """
    company_name = company_data.get('company_name', 'Unknown')
    company_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
    
    logging.info(f"Extracting structured data for: {company_name} ({company_id})")
    
    try:
        from src.lab5.structured_extraction import process_company  # Old lab - keep as is
    except ImportError as e:
        logging.error(f"Failed to import structured extraction: {str(e)}")
        return {
            'company_id': company_id,
            'status': 'error',
            'error': f'Import error: {str(e)}. Note: instructor requires Python >=3.10, but Airflow uses Python 3.8. Consider running extraction in agent service.'
        }
    
    try:
        result = process_company(company_id)
        logging.info(f"✓ Structured extraction complete for {company_id}")
        return {
            'company_id': company_id,
            'status': 'success',
            'events': len(result.get('events', [])),
            'products': len(result.get('products', [])),
            'leadership': len(result.get('leadership', []))
        }
    except ImportError as e:
        # Handle instructor import error specifically
        if 'instructor' in str(e).lower():
            logging.warning(f"Instructor not available for {company_id}: {str(e)}")
            return {
                'company_id': company_id,
                'status': 'error',
                'error': f'Instructor not available. Requires Python >=3.10. Consider running extraction in agent service (Python 3.11).'
            }
        raise
    except Exception as e:
        logging.error(f"✗ Error extracting structured data for {company_id}: {str(e)}")
        return {
            'company_id': company_id,
            'status': 'error',
            'error': str(e)
        }


def assemble_payload(company_data, **context):
    """
    Assemble payload from structured data
    Copies structured data to payloads directory
    """
    try:
        from src.lab5.models import Payload  # Old lab - keep as is
    except ImportError as e:
        logging.error(f"Failed to import Payload model: {str(e)}")
        return {
            'company_id': 'unknown',
            'status': 'error',
            'error': f'Import error: {str(e)}'
        }
    
    company_name = company_data.get('company_name', 'Unknown')
    company_id = company_name.lower().replace(' ', '_').replace('.', '').replace(',', '')
    
    logging.info(f"Assembling payload for: {company_name} ({company_id})")
    
    structured_path = STRUCTURED_DIR / f"{company_id}.json"
    payload_path = PAYLOADS_DIR / f"{company_id}.json"
    
    if not structured_path.exists():
        logging.warning(f"No structured data found for {company_id}")
        return {
            'company_id': company_id,
            'status': 'skipped',
            'reason': 'no_structured_data'
        }
    
    try:
        # Load structured data
        with open(structured_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate it's a valid Payload
        payload = Payload.model_validate(data)
        
        # Save to payloads directory
        PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)
        with open(payload_path, 'w', encoding='utf-8') as f:
            json.dump(payload.model_dump(mode='json'), f, indent=2, default=str)
        
        logging.info(f"✓ Payload assembled for {company_id}")
        return {
            'company_id': company_id,
            'status': 'success'
        }
    except Exception as e:
        logging.error(f"✗ Error assembling payload for {company_id}: {str(e)}")
        return {
            'company_id': company_id,
            'status': 'error',
            'error': str(e)
        }


def index_vector_db(**context):
    """
    Index all scraped data into vector database for RAG
    """
    logging.info("Indexing all companies into vector database...")
    
    try:
        from src.lab4.index_for_rag_all import main as index_all  # Old lab - keep as is
    except ImportError as e:
        logging.error(f"Failed to import vector DB indexing: {str(e)}")
        return {
            'status': 'error',
            'error': f'Import error: {str(e)}. Vector DB dependencies (chromadb, sentence-transformers) may not be installed in Airflow.'
        }
    
    try:
        # This will index all companies from raw data
        index_all()
        logging.info("✓ Vector DB indexing complete")
        return {'status': 'success'}
    except Exception as e:
        logging.error(f"✗ Error indexing vector DB: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def generate_summary(**context):
    """Generate summary of initial load"""
    task_instance = context['task_instance']
    
    summary = {
        'execution_date': context['ds'],
        'completed_at': datetime.utcnow().isoformat() + 'Z',
        'payloads_assembled': 0,
        'companies_processed': 0
    }
    
    # Count payloads
    if PAYLOADS_DIR.exists():
        payload_files = list(PAYLOADS_DIR.glob("*.json"))
        summary['payloads_assembled'] = len([f for f in payload_files if f.stem != 'manifest'])
    
    # Save summary
    summary_file = DATA_DIR / "initial_load_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(f"Initial load summary: {summary}")
    return summary


# Define the DAG
with DAG(
    dag_id='orbit_initial_load_dag',
    default_args=default_args,
    description='Initial load and payload assembly for all Forbes AI 50 companies',
    schedule_interval='@once',  # Run once manually
    start_date=datetime(2025, 1, 1),
    catchup=False,
    dagrun_timeout=timedelta(hours=6),  # 6 hours for entire DAG run
    max_active_runs=1,  # Only one DAG run at a time
    tags=['orbit', 'initial-load', 'payload-assembly'],
) as dag:
    
    # Task 1: Load company list
    load_companies = PythonOperator(
        task_id='load_company_list',
        python_callable=load_company_list,
        provide_context=True,
    )
    
    # Task 2: Extract structured data (using TaskGroup)
    with TaskGroup(group_id='extract_structured') as extract_group:
        
        def create_extract_task(company_index):
            """Factory function to create extract tasks dynamically"""
            
            def extract_wrapper(**context):
                companies = context['task_instance'].xcom_pull(
                    task_ids='load_company_list',
                    key='companies'
                )
                
                if company_index >= len(companies):
                    logging.warning(f"Company index {company_index} out of range")
                    return None
                
                company_data = companies[company_index]
                return extract_structured_data(company_data, **context)
            
            return PythonOperator(
                task_id=f'extract_company_{company_index:02d}',
                python_callable=extract_wrapper,
                provide_context=True,
            )
        
        # Create tasks for each company (50 companies)
        extract_tasks = [create_extract_task(i) for i in range(50)]
    
    # Task 3: Assemble payloads (using TaskGroup)
    with TaskGroup(group_id='assemble_payloads') as assemble_group:
        
        def create_assemble_task(company_index):
            """Factory function to create assemble tasks dynamically"""
            
            def assemble_wrapper(**context):
                companies = context['task_instance'].xcom_pull(
                    task_ids='load_company_list',
                    key='companies'
                )
                
                if company_index >= len(companies):
                    logging.warning(f"Company index {company_index} out of range")
                    return None
                
                company_data = companies[company_index]
                return assemble_payload(company_data, **context)
            
            return PythonOperator(
                task_id=f'assemble_company_{company_index:02d}',
                python_callable=assemble_wrapper,
                provide_context=True,
            )
        
        # Create tasks for each company
        assemble_tasks = [create_assemble_task(i) for i in range(50)]
    
    # Task 4: Index vector DB
    index_vector = PythonOperator(
        task_id='index_vector_db',
        python_callable=index_vector_db,
        provide_context=True,
    )
    
    # Task 5: Generate summary
    generate_summary_task = PythonOperator(
        task_id='generate_summary',
        python_callable=generate_summary,
        provide_context=True,
    )
    
    # Define task dependencies
    load_companies >> extract_group >> assemble_group >> index_vector >> generate_summary_task


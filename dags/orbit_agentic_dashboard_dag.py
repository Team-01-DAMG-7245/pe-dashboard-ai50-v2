"""
Phase 4 - Assignment 5: Agentic Dashboard DAG for Project ORBIT
Invokes MCP + Agentic workflow daily for all AI 50 companies
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta
import json
import os
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configure paths
DATA_DIR = BASE_DIR / "data"
PAYLOADS_DIR = DATA_DIR / "payloads"
SEED_FILE = DATA_DIR / "forbes_ai50_seed.json"
DASHBOARDS_DIR = DATA_DIR / "dashboards"
LOGS_DIR = BASE_DIR / "logs"

# Default arguments
default_args = {
    'owner': 'quanta-capital',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),  # 2 hours per task
}


def load_company_list_for_dashboards(**context):
    """Load the Forbes AI 50 seed list for dashboard generation"""
    logging.info(f"Loading company list from {SEED_FILE}")
    
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found at {SEED_FILE}")
    
    with open(SEED_FILE, 'r') as f:
        companies = json.load(f)
    
    # Get company IDs from payloads directory
    if PAYLOADS_DIR.exists():
        payload_files = list(PAYLOADS_DIR.glob("*.json"))
        available_companies = [f.stem for f in payload_files if f.stem != 'manifest']
        logging.info(f"Found {len(available_companies)} companies with payloads")
    else:
        available_companies = []
        logging.warning("No payloads directory found")
    
    context['task_instance'].xcom_push(key='companies', value=companies)
    context['task_instance'].xcom_push(key='available_companies', value=available_companies)
    return len(available_companies)


def generate_agentic_dashboard(company_id, **context):
    """
    Generate dashboard using MCP-enabled supervisor agent
    This invokes the agentic workflow via MCP server
    """
    import httpx
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv(BASE_DIR / '.env')
    
    # Get MCP server URL from environment or config
    mcp_base_url = os.getenv('MCP_SERVER_URL', 'http://mcp-server:9000')
    
    execution_date = context['ds']
    run_id = context['dag_run'].run_id
    
    logging.info(f"Generating agentic dashboard for: {company_id} (run: {run_id})")
    
    # Create output directory
    DASHBOARDS_DIR.mkdir(parents=True, exist_ok=True)
    company_dashboard_dir = DASHBOARDS_DIR / company_id
    company_dashboard_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        'company_id': company_id,
        'run_id': run_id,
        'execution_date': execution_date,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'dashboards': {},
        'status': 'pending'
    }
    
    try:
        # Use async supervisor agent
        async def run_agent_workflow():
            try:
                from src.lab13.agents.supervisor_agent_mcp import MCPEnabledSupervisor
            except ImportError as e:
                logging.error(f"Failed to import MCPEnabledSupervisor: {str(e)}")
                raise
            
            supervisor = MCPEnabledSupervisor()
            
            try:
                # Override MCP base URL if provided via env
                if mcp_base_url != 'http://localhost:9000':
                    supervisor.mcp_base_url = mcp_base_url
                
                # Run agentic analysis
                analysis_results = await supervisor.analyze_company(company_id)
                
                return analysis_results
            finally:
                await supervisor.close()
        
        # Run async workflow
        analysis_results = asyncio.run(run_agent_workflow())
        
        # Save dashboards
        if 'dashboards' in analysis_results:
            for dashboard_type, dashboard_data in analysis_results['dashboards'].items():
                if 'markdown' in dashboard_data:
                    dashboard_file = company_dashboard_dir / f"{dashboard_type}_{execution_date}.md"
                    with open(dashboard_file, 'w', encoding='utf-8') as f:
                        f.write(dashboard_data['markdown'])
                    
                    results['dashboards'][dashboard_type] = {
                        'file': str(dashboard_file.relative_to(DATA_DIR)),
                        'size': len(dashboard_data['markdown'])
                    }
                    logging.info(f"✓ Saved {dashboard_type} dashboard for {company_id}")
        
        # Save results metadata
        results_file = company_dashboard_dir / f"results_{execution_date}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        results['status'] = 'success'
        logging.info(f"✓ Agentic dashboard generation complete for {company_id}")
        
        return results
        
    except Exception as e:
        logging.error(f"✗ Error generating agentic dashboard for {company_id}: {str(e)}")
        results['status'] = 'error'
        results['error'] = str(e)
        
        # Save error results
        results_file = company_dashboard_dir / f"results_{execution_date}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        return results


def generate_dashboard_summary(**context):
    """Generate summary of dashboard generation run"""
    execution_date = context['ds']
    run_id = context['dag_run'].run_id
    
    summary = {
        'execution_date': execution_date,
        'run_id': run_id,
        'completed_at': datetime.utcnow().isoformat() + 'Z',
        'companies_processed': 0,
        'dashboards_generated': 0,
        'errors': 0,
        'company_details': []
    }
    
    # Aggregate results from all company tasks
    if DASHBOARDS_DIR.exists():
        for company_dir in DASHBOARDS_DIR.iterdir():
            if not company_dir.is_dir():
                continue
            
            company_id = company_dir.name
            results_file = company_dir / f"results_{execution_date}.json"
            
            if results_file.exists():
                with open(results_file, 'r', encoding='utf-8') as f:
                    company_results = json.load(f)
                
                summary['companies_processed'] += 1
                
                if company_results.get('status') == 'success':
                    summary['dashboards_generated'] += len(company_results.get('dashboards', {}))
                else:
                    summary['errors'] += 1
                
                summary['company_details'].append({
                    'company_id': company_id,
                    'status': company_results.get('status'),
                    'dashboards': list(company_results.get('dashboards', {}).keys())
                })
    
    # Save summary
    summary_file = DASHBOARDS_DIR / f"summary_{execution_date}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(
        f"Dashboard generation summary: "
        f"{summary['companies_processed']} companies, "
        f"{summary['dashboards_generated']} dashboards, "
        f"{summary['errors']} errors"
    )
    
    return summary


# Define the DAG
with DAG(
    dag_id='orbit_agentic_dashboard_dag',
    default_args=default_args,
    description='Agentic dashboard generation using MCP + Supervisor Agent for all AI 50 companies',
    schedule_interval='0 4 * * *',  # Run at 4 AM daily (after daily update)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    dagrun_timeout=timedelta(hours=4),  # 4 hours for entire DAG run
    max_active_runs=1,  # Only one DAG run at a time
    tags=['orbit', 'agentic', 'dashboard', 'mcp'],
) as dag:
    
    # Task 1: Load company list
    load_companies = PythonOperator(
        task_id='load_company_list_for_dashboards',
        python_callable=load_company_list_for_dashboards,
        provide_context=True,
    )
    
    # Task 2: Generate dashboards (using TaskGroup)
    with TaskGroup(group_id='generate_dashboards') as dashboard_group:
        
        def create_dashboard_task(company_index):
            """Factory function to create dashboard tasks dynamically"""
            
            def dashboard_wrapper(**context):
                available_companies = context['task_instance'].xcom_pull(
                    task_ids='load_company_list_for_dashboards',
                    key='available_companies'
                )
                
                if company_index >= len(available_companies):
                    logging.warning(f"Company index {company_index} out of range")
                    return None
                
                company_id = available_companies[company_index]
                return generate_agentic_dashboard(company_id, **context)
            
            return PythonOperator(
                task_id=f'generate_dashboard_{company_index:02d}',
                python_callable=dashboard_wrapper,
                provide_context=True,
            )
        
        # Create tasks for each available company
        # We'll create up to 50 tasks, but they'll only run if company exists
        dashboard_tasks = [create_dashboard_task(i) for i in range(50)]
    
    # Task 3: Generate summary
    generate_summary_task = PythonOperator(
        task_id='generate_dashboard_summary',
        python_callable=generate_dashboard_summary,
        provide_context=True,
    )
    
    # Define task dependencies
    load_companies >> dashboard_group >> generate_summary_task


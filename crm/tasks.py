import os
import sys
import decimal
from django.utils import timezone
from celery import shared_task
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# --- Setup Django environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
try:
    import django
    django.setup()
except Exception as e:
    print(f"ERROR: Django setup failed: {e}", file=sys.stderr)
    raise

# --- GraphQL Client ---
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql/"
_transport = RequestsHTTPTransport(url=GRAPHQL_ENDPOINT, verify=False, retries=3, timeout=10)
client = Client(transport=_transport, fetch_schema_from_transport=True)

# --- GraphQL Query ---
REPORT_QUERY = gql("""
    query CRMReport {
        allCustomers {
            totalCount
        }
        allOrders {
            edges {
                node {
                    totalAmount
                }
            }
            totalCount
        }
    }
""")

# --- Celery Task ---
@shared_task(bind=True)
def generate_crm_report(self):
    """
    Celery task to generate a weekly CRM report.
    Fetches data via GraphQL, logs the report, and tracks task state.
    """
    log_file_path = "/tmp/crm_report_log.txt"
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Fetch data via GraphQL
        response_data = client.execute(REPORT_QUERY)
        total_customers = response_data.get("allCustomers", {}).get("totalCount", 0)
        total_orders = response_data.get("allOrders", {}).get("totalCount", 0)

        # Calculate total revenue
        total_revenue = decimal.Decimal('0.00')
        for edge in response_data.get("allOrders", {}).get("edges", []):
            node = edge.get("node")
            if node and node.get("totalAmount") is not None:
                total_revenue += decimal.Decimal(str(node["totalAmount"]))

        # Format and log report
        report_message = (
            f"{timestamp} - Report: {total_customers} customers, "
            f"{total_orders} orders, {total_revenue:.2f} revenue."
        )
        with open(log_file_path, "a") as log_file:
            log_file.write(report_message + "\n")

        print(f"CELERY TASK: CRM Report Generated: {report_message}")
        self.update_state(state='PROGRESS', meta={'message': 'Report generated successfully'})

    except Exception as e:
        error_message = f"{timestamp} - ERROR in CRM Report Generation: {e}"
        with open(log_file_path, "a") as log_file:
            log_file.write(error_message + "\n")
        print(f"CELERY TASK ERROR: {error_message}", file=sys.stderr)
        raise

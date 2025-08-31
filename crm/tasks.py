import os
import requests
import decimal
from datetime import datetime
from django.utils import timezone

# --- Setup Django environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
try:
    import django
    django.setup()
except Exception as e:
    import sys
    print(f"ERROR: Django setup failed: {e}", file=sys.stderr)
    raise

# --- GraphQL endpoint ---
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql/"

# --- Celery Task ---
def generate_crm_report():
    """
    Generate a weekly CRM report by querying GraphQL,
    logging total customers, orders, and revenue.
    """
    log_file_path = "/tmp/crm_report_log.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # GraphQL query string
        query = """
        query {
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
        """

        # Send request to GraphQL API
        response = requests.post(
            GRAPHQL_ENDPOINT,
            json={'query': query}
        )

        if response.status_code != 200:
            raise Exception(f"GraphQL error: {response.text}")

        data = response.json().get("data", {})
        total_customers = data.get("allCustomers", {}).get("totalCount", 0)
        total_orders = data.get("allOrders", {}).get("totalCount", 0)

        # Calculate revenue
        total_revenue = decimal.Decimal('0.00')
        for edge in data.get("allOrders", {}).get("edges", []):
            node = edge.get("node")
            if node and node.get("totalAmount") is not None:
                total_revenue += decimal.Decimal(str(node["totalAmount"]))

        # Build log message
        report_message = (
            f"{timestamp} - Report: {total_customers} customers, "
            f"{total_orders} orders, {total_revenue:.2f} revenue."
        )

        # Write to log file
        with open(log_file_path, "a") as log_file:
            log_file.write(report_message + "\n")

        print(f"CRM Report Generated: {report_message}")

    except Exception as e:
        error_message = f"{timestamp} - ERROR in CRM Report Generation: {e}"
        with open(log_file_path, "a") as log_file:
            log_file.write(error_message + "\n")
        print(error_message)
        raise

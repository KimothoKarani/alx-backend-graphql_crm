import datetime
from django.utils import timezone
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import os
import sys

if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
    try:
        import django
        django.setup()
    except Exception as e:
        print(f"ERROR: Failed to setup Django in crm.cron: {e}", file=sys.stderr)

GRAPHQL_ENDPOINT = "http://localhost:8080/graphql/"

_transport = RequestsHTTPTransport(
    url=GRAPHQL_ENDPOINT,
    verify=False,
    retries=3,
    timeout=5,
)
client = Client(transport=_transport, fetch_schema_from_transport=True)

HELLO_QUERY = gql("""
    query {
        __typename
    }
"""
)

UPDATE_LOW_STOCK_MUTATION = gql("""
    mutation UpdateLowStock {
        updateLowStockProducts {
            updatedProducts {
                id
                name
                stock
            }
            message
            success
            errors {
                field
                message
                code
            }
        }
    }
""")

def log_crm_heartbeat():
    log_file_path = "/tmp/crm_heartbeat_log.txt"
    timestamp = timezone.now().strftime("%d/%m/%Y-%H:%M:%S")

    heartbeat_message = f"{timestamp} CRM is alive."
    graphql_status = "N/A"

    try:
        response_data = client.execute(HELLO_QUERY)
        if response_data and response_data.get("__typename")== "Query":
            graphql_status = "GraphQL Responsive"
        else:
            graphql_status = "GraphQL Not Responsive (Unexpected Response)"
    except Exception as e:
        graphql_status = f"GraphQL Error: {str(e)}"

    full_log_message = f"{heartbeat_message} (GraphQL: {graphql_status})\n"

    try:
        with open(log_file_path, "a") as log_file:
            log_file.write(full_log_message)
        print(f"CRM Heartbeat logged: {full_log_message.strip()}")

    except Exception as e:
        print(f"ERROR: Failed to write heartbeat log to {log_file_path}: {e}", file=sys.stderr)


def update_low_stock():
    """
    Executes a GraphQL mutation to restock low-stock products and logs the updates.
    This function will be executed by django-crontab.
    """
    log_file_path = "/tmp/low_stock_updates_log.txt"
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")

    try:
        # Execute the GraphQL mutation
        response = client.execute(UPDATE_LOW_STOCK_MUTATION)
        mutation_result = response.get("updateLowStockProducts", {})

        updated_products = mutation_result.get("updatedProducts", [])
        message = mutation_result.get("message", "No message from mutation.")
        success = mutation_result.get("success", False)
        errors = mutation_result.get("errors", [])

        with open(log_file_path, "a") as log_file:
            log_file.write(f"[{timestamp}] Starting low stock update job.\n")
            log_file.write(f"[{timestamp}] Mutation response: Success={success}, Message='{message}'.\n")

            if success:
                if updated_products:
                    for product in updated_products:
                        log_file.write(
                            f"[{timestamp}] Updated Product: ID={product['id']}, Name='{product['name']}', New Stock={product['stock']}.\n")
                else:
                    log_file.write(f"[{timestamp}] No products found with low stock or updated.\n")
            else:
                log_file.write(f"[{timestamp}] Low stock update failed.\n")
                for error in errors:
                    log_file.write(
                        f"[{timestamp}] ERROR: Field='{error.get('field', 'N/A')}', Message='{error.get('message', 'N/A')}', Code='{error.get('code', 'N/A')}'.\n")

            log_file.write(f"[{timestamp}] Low stock update job finished (count: {len(updated_products)} updated).\n")

        print(f"Low stock update processed! Success: {success}, Updated: {len(updated_products)} products.")

    except Exception as e:
        error_message = f"[{timestamp}] ERROR: An unexpected error occurred during low stock update cron job: {e}\n"
        with open(log_file_path, "a") as log_file:
            log_file.write(error_message)
        print(f"Error in low stock update cron job: {e}", file=sys.stderr)
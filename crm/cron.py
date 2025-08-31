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


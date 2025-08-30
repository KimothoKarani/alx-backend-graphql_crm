#!/usr/bin/env python3

import os
import sys
from datetime import timedelta
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Ensure project root is in PYTHONPATH
PROJECT_ROOT = "/mnt/c/Users/Admin/ALX/alx-backend-graphql_crm"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Django Setup ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
import django
django.setup()
from django.utils import timezone

# --- GraphQL Client Configuration ---
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql/"  # Adjust if different

_transport = RequestsHTTPTransport(
    url=GRAPHQL_ENDPOINT,
    verify=False,   # For localhost; set True with SSL
    retries=3,
    timeout=10
)
client = Client(transport=_transport, fetch_schema_from_transport=True)

# --- GraphQL Query ---
query_string = """
    query GetRecentOrders($orderDateGte: DateTime!) {
      allOrders(filter: { orderDateGte: $orderDateGte }) {
        edges {
          node {
            id
            orderDate
            customer {
              email
              name
            }
            products {
              name
            }
          }
        }
      }
    }
"""
QUERY = gql(query_string)

# --- Main Logic ---
def send_reminders():
    log_file_path = "/tmp/order_reminders_log.txt"
    timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")

    seven_days_ago = timezone.now() - timedelta(days=7)
    variables = {"orderDateGte": seven_days_ago.isoformat()}

    try:
        response_data = client.execute(QUERY, variable_values=variables)

        with open(log_file_path, "a") as log_file:
            log_file.write(f"[{timestamp}] Starting order reminder script.\n")
            log_file.write(f"[{timestamp}] Querying orders with order_date >= {seven_days_ago.isoformat()}\n")

            orders = response_data.get("allOrders", {}).get("edges", [])

            if orders:
                for edge in orders:
                    order = edge.get("node")
                    if order and order.get("customer") and order["customer"].get("email"):
                        customer_email = order["customer"]["email"]
                        customer_name = order["customer"].get("name", "N/A")
                        order_id = order["id"]
                        order_date_str = order["orderDate"]

                        log_message = (
                            f"[{timestamp}] Reminder for Order ID: {order_id}, "
                            f"Customer: {customer_name} ({customer_email}), "
                            f"Order Date: {order_date_str}.\n"
                        )
                        log_file.write(log_message)
                        # Here you could send an actual email instead of just logging.
                    else:
                        log_file.write(f"[{timestamp}] Warning: Skipping order with missing customer/email data: {order}\n")
            else:
                log_file.write(f"[{timestamp}] No pending orders found within the last 7 days.\n")

            log_file.write(f"[{timestamp}] Order reminders processed!\n")

        print("Order reminders processed!")  # stdout for cron

    except Exception as e:
        error_message = f"[{timestamp}] ERROR: Failed to send order reminders: {e}\n"
        with open(log_file_path, "a") as log_file:
            log_file.write(error_message)
        print(f"Error processing order reminders: {e}", file=sys.stderr)


if __name__ == "__main__":
    send_reminders()

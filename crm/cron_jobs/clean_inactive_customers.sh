#!/bin/bash

# --- Configuration ---
PROJECT_DIR="/mnt/c/Users/Admin/ALX/alx-backend-graphql_crm"
PYTHON_EXEC="$PROJECT_DIR/venv/bin/python"

cd "$PROJECT_DIR" || { echo "Failed to change directory to $PROJECT_DIR" >> /tmp/customer_cleanup_log.txt; exit 1; }

"$PYTHON_EXEC" manage.py shell <<EOF >> /tmp/customer_cleanup_log.txt 2>&1
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql_crm.settings')
django.setup()

from crm.models import Customer, Order

timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"[{timestamp}] Starting inactive customer cleanup...")

one_year_ago = timezone.now() - timedelta(days=365)
active_customer_ids = Order.objects.filter(order_date__gte=one_year_ago).values_list('customer_id', flat=True).distinct()
inactive_customers_queryset = Customer.objects.exclude(id__in=active_customer_ids)

num_deleted, _ = inactive_customers_queryset.delete()
print(f"[{timestamp}] Finished cleanup. Deleted {num_deleted} inactive customers.")
EOF

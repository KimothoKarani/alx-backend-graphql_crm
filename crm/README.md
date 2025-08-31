## CRM Application – Production Task Scheduling

This document describes how to run **background tasks** for the CRM application using **Celery** and **Celery Beat**, with Redis as the message broker.

* * *

## Why Celery Instead of Cron?

In early development, we used `django-crontab` for jobs like cleanup and reminders. For production, all recurring tasks should be managed with **Celery Beat**, because:

*   Centralized scheduling (no mixing cron + Celery).
    
*   Task retries, monitoring, and logging are supported out of the box.
    
*   Works across distributed servers.
    
*   Plays well with monitoring tools like **Flower**.
    

* * *

## Prerequisites

*   **Python 3.x** with `pip`
    
*   **Django project**: `alx-backend-graphql_crm`
    
*   **Virtual environment** (`venv`)
    
*   **Redis server** running
    

### Install Redis (on Ubuntu/WSL):

`sudo apt update`

`sudo apt install redis-server`

`sudo service redis-server start`

`redis-cli ping   # should return "PONG"`

* * *

## Setup

### 1\. Install Dependencies

Make sure you have the required packages:

`cd /mnt/c/Users/Admin/ALX/alx-backend-graphql_crm`

`source venv/bin/activate`

`pip install -r requirements.txt`

`requirements.txt` should include:

`celery`

`django-celery-beat`

`redis`

`gql[requests]`

* * *

### 2\. Migrations

Set up database tables for Celery Beat scheduling and CRM models:

`python manage.py makemigrations crm django_celery_beat`

`python manage.py migrate`

* * *

### 3\. Run the Django Server

Your GraphQL endpoint must be live so Celery tasks can query/mutate data:

`python manage.py runserver`

* * *

### 4\. Start Celery Worker

Run this in a new terminal (inside your venv):

`cd /mnt/c/Users/Admin/ALX/alx-backend-graphql_crm`

`source venv/bin/activate`

`celery -A crm worker -l info`

* * *

### 5\. Start Celery Beat

Run this in another terminal (inside your venv):

`cd /mnt/c/Users/Admin/ALX/alx-backend-graphql_crm`

`source venv/bin/activate`

`celery -A crm beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

This uses the **database scheduler**, meaning you can manage task schedules directly from Django Admin.

* * *

### 6\. (Optional) Monitor with Flower

Flower provides a live dashboard for Celery:

`pip install flower`

`celery -A crm flower --port=5555`

Then open:

`http://localhost:5555`

* * *

## Configured Scheduled Tasks

All periodic tasks are now managed by **Celery Beat**.

Your `crm/settings.py` (or `alx_backend_graphql_crm/settings.py`) should include:

`from celery.schedules import crontab`

`CELERY_BEAT_SCHEDULE = {     "customer-cleanup": {         "task": "crm.tasks.clean_inactive_customers",         "schedule": crontab(hour=2, minute=0, day_of_week="sun"),  # Sundays at 2 AM     },     "order-reminders": {         "task": "crm.tasks.send_order_reminders",         "schedule": crontab(hour="8,20", minute=0),  # Daily at 8 AM and 8 PM     },     "crm-heartbeat": {         "task": "crm.tasks.log_crm_heartbeat",         "schedule": crontab(minute="*/5"),  # Every 5 minutes     },     "crm-weekly-report": {         "task": "crm.tasks.generate_crm_report",         "schedule": crontab(day_of_week="mon", hour=6, minute=0),  # Mondays at 6 AM     }, }`

* * *

## 🔹 Logs

Each task writes to its own log in `/tmp/`:

*   `/tmp/customer_cleanup_log.txt` → inactive customer cleanup
    
*   `/tmp/order_reminders_log.txt` → daily reminders
    
*   `/tmp/crm_heartbeat_log.txt` → heartbeat pings
    
*   `/tmp/crm_report_log.txt` → weekly CRM reports
    

Check logs with:

`tail -f /tmp/crm_report_log.txt`

* * *

## Summary

*   Use **Celery Worker** to run tasks.
    
*   Use **Celery Beat** (not system cron) for scheduling.
    
*   All schedules are tracked in Django (`django-celery-beat`).
    
*   Logs are written to `/tmp/`.
    
*   (Optional) Use **Flower** to monitor in real time.
## CRM Application – Production Task Scheduling

This document outlines the steps to set up and manage background tasks for the CRM application using Celery, Celery Beat, and system cron jobs.
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

## Setup Steps

1.  **Install Python Dependencies:**
    Navigate to your project's root directory and activate your virtual environment.
    ```bash
    cd /mnt/c/Users/Admin/ALX/alx-backend-graphql_crm # Adjust path as needed
    source venv/bin/activate
    pip install -r requirements.txt
    ```
    *(Ensure `requirements.txt` contains `celery`, `django-celery-beat`, `redis`, `gql[requests]`, `django-crontab`.)*

2.  **Run Django Migrations:**
    Apply database migrations for `django-celery-beat` and your CRM app models.
    ```bash
    python manage.py makemigrations crm django_celery_beat
    python manage.py migrate
    ```

3.  **Start Django Development Server:**
    Your GraphQL endpoint (`http://localhost:8000/graphql/`) needs to be running for Celery tasks (and system cron jobs) that interact with it.
    ```bash
    python manage.py runserver
    ```
    *(Keep this running in a separate terminal.)*

4.  **Start Celery Worker:**
    This process listens for tasks and executes them. Run this in a **new terminal** (with virtual environment activated).
    ```bash
    celery -A crm worker -l info
    ```
    *(Ensure you are in the project root with your virtual environment activated before running.)*

5.  **Start Celery Beat Scheduler:**
    This process reads the schedule (`CELERY_BEAT_SCHEDULE` from `settings.py` or database for `django-celery-beat`) and periodically sends tasks to the Celery worker queue. Run this in a **third terminal** (with virtual environment activated).
    ```bash
    celery -A crm beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    ```
    *(Ensure you are in the project root with your virtual environment activated before running.)*

6.  **Verify System Cron Jobs (Optional, for `django-crontab` and `clean_inactive_customers.sh`):**
    These jobs run separately from Celery.
    ```bash
    # Remove old django-crontab entries
    python manage.py crontab remove
    # Add entries from crm/settings.py
    python manage.py crontab add
    # Verify they are in the system crontab
    crontab -l
    ```

## Verification

-   **Celery Worker/Beat Logs:** Observe the terminal windows where `celery worker` and `celery beat` are running. You should see messages indicating tasks being scheduled and executed.
-   **Log Files:** Check the following log files for output from your scheduled tasks:
    -   `/tmp/customer_cleanup_log.txt` (from Task 0)
    -   `/tmp/order_reminders_log.txt` (from Task 1)
    -   `/tmp/crm_heartbeat_log.txt` (from Task 2)
    -   `/tmp/crm_report_log.txt` (from Task 3 - Celery task)
-   **Check GraphQL Endpoints:** Use GraphiQL/GraphQL Playground (`http://localhost:8000/graphql-playground/`) to verify data changes (e.g., product stock after `update_low_stock` cron job runs).
## Summary

*   Use **Celery Worker** to run tasks.
    
*   Use **Celery Beat** (not system cron) for scheduling.
    
*   All schedules are tracked in Django (`django-celery-beat`).
    
*   Logs are written to `/tmp/`.
    
*   (Optional) Use **Flower** to monitor in real time.
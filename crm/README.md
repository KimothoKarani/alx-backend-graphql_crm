# CRM Application – Production Task Scheduling

This document outlines the steps to set up and manage background tasks for the CRM application using Celery, Celery Beat, and system cron jobs.

## Prerequisites

-   **Python 3.x** with `pip`
-   **Django project**: `alx-backend-graphql_crm`
-   **Virtual environment** (`venv`)
-   **Redis server** running

### Install Redis and Dependencies: 
-   **Install Redis (on Ubuntu/WSL):**
    ```bash
    sudo apt update
    sudo apt install redis-server
    sudo service redis-server start
    redis-cli ping   # should return "PONG"
    ```
-   **Install Python Dependencies:**
    Navigate to your project's root directory and activate your virtual environment.
    ```bash
    cd /mnt/c/Users/Admin/ALX/alx-backend-graphql_crm # Adjust path as needed
    source venv/bin/activate
    pip install -r requirements.txt
    ```
    *(Ensure `requirements.txt` contains `celery`, `django-celery-beat`, `redis`, `gql[requests]`, `django-crontab`.)*

## Setup Steps

1.  **Run migrations (`python manage.py migrate`):**
    Apply database migrations for `django-celery_beat` and your CRM app models.
    ```bash
    python manage.py makemigrations crm django_celery_beat
    python manage.py migrate
    ```

2.  **Start Celery worker (`celery -A crm worker -l info`):**
    This process listens for tasks and executes them. Run this in a new terminal (with virtual environment activated).
    ```bash
    celery -A crm worker -l info
    ```
    *(Ensure you are in the project root with your virtual environment activated before running.)*

3.  **Start Celery Beat (`celery -A crm beat -l info`):**
    This process reads the schedule (`CELERY_BEAT_SCHEDULE` from `settings.py`) and periodically sends tasks to the Celery worker queue. Run this in a third terminal (with virtual environment activated).
    ```bash
    celery -A crm beat -l info
    ```
    *(Ensure you are in the project root with your virtual environment activated before running.)*

4.  **Verify logs in `/tmp/crm_report_log.txt`:**
    Check the log file for output from your scheduled Celery tasks.
    ```bash
    cat /tmp/crm_report_log.txt
    ```

## Other Verification Steps (Optional for task, but good practice)
-   **Celery Worker/Beat Logs:** Observe the terminal windows where `celery worker` and `celery beat` are running. You should see messages indicating tasks being scheduled and executed.
-   **All Log Files:** Check the following log files for output from your scheduled tasks:
    -   `/tmp/customer_cleanup_log.txt` (from Task 0)
    -   `/tmp/order_reminders_log.txt` (from Task 1)
    -   `/tmp/crm_heartbeat_log.txt` (from Task 2)
    -   `/tmp/crm_report_log.txt` (from Celery task)
-   **Check GraphQL Endpoints:** Use GraphiQL/GraphQL Playground (`http://localhost:8000/graphql-playground/`) to verify data changes (e.g., product stock after `update_low_stock` cron job runs).

## Summary

*   Use **Celery Worker** to run tasks.
*   Use **Celery Beat** (not system cron) for scheduling.
*   All schedules are tracked in Django (`django-celery-beat`).
*   Logs are written to `/tmp/`.
*   (Optional) Use **Flower** to monitor in real time.
#!/bin/bash

# --- Configuration ---
PROJECT_ROOT="/mnt/c/Users/Admin/ALX/alx-backend-graphql_crm"

# Path to virtual environment
VENV_PATH="$PROJECT_ROOT/venv"

# Path to Python script
PYTHON_SCRIPT="$PROJECT_ROOT/crm/cron_jobs/send_order_reminders.py"

# Log file
LOG_FILE="/tmp/order_reminders_log.txt"

# --- Logging start ---
echo "$(date +"%Y-%m-%d %H:%M:%S %Z") INFO: Cron job started." >> "$LOG_FILE"

# --- Change to project directory ---
cd "$PROJECT_ROOT" || {
    echo "$(date +"%Y-%m-%d %H:%M:%S %Z") ERROR: Failed to change directory to $PROJECT_ROOT" >> "$LOG_FILE"
    exit 1
}

# --- Activate virtual environment ---
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo "$(date +"%Y-%m-%d %H:%M:%S %Z") INFO: Virtual environment activated." >> "$LOG_FILE"
else
    echo "$(date +"%Y-%m-%d %H:%M:%S %Z") ERROR: Virtual environment not found at $VENV_PATH" >> "$LOG_FILE"
    exit 1
fi

# --- Run Python script ---
set +e
"$VENV_PATH/bin/python" "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1
SCRIPT_EXIT_CODE=$?
set -e

# --- Deactivate virtual environment ---
deactivate
echo "$(date +"%Y-%m-%d %H:%M:%S %Z") INFO: Virtual environment deactivated." >> "$LOG_FILE"

# --- Handle exit code ---
if [ "$SCRIPT_EXIT_CODE" -ne 0 ]; then
    echo "$(date +"%Y-%m-%d %H:%M:%S %Z") WARNING: send_order_reminders.py exited with code $SCRIPT_EXIT_CODE." >> "$LOG_FILE"
else
    echo "$(date +"%Y-%m-%d %H:%M:%S %Z") INFO: send_order_reminders.py completed successfully." >> "$LOG_FILE"
fi

# --- Logging end ---
echo "$(date +"%Y-%m-%d %H:%M:%S %Z") INFO: Cron job finished." >> "$LOG_FILE"

import os
import sys
import requests
from datetime import date, timedelta

# =============================================================================
# CONFIGURATION — Edit this block when duplicating for a new task
# =============================================================================

TASK_NAME = "test"

ASSIGNEE = "kevin@piekarskitree.com"

PROJECT_GID = "1211903431208886"

SECTION_GID = "1211903431208887"

# Due date: "today", "tomorrow", or a fixed date string "YYYY-MM-DD"
DUE_DATE = "today"

# Description / notes (optional — set to None to skip)
DESCRIPTION = None
# DESCRIPTION = """
# Please complete the following:
# 1. Item one
# 2. Item two
# """

# Template task GID to duplicate instead of creating from scratch (optional)
# If set, all fields above still apply as overrides on the duplicated task
# Find via the task URL: app.asana.com/0/{project}/{task_gid}
TEMPLATE_TASK_GID = None  # e.g. "9876543210"

# Fields to carry over when duplicating a template task
# Options: assignee, attachments, dates, dependencies, followers, notes, subtasks, tags
TEMPLATE_COPY_FIELDS = ["assignee", "notes", "subtasks", "tags"]

# =============================================================================
# END CONFIGURATION
# =============================================================================


ASANA_TOKEN = os.environ["ASANA_TOKEN"]
BASE_URL = "https://app.asana.com/api/1.0"
HEADERS = {
    "Authorization": f"Bearer {ASANA_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def resolve_due_date(due: str) -> str:
    if due == "today":
        return date.today().isoformat()
    elif due == "tomorrow":
        return (date.today() + timedelta(days=1)).isoformat()
    else:
        return due  # assume already YYYY-MM-DD


def get_assignee_gid(assignee: str) -> str:
    """Resolve email to GID if needed; Asana also accepts emails directly."""
    return assignee  # Asana REST API accepts email strings as assignee


def duplicate_template(template_gid: str) -> str:
    """Duplicate a template task and return the new task GID."""
    print(f"Duplicating template task {template_gid}...")
    url = f"{BASE_URL}/tasks/{template_gid}/duplicate"
    payload = {
        "data": {
            "name": TASK_NAME,
            "include": TEMPLATE_COPY_FIELDS,
        }
    }
    resp = requests.post(url, json=payload, headers=HEADERS)
    resp.raise_for_status()
    job = resp.json()["data"]
    # Duplication is async — poll the job until complete
    job_gid = job["gid"]
    import time
    for _ in range(20):
        time.sleep(2)
        job_resp = requests.get(f"{BASE_URL}/jobs/{job_gid}", headers=HEADERS)
        job_resp.raise_for_status()
        job_data = job_resp.json()["data"]
        if job_data["status"] == "succeeded":
            new_task_gid = job_data["new_task"]["gid"]
            print(f"Template duplicated — new task GID: {new_task_gid}")
            return new_task_gid
        elif job_data["status"] == "failed":
            raise RuntimeError("Asana duplication job failed")
    raise TimeoutError("Timed out waiting for Asana duplication job")


def create_task_from_scratch() -> str:
    """Create a brand new task and return its GID."""
    print("Creating new task from scratch...", flush=True)
    payload = {
        "data": {
            "name": TASK_NAME,
            "assignee": ASSIGNEE,
            "projects": [PROJECT_GID],
            "due_on": resolve_due_date(DUE_DATE),
        }
    }
    if DESCRIPTION:
        payload["data"]["notes"] = DESCRIPTION.strip()

    resp = requests.post(f"{BASE_URL}/tasks", json=payload, headers=HEADERS)
    print(f"API response status: {resp.status_code}", flush=True)
    print(f"API response body: {resp.text}", flush=True)
    resp.raise_for_status()
    task_gid = resp.json()["data"]["gid"]
    print(f"Task created — GID: {task_gid}", flush=True)
    return task_gid


def update_task(task_gid: str):
    """Apply overrides to a task (used after duplication)."""
    payload = {
        "data": {
            "name": TASK_NAME,
            "assignee": ASSIGNEE,
            "due_on": resolve_due_date(DUE_DATE),
        }
    }
    if DESCRIPTION:
        payload["data"]["notes"] = DESCRIPTION.strip()

    resp = requests.put(f"{BASE_URL}/tasks/{task_gid}", json=payload, headers=HEADERS)
    resp.raise_for_status()
    print("Task updated with config overrides.")


def add_to_project(task_gid: str):
    """Ensure the task is in the correct project (needed after duplication)."""
    payload = {"data": {"project": PROJECT_GID}}
    resp = requests.post(
        f"{BASE_URL}/tasks/{task_gid}/addProject", json=payload, headers=HEADERS
    )
    resp.raise_for_status()
    print(f"Task added to project {PROJECT_GID}.")


def move_to_section(task_gid: str):
    """Move the task to the configured section."""
    if not SECTION_GID:
        return
    payload = {"data": {"task": task_gid}}
    resp = requests.post(
        f"{BASE_URL}/sections/{SECTION_GID}/addTask", json=payload, headers=HEADERS
    )
    resp.raise_for_status()
    print(f"Task moved to section {SECTION_GID}.")


def main():
    print(f"--- Asana Task Creator: '{TASK_NAME}' ---")

    if TEMPLATE_TASK_GID:
        task_gid = duplicate_template(TEMPLATE_TASK_GID)
        update_task(task_gid)
        add_to_project(task_gid)
    else:
        task_gid = create_task_from_scratch()

    move_to_section(task_gid)

    task_url = f"https://app.asana.com/0/{PROJECT_GID}/{task_gid}"
    print(f"Done! Task URL: {task_url}")


if __name__ == "__main__":
    main()

import requests
import datetime
import re
import json
import os
from icalendar import Calendar, Event

# ICS URLs
USER_ICS_URL = "https://hkr.instructure.com/feeds/calendars/user_xOrYwkKlKq1lm1iOXuRabKHLhfIVId0kLKCCs7C4.ics"
SCHEMA_ICS_URL = "https://schema.hkr.se/setup/jsp/SchemaICAL.ics?startDatum=2025-03-13&intervallTyp=a&intervallAntal=1&sokMedAND=false&sprak=SV&resurser=k.BMA451%202025%2004%20100%20DAG%20NML%20sv-%2C"

TODOIST_API_TOKEN = "46fc28554f4438c1645854cbdaa7ea72d3cb63de"
TASKS_FILE = "added_tasks.json"

def load_calendar(url):
    response = requests.get(url)
    return Calendar.from_ical(response.text)

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip().lower()

def extract_lecture_title(summary):
    summary_clean = clean_text(summary)
    idx = summary_clean.find("laboratoriemedicin")
    if idx != -1:
        sub = summary_clean[idx:]
        m = re.search(r'(sign:|moment:)', sub)
        if m:
            return sub[:m.start()].strip()
        else:
            return sub.strip()
    return summary.strip()

def find_schema_times(user_event, schema_events):
    dtstart_field = user_event.get('dtstart')
    if not dtstart_field:
        return None
    user_date = dtstart_field.dt if isinstance(dtstart_field.dt, datetime.date) else dtstart_field.dt.date()
    user_title = extract_lecture_title(user_event.get('summary', ''))
    
    for se in schema_events:
        schema_dtstart = se.get('dtstart').dt
        if not isinstance(schema_dtstart, datetime.datetime):
            continue
        schema_date = schema_dtstart.date()
        if schema_date == user_date:
            schema_title = extract_lecture_title(se.get('summary', ''))
            if (user_title in schema_title) or (schema_title in user_title):
                return se.get('dtstart').dt, se.get('dtend').dt
    return None

def adjust_zoom_title(title, event):
    loc = event.get('location', '')
    desc = event.get('description', '')
    if ("zoom" in loc.lower()) or ("zoom meeting" in desc.lower()):
        if not title.lower().startswith("zoom "):
            return "Zoom " + title
    return title

def load_added_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r") as file:
            return json.load(file)
    return {}

def save_added_tasks(tasks):
    with open(TASKS_FILE, "w") as file:
        json.dump(tasks, file, indent=2, default=str)

def create_todoist_task(api_token, task_name, due_datetime=None):
    tasks = load_added_tasks()
    task_key = f"{task_name}_{due_datetime.isoformat() if due_datetime else 'no_date'}"

    if task_key in tasks:
        print(f"⚠️ Task already added, skipping: {task_name}")
        return

    url = "https://api.todoist.com/rest/v2/tasks"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    data = {"content": task_name}

    if due_datetime:
        data["due_datetime"] = due_datetime.isoformat()

    response = requests.post(url, json=data, headers=headers)
    if response.status_code in [200, 201]:
        print(f"✅ Added Todoist task: {task_name}")
        tasks[task_key] = True
        save_added_tasks(tasks)
    else:
        print(f"❌ Failed to add task {task_name}: {response.text}")

def clean_calendar():
    user_cal = load_calendar(USER_ICS_URL)
    schema_cal = load_calendar(SCHEMA_ICS_URL)
    schema_events = [comp for comp in schema_cal.walk() if comp.name == "VEVENT"]

    new_cal = Calendar()
    new_cal.add('prodid', '-//Uppdaterad Kalender//EN')
    new_cal.add('version', '2.0')

    for comp in user_cal.walk():
        if comp.name != "VEVENT":
            continue

        summary = comp.get('summary')
        if not summary:
            continue

        if "BMA152" in summary or "[BMA052 HT24]" in summary or "[BMA201 VT25]" in summary:
            continue

        title = extract_lecture_title(summary)
        dtstart_field = comp.get('dtstart')
        if not dtstart_field:
            continue

        if isinstance(dtstart_field.dt, datetime.datetime):
            new_dtstart = dtstart_field.dt
            dtend_field = comp.get('dtend')
            new_dtend = dtend_field.dt if dtend_field else new_dtstart + datetime.timedelta(hours=1)
        else:
            times = find_schema_times(comp, schema_events)
            if times is None:
                date_obj = dtstart_field.dt
                new_dtstart = datetime.datetime.combine(date_obj, datetime.time(23, 0))
                new_dtend = datetime.datetime.combine(date_obj, datetime.time(23, 59))
            else:
                new_dtstart, new_dtend = times

        new_title = adjust_zoom_title(title, comp)

        new_event = Event()
        new_event.add('summary', new_title)
        new_event.add('dtstart', new_dtstart)
        new_event.add('dtend', new_dtend)
        if comp.get('location'):
            new_event.add('location', comp.get('location'))
        if comp.get('description'):
            new_event.add('description', comp.get('description'))
        new_cal.add_component(new_event)

        create_todoist_task(TODOIST_API_TOKEN, new_title, new_dtstart)

    return new_cal.to_ical()

if __name__ == "__main__":
    updated_ical = clean_calendar()
    print(updated_ical.decode('utf-8'))

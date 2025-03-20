import os
import requests
import re
from icalendar import Calendar, Event
from datetime import datetime

# Fetch the ICS URL from environment variable
ICS_URL = os.environ.get('ICS_URL')

def clean_event_summary(summary):
    # Remove unwanted information
    patterns = [
        r'Program:.*?(?=\s\w+:|\Z)',
        r'Kurs\.grp:.*?(?=\s\w+:|\Z)',
        r'Sign:.*?(?=\s\w+:|\Z)',
        r'Aktivitetstyp:.*?(?=\s\w+:|\Z)',
        r'Moment:.*?(?=\s\w+:|\Z)'
    ]
    for pattern in patterns:
        summary = re.sub(pattern, '', summary)
    return summary.strip()

def clean_calendar():
    response = requests.get(ICS_URL)
    original_cal = Calendar.from_ical(response.text)
    
    clean_cal = Calendar()
    clean_cal.add('prodid', '-//Cleaned HKR Calendar//EN')
    clean_cal.add('version', '2.0')
    
    for component in original_cal.walk():
        if component.name == "VEVENT":
            clean_event = Event()
            clean_event.add('summary', clean_event_summary(component.get('summary')))
            clean_event.add('dtstart', component.get('dtstart'))
            clean_event.add('dtend', component.get('dtend'))
            clean_event.add('location', component.get('location', ''))
            clean_event.add('description', component.get('description', ''))
            clean_cal.add_component(clean_event)
    
    return clean_cal.to_ical()

if __name__ == "__main__":
    cleaned_ical = clean_calendar()
    print(cleaned_ical.decode('utf-8'))

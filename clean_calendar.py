import os
import requests
import re
from icalendar import Calendar, Event

# Fetch the ICS URL from environment variables
ICS_URL = os.environ.get('ICS_URL')

def clean_event_summary(summary):
    """
    Extract course code, remove 'Aktivitetstyp', and clean the summary.
    """
    # Remove 'Aktivitetstyp' explicitly
    summary = re.sub(r'Aktivitetstyp', '', summary)

    # Extract course code (assuming it starts with BMA followed by digits)
    course_code_match = re.search(r'(BMA\d{3})', summary)
    course_code = course_code_match.group(1) if course_code_match else ''

    # Extract Moment from the summary
    moment_pattern = r'Moment:([^:]+)'
    moment_match = re.search(moment_pattern, summary)
    
    if moment_match:
        moment = moment_match.group(1).strip()
        return f"{course_code}: {moment}" if course_code else moment
    else:
        # If no Moment found, return the course code (if any) followed by the cleaned summary
        cleaned_summary = summary.strip()
        return f"{course_code}: {cleaned_summary}" if course_code else cleaned_summary

def clean_calendar():
    """
    Fetch and clean the calendar by extracting only relevant information.
    """
    # Fetch the original calendar data from the ICS URL
    response = requests.get(ICS_URL)
    original_cal = Calendar.from_ical(response.text)
    
    # Create a new calendar for cleaned events
    clean_cal = Calendar()
    clean_cal.add('prodid', '-//Cleaned HKR Calendar//EN')
    clean_cal.add('version', '2.0')
    
    for component in original_cal.walk():
        if component.name == "VEVENT":  # Process only events
            clean_event = Event()
            # Extract and clean relevant fields
            clean_event.add('summary', clean_event_summary(component.get('summary')))
            clean_event.add('dtstart', component.get('dtstart'))
            clean_event.add('dtend', component.get('dtend'))
            clean_event.add('location', component.get('location', ''))
            clean_event.add('description', component.get('description', ''))
            
            # Add cleaned event to the new calendar
            clean_cal.add_component(clean_event)
    
    return clean_cal.to_ical()

if __name__ == "__main__":
    # Clean calendar and print output (for debugging or local testing)
    cleaned_ical = clean_calendar()
    print(cleaned_ical.decode('utf-8'))

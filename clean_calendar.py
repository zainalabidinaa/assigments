import os
import requests
import re
from icalendar import Calendar, Event

# Fetch the ICS URL from environment variables
ICS_URL = os.environ.get('ICS_URL')

def clean_event_summary(summary):
    """
    Extract the first course code, remove 'Aktivitetstyp', and clean the summary.
    """
    print(f"Original summary: {summary}")  # Debug print

    # Remove 'Aktivitetstyp' explicitly
    summary = re.sub(r'Aktivitetstyp', '', summary)

    # Extract all course codes (BMA followed by digits)
    course_codes = re.findall(r'(BMA\d{3})', summary)
    
    # Remove all course codes from the summary
    for code in course_codes:
        summary = summary.replace(code, '')

    # Clean up any remaining commas and whitespace
    summary = re.sub(r'\s*,\s*', ' ', summary).strip()

    print(f"Extracted course codes: {course_codes}")  # Debug print
    print(f"Cleaned summary: {summary}")  # Debug print

    # Construct the final result
    if course_codes:
        result = f"{course_codes[0]}: {summary}"  # Use only the first course code
    else:
        result = summary  # If no course code, return just the cleaned summary

    print(f"Final result: {result}")  # Debug print
    return result

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
            
            print(f"Event summary: {clean_event.get('summary')}")  # Debug print
            
            # Add cleaned event to the new calendar
            clean_cal.add_component(clean_event)
    
    return clean_cal.to_ical()

if __name__ == "__main__":
    # Clean calendar and print output (for debugging or local testing)
    cleaned_ical = clean_calendar()
    print(cleaned_ical.decode('utf-8'))

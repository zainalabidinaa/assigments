import os
import requests
import re
from icalendar import Calendar, Event

# Fetch the ICS URL from environment variables
ICS_URL = os.environ.get('ICS_URL')

def clean_event_summary(summary):
    """
    Rensa händelsens sammanfattning genom att:
    1. Extrahera endast kurskoden (t.ex. BMA451) om den finns i början av strängen.
    2. Ta bort 'Aktivitetstyp' från sammanfattningen.
    3. Hantera fall där 'Moment:' inte finns.
    """
    # Remove 'Aktivitetstyp' explicitly
    summary = re.sub(r'Aktivitetstyp', '', summary)

    # Extract course code at the beginning of the string
    course_code_match = re.search(r'([A-Z]{3}\d{3,4})', summary)
    if course_code_match:
        extracted_course_code = course_code_match.group(1)
        # Extract Moment from the summary
        moment_pattern = r'Moment:([^:]+)'
        match = re.search(moment_pattern, summary)
        if match:
            return f"{extracted_course_code} {match.group(1).strip()}"  # Return Course code and Moment
        else:
            return extracted_course_code # Returns only the course code
    else:
        # Extract Moment from the summary
        moment_pattern = r'Moment:([^:]+)'
        match = re.search(moment_pattern, summary)
        if match:
            return match.group(1).strip()  # Return only the extracted text, trimmed of whitespace
        else:
            return summary.strip()  # Return cleaned summary without 'Aktivitetstyp'

def clean_calendar():
    """
    Hämta och rensa kalendern genom att endast extrahera relevant information.
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
            summary = clean_event_summary(component.get('summary'))
            clean_event.add('summary', summary)
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

import os
import requests
import re
from icalendar import Calendar, Event

# Fetch the ICS URL from environment variables
ICS_URL = os.environ.get('ICS_URL')

COURSE_CODE_MAPPING = {
    "Laboratoriemedicin vår T3, Biomedicinsk laboratorievetenskap II, Laboratoriemedicin och laboratorievetenskapliga metoder Laboratoriemedicin vår T4": "BMA451",
    "Proteinkemi och analysmetoder": "BMA052",
    "Laboratoriemedicin - höst T4, Laboratoriemedicin - höst T3": "BMA351"
}

def clean_event_summary(summary):
    """
    Clean the summary to extract relevant information.
    """
    print(f"Original summary: {summary}")  # Debug print

    # Remove everything before "Moment:"
    moment_match = re.search(r'Moment:(.*)', summary)
    if moment_match:
        summary = f"Moment:{moment_match.group(1)}"
    else:
        print("No 'Moment:' found in summary.")  # Debug print
        return summary  # If no Moment, return original

    # Remove everything after "Aktivitetstyp:"
    aktivitetstyp_match = re.search(r'(.*)Aktivitetstyp:', summary)
    if aktivitetstyp_match:
        summary = aktivitetstyp_match.group(1).strip()
    else:
        print("No 'Aktivitetstyp:' found in summary.")  # Debug print

    # Extract course code
    course_code = None
    course_code_match = re.search(r'\b([A-Z][A-Za-z0-9]{3})\b', summary)

    # Check specific cheat codes
    for key, code in COURSE_CODE_MAPPING.items():
        if key in summary:
            course_code = code
            break

    # Handle cases like "BMA401, BMA451, ..."
    if "Kurs.grp:" in summary and course_code is None:
        kurs_grp_match = re.search(r"Kurs\.grp: (.*)", summary)
        if kurs_grp_match:
            kurs_grp = kurs_grp_match.group(1).strip()
            for key, code in COURSE_CODE_MAPPING.items():
                if key in kurs_grp:
                    course_code = code
                    break
        summary = re.sub(r'^[A-Z0-9, ]*dp\s*\d+', '', summary)  # Remove text before 'dp' in Kurs.grp cases

    if course_code_match:
       course_code = course_code_match.group(1)

    # Construct final result
    if course_code:
        result = f"{course_code}: {summary}"
    else:
        result = summary

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

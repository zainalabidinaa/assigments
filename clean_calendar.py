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

    # 1. Extract Moment Content
    moment_match = re.search(r'Moment:(.*)', summary)
    if moment_match:
        summary = moment_match.group(1).strip() # Keep only moment content
    else:
        print("No 'Moment:' found in summary.")
        return summary

   # Remove everything after "Aktivitetstyp:"
    aktivitetstyp_match = re.search(r'(.*)Aktivitetstyp:', summary)
    if aktivitetstyp_match:
        summary = aktivitetstyp_match.group(1).strip()
    else:
        print("No 'Aktivitetstyp:' found in summary.")  # Debug print

    # 2. Extract course code from Kurs.grp if applicable, and clean from dp onwards
    if "Kurs.grp:" in summary:
        kurs_grp_match = re.search(r"Kurs\.grp: (.*)", summary)
        if kurs_grp_match:
            kurs_grp = kurs_grp_match.group(1).strip()
            for key, code in COURSE_CODE_MAPPING.items():
                if key in kurs_grp:
                    course_code = code
                    break
            else: course_code = None # If not found setting it to be None.
        summary = re.sub(r'^[A-Z0-9, ]*dp\s*\d+', '', summary).strip()
    else: course_code = None # Setting it to None for cases where it's missing
           

    # 3. Extract first potential course code (Four characters with at least one capital letter)
    if course_code is None: # Ensuring it only extracts if cheat code is missed
        course_code_match = re.search(r'\b([A-Z][A-Za-z0-9]{3})\b', summary)
        course_code = course_code_match.group(1) if course_code_match else None

    # 4. Apply Cheat Codes if no course code found
    if course_code is None:
        for key, code in COURSE_CODE_MAPPING.items():
            if key in summary:
                course_code = code
                break

    # 5. Construct final result
    if course_code:
        result = f"{course_code}: {summary}"
    else:
        result = summary # Otherwise, return just the summary without a code.

    print(f"Final result: {result}") # Debug print
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

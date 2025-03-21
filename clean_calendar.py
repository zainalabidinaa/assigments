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

    # Extract potential course code at the beginning (Four characters with at least one capital letter)
    course_code_match = re.search(r'([A-Z][A-Za-z0-9]{3})', summary)
    course_code = course_code_match.group(1) if course_code_match else None # To grab those initials first

   # 1. Extract Moment Content
    moment_match = re.search(r'Moment:(.*)', summary)
    if moment_match:
        moment_content = moment_match.group(1).strip()  # Capture it here.

    else:
        print("No 'Moment:' found in summary.")
        return summary

   # Remove everything after "Aktivitetstyp:"
    aktivitetstyp_match = re.search(r'(.*)Aktivitetstyp:', moment_content)
    if aktivitetstyp_match:
        moment_content = aktivitetstyp_match.group(1).strip()
    else:
        print("No 'Aktivitetstyp:' found in summary.")

    # 2. Apply Cheat Codes if no course code found, before even extraction
    if course_code is None:
        for key, code in COURSE_CODE_MAPPING.items():
            if key in summary: # using the whole to be safe
                course_code = code
                break # once we found it, break.
               

    # 3. If Kurs.grp is included do this process, otherwise keep the original course code
    if "Kurs.grp:" in summary:
        kurs_grp_match = re.search(r"Kurs\.grp: (.*)", summary)
        if kurs_grp_match:
            kurs_grp = kurs_grp_match.group(1).strip() # Grabbing what's in the KURS GRP
            summary = re.sub(r'^[A-Z0-9, ]*dp\s*\d+', '', summary).strip()  # Remove text before 'dp' in Kurs.grp cases

   # 4. Before Returning Construct final result, place it before
    if course_code:
        result = f"{course_code}: {moment_content}"  # Use the correct format. BMA : Moment
    else:
        result = moment_content

    print(f"Final result: {result}")
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

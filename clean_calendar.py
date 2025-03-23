import os
import requests
import re
from icalendar import Calendar, Event

# Hämtar ICS-URL från miljövariabler
ICS_URL = os.environ.get('ICS_URL')

def clean_event_summary(summary):
    """
    Rensar händelsens sammanfattning enligt följande:
      - Tar bort strängen 'Aktivitetstyp'.
      - Om sammanfattningen innehåller en lista med kurskoder tas alla kurskoder bort utom 'BMA451'.
        Exempel: "BMA401, BMA451, BMK101, KUBM26, DEL 1, dp 6, ..." 
        blir "BMA451, DEL 1, dp 6, ..." (observera att resten av texten bibehålls)
      - Om sammanfattningen innehåller "Laboration Klinisk hematologi:" så lämnas den oförändrad.
      - I övriga fall, om sammanfattningen innehåller "Moment:" så extraheras texten efter detta
        fram till nästa kolon.
    """
    # Ta bort 'Aktivitetstyp'
    summary = re.sub(r'Aktivitetstyp', '', summary)
    
    # Ta bort oönskade kurskoder (behåll endast BMA451)
    undesired_codes = ["BMA401", "BMK101", "KUBM26"]
    for code in undesired_codes:
        summary = re.sub(r'\b' + code + r'\b,?\s*', '', summary)
    
    # Rensa eventuella inledande kommatecken
    summary = re.sub(r'^\s*,\s*', '', summary)
    
    # Om det är en laboration i klinisk hematologi, lämna sammanfattningen oförändrad.
    if "Laboration Klinisk hematologi:" in summary:
        return summary.strip()
    
    # Om sammanfattningen innehåller 'Moment:' extrahera texten efter detta upp till nästa kolon.
    moment_pattern = r'Moment:([^:]+)'
    match = re.search(moment_pattern, summary)
    if match:
        return match.group(1).strip()
    else:
        return summary.strip()

def clean_calendar():
    """
    Hämtar ICS-kalendern, rensar varje VEVENT med den modifierade sammanfattningen och returnerar
    den nya kalendern som iCal-data.
    """
    response = requests.get(ICS_URL)
    original_cal = Calendar.from_ical(response.text)
    
    clean_cal = Calendar()
    clean_cal.add('prodid', '-//Cleaned HKR Calendar//EN')
    clean_cal.add('version', '2.0')
    
    for component in original_cal.walk():
        if component.name == "VEVENT":
            clean_event = Event()
            # Använder den modifierade funktionen för att rensa sammanfattningen
            clean_event.add('summary', clean_event_summary(component.get('summary')))
            clean_event.add('dtstart', component.get('dtstart'))
            clean_event.add('dtend', component.get('dtend'))
            clean_event.add('location', component.get('location', ''))
            clean_event.add('description', component.get('description', ''))
            
            clean_cal.add_component(clean_event)
    
    return clean_cal.to_ical()

if __name__ == "__main__":
    # För testning/radutskrift: skriv ut den rensade iCal-strängen
    cleaned_ical = clean_calendar()
    print(cleaned_ical.decode('utf-8'))

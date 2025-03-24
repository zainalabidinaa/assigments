import os
import requests
import datetime
import re
from icalendar import Calendar, Event

# ICS-URL från HKRs schema med BMA451 (exempel)
ICS_URL = "https://schema.hkr.se/setup/jsp/SchemaICAL.ics?startDatum=2025-03-13&intervallTyp=a&intervallAntal=1&sokMedAND=false&sprak=SV&resurser=k.BMA451%202025%2004%20100%20DAG%20NML%20sv-"

def get_default_time_for_lecture(summary, date_obj):
    """
    Baserat på innehållet i sammanfattningen avgör vi vilken tid ett event ska få om endast ett datum finns.
    Justera dessa tider enligt dina behov.
    """
    if "Föreläsning" in summary:
        start_time = datetime.time(9, 0)
        end_time = datetime.time(10, 30)
    elif "Laboration" in summary:
        start_time = datetime.time(12, 0)
        end_time = datetime.time(13, 0)
    elif "Seminarium" in summary:
        start_time = datetime.time(13, 0)
        end_time = datetime.time(14, 0)
    else:
        # Standardtid om ingen känd aktivitet hittas
        start_time = datetime.time(23, 0)
        end_time = datetime.time(23, 59)
    return (datetime.datetime.combine(date_obj, start_time),
            datetime.datetime.combine(date_obj, end_time))

def adjust_event_times(event, summary):
    """
    Justerar tidsangivelserna för ett event:
      - Om dtstart endast är ett datum (dvs ett date-objekt) så hämtas default-tid baserat på eventets sammanfattning.
      - Om dtstart redan är ett datetime-objekt lämnas tiden oförändrad.
    """
    dtstart_field = event.get('dtstart')
    if not dtstart_field:
        return None, None  # Om inget startdatum finns

    dtstart = dtstart_field.dt
    dtend_field = event.get('dtend')
    dtend = dtend_field.dt if dtend_field else None

    # Om dtstart inte innehåller en tid, avgör tiden baserat på sammanfattningen
    if not isinstance(dtstart, datetime.datetime):
        dtstart, dtend = get_default_time_for_lecture(summary, dtstart)
    # Om dtend saknas men dtstart är ett datetime, sätt ett default-offset (kan anpassas)
    elif dtend is None:
        dtend = dtstart + datetime.timedelta(hours=1)

    return dtstart, dtend

def adjust_event_summary(summary, event):
    """
    Om eventet innehåller en Zoom-länk (i location eller description)
    ändras sammanfattningen så att den inleds med "Zoom ".
    Försöker ta bort en eventuell inledande kurskod.
    """
    location = event.get('location', '')
    description = event.get('description', '')

    if ("zoom" in location.lower()) or ("zoom meeting" in description.lower()):
        # Ta bort en eventuell inledande kurskod (exempelvis "BMA401 VT25 ") med regex
        modified = re.sub(r'^[A-Z]+\d+\s+VT\d+\s+', '', summary)
        return "Zoom " + modified.strip()
    else:
        return summary

def clean_calendar():
    """
    Hämtar ICS-kalendern, filtrerar bort events med "BMA152" i sammanfattningen,
    justerar tidsangivelserna om de saknar tid (baserat på typ av föreläsning) och
    ändrar titeln för Zoom-möten.
    Returnerar den nya kalendern som iCal-data.
    """
    response = requests.get(ICS_URL)
    original_cal = Calendar.from_ical(response.text)

    clean_cal = Calendar()
    clean_cal.add('prodid', '-//Filtered Calendar (BMA451) - Removed BMA152//EN')
    clean_cal.add('version', '2.0')

    for component in original_cal.walk():
        if component.name == "VEVENT":
            summary = component.get('summary')
            # Filtrera bort event med "BMA152" i titeln
            if summary and "BMA152" in summary:
                continue

            # Modifiera titeln om eventet är ett Zoom-möte
            new_summary = adjust_event_summary(summary, component) if summary else summary

            # Justera tiderna baserat på eventets datum och typ
            new_dtstart, new_dtend = adjust_event_times(component, new_summary)

            clean_event = Event()
            clean_event.add('summary', new_summary)
            if new_dtstart is not None:
                clean_event.add('dtstart', new_dtstart)
            if new_dtend is not None:
                clean_event.add('dtend', new_dtend)

            # Kopiera övriga fält
            if component.get('location'):
                clean_event.add('location', component.get('location'))
            if component.get('description'):
                clean_event.add('description', component.get('description'))

            clean_cal.add_component(clean_event)

    return clean_cal.to_ical()

if __name__ == "__main__":
    # För testning: skriv ut den filtrerade och justerade iCal-strängen
    cleaned_ical = clean_calendar()
    print(cleaned_ical.decode('utf-8'))

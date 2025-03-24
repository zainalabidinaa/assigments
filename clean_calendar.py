import os
import requests
import datetime
from icalendar import Calendar, Event

# Hämtar ICS-URL från miljövariabler
ICS_URL = os.environ.get('ICS_URL')

def adjust_event_times(event):
    """
    Justerar tidsangivelserna för ett event:
      - Om dtstart endast är ett datum (dvs ett date-objekt) så sätts starttiden till 23:00.
      - Om dtend saknas eller endast är ett datum, sätts sluttiden till 23:59.
      - Om eventet redan innehåller exakta tidpunkter (datetime) lämnas dessa oförändrade.
    """
    dtstart_field = event.get('dtstart')
    if not dtstart_field:
        return None, None  # Om inget startdatum finns

    dtstart = dtstart_field.dt
    dtend_field = event.get('dtend')
    dtend = dtend_field.dt if dtend_field else None

    # Om dtstart endast innehåller ett datum (dvs ingen tid), sätt standardtiden 23:00
    if not isinstance(dtstart, datetime.datetime):
        dtstart = datetime.datetime.combine(dtstart, datetime.time(23, 0))
        # Om dtend saknas, sätt dtend till samma datum med tid 23:59
        if dtend is None:
            dtend = datetime.datetime.combine(event.get('dtstart').dt, datetime.time(23, 59))
        else:
            # Om dtend endast är ett datum, lägg till standardtiden 23:59
            if not isinstance(dtend, datetime.datetime):
                dtend = datetime.datetime.combine(dtend, datetime.time(23, 59))
    return dtstart, dtend

def clean_calendar():
    """
    Hämtar ICS-kalendern, tar bort events med "BMA152" i sammanfattningen och
    justerar tidsangivelserna om de saknar tid. Returnerar den nya kalendern som iCal-data.
    """
    response = requests.get(ICS_URL)
    original_cal = Calendar.from_ical(response.text)

    clean_cal = Calendar()
    clean_cal.add('prodid', '-//Filtered Calendar (Removed BMA152)//EN')
    clean_cal.add('version', '2.0')

    for component in original_cal.walk():
        if component.name == "VEVENT":
            summary = component.get('summary')
            # Ta bort event med "BMA152" i sammanfattningen
            if summary and "BMA152" in summary:
                continue

            clean_event = Event()
            clean_event.add('summary', summary)

            # Justera tidsangivelser om de bara är datum
            new_dtstart, new_dtend = adjust_event_times(component)
            if new_dtstart is not None:
                clean_event.add('dtstart', new_dtstart)
            if new_dtend is not None:
                clean_event.add('dtend', new_dtend)

            # Kopiera övriga fält om de finns
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

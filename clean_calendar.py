import requests
import datetime
from icalendar import Calendar, Event

# ICS-URL från schema (BMA451)
ICS_URL = "https://schema.hkr.se/setup/jsp/SchemaICAL.ics?startDatum=2025-03-13&intervallTyp=a&intervallAntal=1&sokMedAND=false&sprak=SV&resurser=k.BMA451%202025%2004%20100%20DAG%20NML%20sv-%2C"

# Mappning från identifierande nyckelord i föreläsningsnamnet till önskade tider.
# Exempel: Om sammanfattningen innehåller "Laboratoriemedicin" så sätts start- och sluttid enligt tuple.
lecture_time_mapping = {
    "Laboratoriemedicin": (datetime.time(8, 30), datetime.time(11, 0)),
    # Lägg gärna till fler mappningar, exempelvis:
    # "Föreläsning": (datetime.time(9, 0), datetime.time(10, 30)),
    # "Laboration": (datetime.time(12, 0), datetime.time(13, 0)),
}

def get_default_time_for_lecture(summary, date_obj):
    """
    Letar efter ett nyckelord från lecture_time_mapping i sammanfattningen.
    Om ett matchande nyckelord hittas sätts start- och sluttid enligt mappningen.
    Om inget matchande nyckelord finns används defaulttiden 23:00 - 23:59.
    """
    for key, (start_time, end_time) in lecture_time_mapping.items():
        if key in summary:
            return (datetime.datetime.combine(date_obj, start_time),
                    datetime.datetime.combine(date_obj, end_time))
    return (datetime.datetime.combine(date_obj, datetime.time(23, 0)),
            datetime.datetime.combine(date_obj, datetime.time(23, 59)))

def adjust_event_times(event, summary):
    """
    Om eventet endast har ett datum (dvs dtstart saknar tid) används get_default_time_for_lecture()
    för att sätta rätt tid baserat på eventets sammanfattning.
    Om dtstart redan är ett datetime-objekt används det som det är (och dtend sätts till dtstart +1 timme om det saknas).
    """
    dtstart_field = event.get('dtstart')
    if not dtstart_field:
        return None, None
    dtstart = dtstart_field.dt
    dtend_field = event.get('dtend')
    dtend = dtend_field.dt if dtend_field else None

    if not isinstance(dtstart, datetime.datetime):
        # dtstart är ett date-objekt
        dtstart, dtend = get_default_time_for_lecture(summary, dtstart)
    elif dtend is None:
        dtend = dtstart + datetime.timedelta(hours=1)
    return dtstart, dtend

def clean_calendar():
    """
    Hämtar ICS-kalendern från schema.hkr.se, filtrerar bort event med "BMA152" i titeln
    och justerar tidsangivelserna baserat på eventets sammanfattning (t.ex. att identifiera
    "Laboratoriemedicin" och sätta rätt tider).
    Returnerar den nya kalendern som iCal-data.
    """
    response = requests.get(ICS_URL)
    original_cal = Calendar.from_ical(response.text)

    clean_cal = Calendar()
    clean_cal.add('prodid', '-//Filtered Schema Calendar for Lectures//EN')
    clean_cal.add('version', '2.0')

    for component in original_cal.walk():
        if component.name == "VEVENT":
            summary = component.get('summary')
            # Ta bort event som innehåller "BMA152" i titeln
            if summary and "BMA152" in summary:
                continue

            # Sätt rätt tid om endast datum anges
            new_dtstart, new_dtend = adjust_event_times(component, summary)

            new_event = Event()
            new_event.add('summary', summary)
            if new_dtstart:
                new_event.add('dtstart', new_dtstart)
            if new_dtend:
                new_event.add('dtend', new_dtend)

            # Kopiera över övriga fält om de finns
            if component.get('location'):
                new_event.add('location', component.get('location'))
            if component.get('description'):
                new_event.add('description', component.get('description'))

            clean_cal.add_component(new_event)
    return clean_cal.to_ical()

if __name__ == "__main__":
    cleaned_ical = clean_calendar()
    print(cleaned_ical.decode('utf-8'))

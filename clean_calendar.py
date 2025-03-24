import requests
import datetime
import re
from icalendar import Calendar, Event

# ICS-URL:er
USER_ICS_URL = "https://hkr.instructure.com/feeds/calendars/user_xOrYwkKlKq1lm1iOXuRabKHLhfIVId0kLKCCs7C4.ics"
SCHEMA_ICS_URL = "https://schema.hkr.se/setup/jsp/SchemaICAL.ics?startDatum=2025-03-13&intervallTyp=a&intervallAntal=1&sokMedAND=false&sprak=SV&resurser=k.BMA451%202025%2004%20100%20DAG%20NML%20sv-%2C"

def load_calendar(url):
    response = requests.get(url)
    return Calendar.from_ical(response.text)

def clean_text(text):
    """
    Enkel funktion för att "rensa" texten från onödig whitespace
    och göra om till gemener för jämförelse.
    """
    return re.sub(r'\s+', ' ', text).strip().lower()

def extract_lecture_title(summary):
    """
    Försök extrahera ett centralt del av titeln.
    I detta exempel antar vi att ordet "laboratoriemedicin" är
    karakteristiskt och att den relevanta titeln börjar där.
    Om inte finns returneras hela sammanfattningen.
    """
    summary_clean = clean_text(summary)
    idx = summary_clean.find("laboratoriemedicin")
    if idx != -1:
        # Ta ut texten från "laboratoriemedicin" och vidare,
        # men stopp vid t.ex. "sign:" eller "moment:" om de förekommer.
        sub = summary_clean[idx:]
        m = re.search(r'(sign:|moment:)', sub)
        if m:
            return sub[:m.start()].strip()
        else:
            return sub.strip()
    return summary_clean

def find_schema_times(user_event, schema_events):
    """
    För ett user_event (som saknar tid, dvs endast ett datum)
    letar vi igenom schema_events (från schemat) och söker efter ett event
    med samma datum där den "rensade" titeln (utifrån lecture_title) matchar (enkel substring-match).
    Returnerar (dtstart, dtend) från schema-eventet om en matchning hittas, annars None.
    """
    # Hämta datumet (antingen om dtstart är date eller datetime)
    dtstart_field = user_event.get('dtstart')
    if not dtstart_field:
        return None
    user_date = dtstart_field.dt if isinstance(dtstart_field.dt, datetime.date) else dtstart_field.dt.date()
    user_title = extract_lecture_title(user_event.get('summary', ''))
    
    for se in schema_events:
        # Vi kräver att schema-eventet har tid (dtstart som datetime)
        schema_dt = se.get('dtstart').dt
        if not isinstance(schema_dt, datetime.datetime):
            continue
        schema_date = schema_dt.date()
        if schema_date == user_date:
            schema_title = extract_lecture_title(se.get('summary', ''))
            # Enkel matchning: om den rensade titeln från användarens event
            # finns som substring i schema-eventets rensade titel, eller vice versa.
            if user_title in schema_title or schema_title in user_title:
                return se.get('dtstart').dt, se.get('dtend').dt
    return None

def adjust_zoom_title(title, event):
    """
    Om eventet innehåller "zoom" i location eller description,
    lägg till "Zoom " i början av titeln om det inte redan finns.
    """
    loc = event.get('location', '')
    desc = event.get('description', '')
    if ("zoom" in loc.lower()) or ("zoom meeting" in desc.lower()):
        if not title.lower().startswith("zoom "):
            return "Zoom " + title
    return title

def clean_calendar():
    """
    Huvudfunktion:
      - Laddar användarens kalender från Instructure.
      - Laddar schema-kalendern (som innehåller korrekta tider).
      - Itererar över användarens events.
          * Filtrerar bort de med "BMA152" i titeln.
          * Om eventet saknar tid (dtstart är date) så försöker vi hitta
            motsvarande schema-event (samma datum och liknande titel).
          * Uppdaterar dtstart och dtend om vi hittar en match.
          * Justerar titeln om det är ett Zoom-event.
      - Returnerar en ny kalender med de uppdaterade eventen.
    """
    user_cal = load_calendar(USER_ICS_URL)
    schema_cal = load_calendar(SCHEMA_ICS_URL)
    # Skapa lista över schema-event
    schema_events = [comp for comp in schema_cal.walk() if comp.name == "VEVENT"]

    new_cal = Calendar()
    new_cal.add('prodid', '-//Uppdaterad Kalender//EN')
    new_cal.add('version', '2.0')

    for comp in user_cal.walk():
        if comp.name != "VEVENT":
            continue

        summary = comp.get('summary')
        if not summary:
            continue

        # Filtrera bort event med "BMA152" i titeln
        if "BMA152" in summary:
            continue

        # Ta ut en "rensad" version av titeln
        lecture_title = extract_lecture_title(summary)

        # Om dtstart saknar tid (dvs endast är ett date) försöker vi hitta tider från schemat
        dtstart_field = comp.get('dtstart')
        if dtstart_field is None:
            continue

        # Om dtstart är ett datetime, vi antar att tiden redan är satt.
        if isinstance(dtstart_field.dt, datetime.datetime):
            new_dtstart = dtstart_field.dt
            dtend_field = comp.get('dtend')
            new_dtend = dtend_field.dt if dtend_field else new_dtstart + datetime.timedelta(hours=1)
        else:
            # dtstart är bara ett datum – försök hämta tider från schema
            times = find_schema_times(comp, schema_events)
            if times is None:
                # Om vi inte hittar någon match i schemat kan vi hoppa över eventet
                continue
            new_dtstart, new_dtend = times

        # Justera titeln om eventet verkar vara ett Zoom-event
        new_title = adjust_zoom_title(lecture_title, comp)

        new_event = Event()
        new_event.add('summary', new_title)
        new_event.add('dtstart', new_dtstart)
        new_event.add('dtend', new_dtend)

        # Kopiera övriga fält om de finns
        if comp.get('location'):
            new_event.add('location', comp.get('location'))
        if comp.get('description'):
            new_event.add('description', comp.get('description'))

        new_cal.add_component(new_event)

    return new_cal.to_ical()

if __name__ == "__main__":
    updated_ical = clean_calendar()
    print(updated_ical.decode('utf-8'))

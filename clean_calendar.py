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
    """Tar bort extra whitespace och gör om till gemener för jämförelse."""
    return re.sub(r'\s+', ' ', text).strip().lower()

def extract_lecture_title(summary):
    """
    Försöker extrahera den centrala delen av titeln.
    Exempelvis:
      "Program: ... Laboratoriemedicin vår T3 [BMA401 VT25]" → "laboratoriemedicin vår t3"
    Om ordet "laboratoriemedicin" finns, returneras texten från det ordet
    till exempelvis "sign:" eller "moment:" om de förekommer.
    Om inte returneras hela sammanfattningen (oförändrad).
    """
    summary_clean = clean_text(summary)
    idx = summary_clean.find("laboratoriemedicin")
    if idx != -1:
        sub = summary_clean[idx:]
        m = re.search(r'(sign:|moment:)', sub)
        if m:
            return sub[:m.start()].strip()
        else:
            return sub.strip()
    return summary.strip()

def find_schema_times(user_event, schema_events):
    """
    För ett event i din kalender som endast har ett datum (saknar tid)
    letar vi igenom schema‑kalenderns events efter ett event med samma datum
    där den rensade titeln (baserat på extract_lecture_title) matchar (substring-matchning).
    Returnerar (dtstart, dtend) från schema‑eventet om en matchning hittas, annars None.
    """
    dtstart_field = user_event.get('dtstart')
    if not dtstart_field:
        return None
    # Om dtstart är ett date-objekt, använd det; om det är datetime, extrahera datumdelen.
    user_date = dtstart_field.dt if isinstance(dtstart_field.dt, datetime.date) else dtstart_field.dt.date()
    user_title = extract_lecture_title(user_event.get('summary', ''))
    
    for se in schema_events:
        schema_dtstart = se.get('dtstart').dt
        if not isinstance(schema_dtstart, datetime.datetime):
            continue
        schema_date = schema_dtstart.date()
        if schema_date == user_date:
            schema_title = extract_lecture_title(se.get('summary', ''))
            # Enkel substring-matchning (båda sätt)
            if (user_title in schema_title) or (schema_title in user_title):
                return se.get('dtstart').dt, se.get('dtend').dt
    return None

def adjust_zoom_title(title, event):
    """
    Om eventets location eller description innehåller "zoom" (gemener)
    läggs "Zoom " till i början av titeln (om det inte redan finns).
    """
    loc = event.get('location', '')
    desc = event.get('description', '')
    if ("zoom" in loc.lower()) or ("zoom meeting" in desc.lower()):
        if not title.lower().startswith("zoom "):
            return "Zoom " + title
    return title

def clean_calendar():
    """
    Huvudfunktionen:
      - Laddar användarens kalender (Instructure) och schema‑kalendern (för tider)
      - Itererar över varje event i användarens kalender.
          * Filtrerar bort event med "BMA152" i titeln.
          * Om eventet har en tid (dtstart som datetime) används den oförändrad.
          * Om endast ett datum anges (dtstart är date) så söks en matchning i schema‑kalendern.
            Om ingen matchning hittas används defaulttiden 23:00–23:59.
          * Titeln rensas med extract_lecture_title och justeras med adjust_zoom_title.
      - Returnerar en ny kalender med alla (uppdaterade) events.
    """
    user_cal = load_calendar(USER_ICS_URL)
    schema_cal = load_calendar(SCHEMA_ICS_URL)
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

        # Extrahera en rensad titel
        title = extract_lecture_title(summary)

        dtstart_field = comp.get('dtstart')
        if not dtstart_field:
            continue

        if isinstance(dtstart_field.dt, datetime.datetime):
            # Eventet har redan en tid, behåll den
            new_dtstart = dtstart_field.dt
            dtend_field = comp.get('dtend')
            new_dtend = dtend_field.dt if dtend_field else new_dtstart + datetime.timedelta(hours=1)
        else:
            # Eventet har endast ett datum – försök hämta tider från schema
            times = find_schema_times(comp, schema_events)
            if times is None:
                # Om ingen matchning hittas, använd defaulttiden 23:00–23:59
                date_obj = dtstart_field.dt
                new_dtstart = datetime.datetime.combine(date_obj, datetime.time(23, 0))
                new_dtend = datetime.datetime.combine(date_obj, datetime.time(23, 59))
            else:
                new_dtstart, new_dtend = times

        new_title = adjust_zoom_title(title, comp)

        new_event = Event()
        new_event.add('summary', new_title)
        new_event.add('dtstart', new_dtstart)
        new_event.add('dtend', new_dtend)
        if comp.get('location'):
            new_event.add('location', comp.get('location'))
        if comp.get('description'):
            new_event.add('description', comp.get('description'))
        new_cal.add_component(new_event)

    return new_cal.to_ical()

if __name__ == "__main__":
    updated_ical = clean_calendar()
    print(updated_ical.decode('utf-8'))

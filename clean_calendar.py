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
    """ Tar bort extra whitespace och gör om till gemener för jämförelse. """
    return re.sub(r'\s+', ' ', text).strip().lower()

def extract_lecture_title(summary):
    """
    Försöker extrahera den centrala delen av titeln.
    Exempelvis: 
      "Program: ... Laboratoriemedicin vår T3 [BMA401 VT25]" → "laboratoriemedicin vår t3"
    Om ordet "laboratoriemedicin" finns, returneras texten från det ordet till exempelvis "sign:" eller "moment:".
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
    där den rensade titeln (baserat på extract_lecture_title) matchar (substring-match).
    Returnerar (dtstart, dtend) från schema‑eventet om en matchning hittas, annars None.
    """
    dtstart_field = user_event.get('dtstart')
    if not dtstart_field:
        return None
    # Om dtstart är ett date, hämta datumet; om det är datetime, extrahera datumdelen.
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
            if user_title in schema_title or

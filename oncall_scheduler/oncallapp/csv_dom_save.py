import csv
from io import StringIO
import uuid
from datetime import datetime, time
from oncallapp.models import ScheduleTemplate, TemplateEvent

def parse_iso_datetime(dt_str):
    """
    Parse ISO date or datetime string.
    If only date is present, returns datetime at 00:00.
    """
    try:
        # Try full datetime first
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Try date only
        try:
            d = datetime.strptime(dt_str, "%Y-%m-%d")
            return datetime.combine(d.date(), time(0, 0))
        except ValueError:
            raise


def parse_csv_to_events(csv_content):
    """
    Parse CSV string to a list of event dicts.
    Expects columns: Attendee,Start,End,Category
    """
    reader = csv.DictReader(StringIO(csv_content))
    events = []
    for row in reader:
        # Defensive: skip incomplete rows
        if not (row.get('Attendee') and row.get('Start') and row.get('End') and row.get('Category')):
            continue
        events.append({
            'attendee': row['Attendee'],
            'start': row['Start'],
            'end': row['End'],
            'category': row['Category']
        })
    return events

def create_schedule_template_from_csv(db_session, csv_content, category):
    """
    Create a ScheduleTemplate and TemplateEvent entries from CSV content.
    The template is named after the category.
    Returns the created ScheduleTemplate instance.
    """
    # Parse events from CSV
    events = parse_csv_to_events(csv_content)
    if not events:
        raise ValueError("No valid events found in CSV.")

    # Check for duplicate template names and make unique if needed
    base_name = category or "Imported Template"
    name = base_name
    i = 1
    while db_session.query(ScheduleTemplate).filter_by(name=name).first():
        i += 1
        name = f"{base_name} ({i})"

    # Calculate start/end dates for the template
    start_dates = []
    end_dates = []
    for event in events:
        try:
            start_dates.append(parse_iso_datetime((event['start'])))
            end_dates.append(parse_iso_datetime((event['end'])))
        except Exception:
            continue
    if not start_dates or not end_dates:
        raise ValueError("Could not determine start/end dates from CSV.")

    template = ScheduleTemplate(
        id=str(uuid.uuid4()),  # simple unique id
        name=name,
        start_date=min(start_dates).date(),
        end_date=max(end_dates).date(),
        repeat_weekly=False,
        test_mode=False
    )
    db_session.add(template)
    db_session.flush()  # Get template.id

    # Create TemplateEvent entries
    total= 0
    for event in events:
        total = total + 1
        try:
            start_dt = parse_iso_datetime(event['start'])
            end_dt = parse_iso_datetime(event['end'])
        except Exception:
            continue
        tevent = TemplateEvent(
            id = total ,
            title=event['attendee'],
            start=start_dt,
            end=end_dt,
            resource_id = 1,
            all_day=False,
            template_id=template.id
        )
        db_session.add(tevent)

    db_session.commit()
    return template
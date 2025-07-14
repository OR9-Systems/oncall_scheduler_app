import csv
from io import StringIO
import uuid
from datetime import datetime, time,  timedelta  
from oncallapp.models import ScheduleTemplate, TemplateEvent
def parse_iso_datetime(dt_str):
    """
    Parse a date/time string in various common formats.
    Supports:
      - 'YYYY-MM-DD'
      - 'YYYY-MM-DD HH:MM'
      - 'YYYY-MM-DD HH:MM:SS'
      - 'YYYY-MM-DDTHH:MM'
      - 'YYYY-MM-DDTHH:MM:SS'
    If only date is present, returns datetime at 00:00.
    """
    dt_str = dt_str.strip()
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unrecognized datetime format: {dt_str}")


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

def create_schedule_template_from_csv(
    db_session,
    csv_content,
    category,
    each_day=False,
    default_start_time=time(0, 0),
    default_end_time=time(0, 0)
):
    """
    Create a ScheduleTemplate and TemplateEvent entries from CSV content.
    If `each_day=True`, creates daily entries from start to end dates.
    If start/end times are missing in CSV, uses provided defaults.
    """
    events = parse_csv_to_events(csv_content)
    if not events:
        raise ValueError("No valid events found in CSV.")

    # Unique name logic
    base_name = category or "Imported Template"
    name = base_name
    i = 1
    while db_session.query(ScheduleTemplate).filter_by(name=name).first():
        i += 1
        name = f"{base_name} ({i})"

    # Calculate overall start/end range
    start_dates, end_dates = [], []
    for event in events:
        try:
            start_dt = parse_iso_datetime(event['start'])
            end_dt = parse_iso_datetime(event['end'])
            start_dates.append(start_dt)
            end_dates.append(end_dt)
        except Exception:
            continue
    if not start_dates or not end_dates:
        raise ValueError("Could not determine start/end dates from CSV.")

    template = ScheduleTemplate(
        id=str(uuid.uuid4()),
        name=name,
        start_date=min(start_dates).date(),
        end_date=max(end_dates).date(),
        repeat_weekly=False,
        test_mode=False
    )
    db_session.add(template)
    db_session.flush()

    # Max ID logic
    total_id = db_session.query(TemplateEvent.id).order_by(TemplateEvent.id.desc()).first()
    total_id = total_id[0] if total_id else 0

    for event in events:
        try:
            raw_start = parse_iso_datetime(event['start'])
            raw_end = parse_iso_datetime(event['end'])
        except Exception:
            continue

        # Use defaults if time is missing
        start_time = raw_start.time() if raw_start.time() != time(0, 0) else default_start_time
        end_time = raw_end.time() if raw_end.time() != time(0, 0) else default_end_time
        start_date = raw_start.date()
        end_date = raw_end.date()

        if each_day:
            current_day = start_date
            while current_day <= end_date:
                total_id += 1
                start_dt = datetime.combine(current_day, start_time)
                end_dt = datetime.combine(current_day, end_time)
                tevent = TemplateEvent(
                    id=total_id,
                    title=event['attendee'],
                    start=start_dt,
                    end=end_dt,
                    resource_id=1,
                    all_day=False,
                    template_id=template.id
                )
                db_session.add(tevent)
                current_day += timedelta(days=1)
        else:
            total_id += 1
            start_dt = datetime.combine(start_date, start_time)
            end_dt = datetime.combine(end_date, end_time)
            all_day = (end_date > start_date and start_time == time(0, 0) and end_time == time(0, 0))
            tevent = TemplateEvent(
                id=total_id,
                title=event['attendee'],
                start=start_dt,
                end=end_dt,
                resource_id=1,
                all_day=all_day,
                template_id=template.id
            )
            db_session.add(tevent)

    db_session.commit()
    return template
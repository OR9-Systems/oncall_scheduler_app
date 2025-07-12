import csv
from io import StringIO

def extra_data_to_csv(extra_data, category=None, user_filter=None):
    """
    Convert extra_data dict to CSV string.
    Optionally filter by category and/or attendee name.
    Orders items by Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM).
    """
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Attendee', 'Start', 'End', 'Category'])  # CSV header

    all_items = []
    for cat, items in extra_data.items():
        if category and cat != category:
            continue
        for item in items:
            attendee = item['attendee']
            if user_filter and attendee != user_filter:
                continue
            all_items.append((item['start'], attendee, item['end'], cat))

    # Sort by start date string (ISO format sorts correctly)
    all_items.sort(key=lambda x: x[0])

    for start, attendee, end, cat in all_items:
        writer.writerow([attendee, start, end, cat])
    return output.getvalue()



def csv_to_extra_data(csv_content):
    """
    Convert CSV string to extra_data dict.
    """
    reader = csv.DictReader(StringIO(csv_content))
    extra_data = {}
    
    for row in reader:
        attendee = row['Attendee']
        start = row['Start']
        end = row['End']
        cat = row['Category']
        
        if attendee not in extra_data:
            extra_data[attendee] = []
        
        extra_data[attendee].append({
            'attendee': attendee,
            'start': start,
            'end': end,
            'category': cat
        })
    
    return extra_data  
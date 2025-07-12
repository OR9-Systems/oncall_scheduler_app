from icalendar import Calendar
from collections import Counter

#
def parse_ical(file_data, user_email, category):
    matched_tags = {'attendee_email_counter': 0}
    start_stop_times = []
    r_catagory = ""

    calendar = Calendar.from_ical(file_data)

    for component in calendar.walk():
        r_catagory = component.get('categories',[])
        if r_catagory:
            r_catagory = r_catagory.to_ical().decode('utf-8').strip()
        if component.name == "VEVENT" and r_catagory  == category:
            attendees = component.get('attendee', [])
            if not isinstance(attendees, list):
                attendees = [attendees]

            for attendee in attendees:
                if user_email in str(attendee):
                    matched_tags['attendee_email_counter'] += 1
                    start_stop_times.append({
                        'start': component.get('dtstart').dt,
                        'stop': component.get('dtend').dt
                    })

    return matched_tags, start_stop_times


def load_ical_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


if __name__ == "__main__":
    # Test the functionality
    file_path = "test.ics"  # Replace with your .ics file path
    user_email = "orion.nelson@intact.net"  # Replace with the email to search for
    category = "On Call: Primary"  # Replace with the category to filter

    try:
        file_data = load_ical_file(file_path)
        matched_tags, start_stop_times = parse_ical(file_data, user_email, category)

        print("Matched Tags:", matched_tags)
        print("Start/Stop Times:", start_stop_times)
    except Exception as e:
        print("An error occurred:", e)
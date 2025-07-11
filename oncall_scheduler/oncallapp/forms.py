from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, BooleanField, DateTimeField, FileField, RadioField,FieldList,StringField , TextAreaField
from wtforms.validators import DataRequired
from oncallapp.models import UserGroup, User
from icalendar import Calendar
from collections import Counter

class CreateUserGroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired()])
    submit = SubmitField('Create Group')

class ImportScheduleForm(FlaskForm):
    file = FileField('Upload .ics File', validators=[])
    calendars = RadioField('Select Calendar', choices=[], validators=[])  # Initially empty, no validation
    matched_tags = FieldList(StringField('Tag'), min_entries=0)  # Placeholder for unmatched tags
    extra_data_text = TextAreaField('Edit Extra Data') #I want this to be what matters
    submit = SubmitField('Import Calendar')
    def process_ics_file(self, uploaded_file, extra_data_to_csv):
        category_to_tags = {}
        matched_tags = {}
        extra_data = {}
        event_types = set()
        extra_data_csv = ""

        ical_data = uploaded_file.read()
        calendar = Calendar.from_ical(ical_data)

        for component in calendar.walk():
            if component.name == "VEVENT":
                event_name = component.get("categories")
                summary = component.get("summary")
                attendee = component.get("ATTENDEE")

                # Decode event_name *catagory* if it exists
                if event_name:
                    event_name = event_name.to_ical().decode('utf-8').strip()
                if event_name:
                    event_types.add(event_name)
                    if event_name not in category_to_tags:
                        category_to_tags[event_name] = []
                    if summary:
                        category_to_tags[event_name].append(str(summary))

                # Process matched tags with attendees
                if attendee:
                    attendee_email = str(attendee).split(":")[-1].strip()
                    if "@" in attendee_email:
                        attendee_email = attendee_email.replace(')','').replace(']','')
                        attendee_email = (attendee_email.split('@')[0]).replace('.', ' ').title()
                        if event_name:
                            if event_name not in matched_tags:
                                matched_tags[event_name] = []
                            matched_tags[event_name].append({
                                "summary": summary,
                                "attendee": attendee_email,
                                "start": component.get("dtstart").dt if component.get("dtstart") else None,
                                "end": component.get("dtend").dt if component.get("dtend") else None
                            })
                            if 'attendee_email_counter' not in matched_tags:
                                matched_tags['attendee_email_counter'] = {}
                            if event_name not in matched_tags['attendee_email_counter']:
                                matched_tags['attendee_email_counter'][event_name] = Counter()
                            matched_tags['attendee_email_counter'][event_name][attendee_email] += 1

        self.calendars.choices = [(event, event) for event in sorted(event_types)]

        extra_data = matched_tags.copy()
        extra_data.pop('attendee_email_counter', None)
        attendee_email_counter = matched_tags.get('attendee_email_counter', {})
        selected_category = self.calendars.data or None
        extra_data_csv = extra_data_to_csv(extra_data, category=selected_category)
        if extra_data_csv:
            self.extra_data_text.data = extra_data_csv

        return {
            "matched_tags": attendee_email_counter,
            "extra_data": extra_data,
            "extra_data_csv": extra_data_csv
        }

class CreateScheduleForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()])
    time_segment = SelectField('Time Segment', choices=[('Morning', 'Morning'), ('Evening', 'Evening')])
    group = SelectField('Group', coerce=int, validators=[DataRequired()])
    user = SelectField('User', coerce=int, validators=[DataRequired()])
    submit_button = SubmitField('Create Schedule')

    def __init__(self, group_id=None, *args, **kwargs):
        super(CreateScheduleForm, self).__init__(*args, **kwargs)
        self.group.choices = [(group.id, group.name) for group in UserGroup.query.all()]
        
        if group_id:
            self.user.choices = [(user.id, user.name) for user in User.query.filter_by(group_id=group_id).all()]
        else:
            self.user.choices = []

class ModifyUserForm(FlaskForm):
    user = SelectField('User', choices=[], coerce=str, validators=[DataRequired()])
    group = SelectField('User Group', coerce=int, validators=[DataRequired()])
    action = SelectField('Action', choices=[('add', 'Add User'), ('remove', 'Remove User')], validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, group_id=None, *args, **kwargs):
        group_id = group_id or 1
        super(ModifyUserForm, self).__init__(*args, **kwargs)
        self.group.choices = [(group.id, group.name) for group in UserGroup.query.all()]
        if group_id:
            self.group.data = group_id
            self.user.choices = [(user.name, user.name) for user in User.query.filter_by(group_id=group_id).all()]
        else:
            self.user.choices = []

class CreateUserForm(FlaskForm):
    name = StringField('User Name', validators=[DataRequired()])
    group = SelectField('User Group', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create User')

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        self.group.choices = [(group.id, group.name) for group in UserGroup.query.all()]
        print(f"Group Choices: {self.group.choices}", flush=True)  # Debugging line

class CreateScheduleTemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired()])
    group = SelectField('User Group', coerce=int, validators=[DataRequired()])
    #Auto Generated
    start_date = DateTimeField('Start Date', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    end_date = DateTimeField('End Date', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    repeat_weekly = BooleanField('Repeat Weekly')
    submit = SubmitField('Create Template')

    def __init__(self, group_id=None, *args, **kwargs):
        super(CreateScheduleTemplateForm, self).__init__(*args, **kwargs)
        self.group.choices = [(group.id, group.name) for group in UserGroup.query.all()]
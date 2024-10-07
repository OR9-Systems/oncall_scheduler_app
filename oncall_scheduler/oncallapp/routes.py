from flask import render_template, redirect, url_for, flash, request, jsonify, session
from oncallapp import app, db
from oncallapp.forms import CreateUserGroupForm, CreateScheduleForm, CreateUserForm, CreateScheduleTemplateForm
from oncallapp.models import UserGroup, Schedule, User, ScheduleTemplate, TemplateEvent
import uuid
import datetime
from dateutil import parser

@app.route('/')
def index():
    schedules = Schedule.query.all()
    return render_template('index.html', schedules=schedules)



@app.route('/create_user', methods=['GET', 'POST'])
def create_user():
    form = CreateUserForm()

    # Print the form data for debugging
    print(f"Form Data: {form.data}", flush=True)
    
    if form.validate_on_submit():
        print("Form validated successfully.", flush=True)
        user = User(name=form.name.data, group_id=form.group.data)
        
        # Print the user information before adding to the database
        print(f"Creating User: {user.name} in Group ID: {user.group_id}", flush=True)
        
        db.session.add(user)
        db.session.commit()
        flash('User created successfully!')
        return redirect(url_for('create_user'))  # Redirect to the same page or another page if needed
    else:
        print("Form validation failed.", flush=True)
        for field, errors in form.errors.items():
            print(f"Field: {field}, Errors: {errors}", flush=True)

    return render_template('create_user.html', form=form)

@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    form = CreateUserGroupForm()
    if form.validate_on_submit():
        group = UserGroup(name=form.name.data)
        db.session.add(group)
        db.session.commit()
        flash('User group created successfully!')
        return redirect(url_for('index'))
    return render_template('create_group.html', form=form)


@app.route('/create_schedule', methods=['GET', 'POST'])
def create_schedule():
    # Determine the group_id: if None, default to the first group
    if request.method == 'POST':
        group_id = request.form.get('group', type=int)
    else:
        group_id = request.args.get('group', type=int) or (UserGroup.query.first().id if UserGroup.query.first() else None)
    
    form = CreateScheduleForm(group_id=group_id)
    print(f"Group ID: {group_id}", flush=True)


    # Print all users and their respective groups
    all_users = User.query.all()
    if all_users:
        for user in all_users:
            group_name = user.group.name if user.group else "No Group"
            print(f"User: {user.name}, Group: {group_name}", flush=True)
    else:
        print("No Users",flush=True)

    # Populate user choices based on the selected or default group
    if group_id:
        form.user.choices = [(user.id, user.name) for user in User.query.filter_by(group_id=group_id).all()]
        print(f"User choices: {form.user.choices}", flush=True)

    # Handle form submission
    if form.validate_on_submit():
        # Create a new schedule entry
        schedule = Schedule(
            date=form.date.data,
            time_segment=form.time_segment.data,
            user_id=form.user.data
        )
        db.session.add(schedule)
        db.session.commit()
        flash('Schedule created successfully!')
        return redirect(url_for('index'))

    # Render the form, either initially or after a selection has been made
    return render_template('create_schedule.html', form=form)


@app.route('/ecworks')
def ec_works():
    return render_template('Event Calendar.htm')


@app.route('/view_schedule')
def view_schedule():
    schedules = Schedule.query.all()
    return render_template('view_schedule.html', schedules=schedules)





@app.route('/create_template', methods=['GET', 'POST'])
def create_template():
    form = CreateScheduleTemplateForm()

    # Check if template_id exists in session; if not, create a new unique ID
    if 'template_id' not in session:
        # Generate a new UUID or use the Flask session ID
        session['template_id'] = str(uuid.uuid4())  # Using UUID for uniqueness
    print(f"Session ID:{session['template_id']}", flush=True)

    # Use the session 'template_id'
    template_id = session['template_id']
    template = ScheduleTemplate.query.filter_by(id=template_id).first()

    if request.method == 'POST':
        test_mode = request.form.get('test_mode', 'false') == 'true'  # Capture test mode flag
        group_id = request.form.get('group', type=int)

        if template:
            # Updating an existing template
            template.name = form.name.data
            template.start_date = form.start_date.data
            template.end_date = form.end_date.data
            template.repeat_weekly = form.repeat_weekly.data
            template.test_mode = test_mode
        else:
            # Creating a new template
            template = ScheduleTemplate(
                id=template_id,  # Assign the session ID as template ID
                name=form.name.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                repeat_weekly=form.repeat_weekly.data,
                test_mode=test_mode
            )
            db.session.add(template)
            db.session.commit()

        # Sync events from the frontend
        events_from_frontend = request.json.get('events', [])
        sync_template_events(template.id, events_from_frontend)

        flash('Schedule template created and events synced successfully!')
        return redirect(url_for('create_template'))

    return render_template('create_template.html', form=form, template=template)


def sync_template_events(template_id, events_from_frontend):
    """
    Syncs the TemplateEvent table with the events sent from the frontend.
    Handles adding new events, updating existing ones, and deleting removed events.
    """
    existing_events = TemplateEvent.query.filter_by(template_id=template_id).all()
    existing_events_dict = {event.id: event for event in existing_events}

    frontend_event_ids = set()
    for event_data in events_from_frontend:
        event_id = event_data.get('id')
        frontend_event_ids.add(event_id)

        if event_id in existing_events_dict:
            event = existing_events_dict[event_id]
            event.title = event_data.get('title', event.title)
            event.start = event_data.get('start', event.start)
            event.end = event_data.get('end', event.end)
            event.all_day = event_data.get('all_day', event.all_day)
            event.group_id = event_data.get('group_id', event.group_id)
        else:
            new_event = TemplateEvent(
                title=event_data['title'],
                start=event_data['start'],
                end=event_data['end'],
                all_day=event_data.get('all_day', False),
                template_id=template_id,
                group_id=event_data.get('group_id')
            )
            db.session.add(new_event)

    # Delete events that no longer exist
    for event_id, event in existing_events_dict.items():
        if event_id not in frontend_event_ids:
            db.session.delete(event)

    db.session.commit()

@app.route('/view_templates')
def view_templates():
    templates = ScheduleTemplate.query.all()
    return render_template('view_templates.html', templates=templates)

@app.route('/save_event', methods=['POST'])
def save_event():
    event_data = request.get_json()
    print(f"Received Event Data: {event_data}", flush=True)  # Debugging line
    
    event_id = event_data.get('id', None)
    start_time_str = event_data.get('start', None)
    end_time_str = event_data.get('end', None)
    resource_id = event_data.get('resourceId', None)
    template_id = event_data.get('template_id', None)
    
    if not template_id:
        return jsonify({'status': 'error', 'message': 'Template ID is required.'}), 400

    # Validate required data
    if not start_time_str or not end_time_str:
        return jsonify({'status': 'error', 'message': 'Start and end time are required.'}), 400

    # Convert the date strings to datetime objects
    # Convert the date strings to datetime objects
    try:
        # Parse ISO 8601 strings using dateutil.parser.parse
        start_time = parser.parse(start_time_str)
        end_time = parser.parse(end_time_str)
    except ValueError as e:
        print(f"Date parsing error: {e}", flush=True)
        return jsonify({'status': 'error', 'message': 'Invalid date format.'}), 400


    # Log current state of TemplateEvent items
    all_events = TemplateEvent.query.all()
    print(f"All Template Events Before Save: {[event.__dict__ for event in all_events]}", flush=True)

    # Update the event if it already exists
    if event_id:
        event = TemplateEvent.query.get(event_id)
        if event:
            print(f"Updating Event: {event_id}", flush=True)
            event.title = event_data.get('title', event.title)
            event.start = start_time
            event.end = end_time
            event.resource_id = resource_id
            event.group_id = event_data.get('group_id', event.group_id)
            db.session.commit()
            print(f"Event {event_id} updated successfully.", flush=True)
            return jsonify({'status': 'success', 'message': 'Event updated successfully.'})
        else:
            print(f"Event ID {event_id} not found, creating new event.", flush=True)

    # Create a new event if it doesn't exist
    print("Creating new event", flush=True)
    new_event = TemplateEvent(
        title=event_data.get('title', 'Untitled Event'),
        start=start_time,
        end=end_time,
        resource_id=resource_id,
        template_id=template_id,
        user_id=None,  # Adjust based on your user logic
        group_id=event_data.get('group_id', None)
    )
    db.session.add(new_event)
    db.session.commit()

    print(f"New event created with ID: {new_event.id}", flush=True)

    # Log all events after creation
    all_events_after_create = TemplateEvent.query.all()
    print(f"All Template Events After Create: {[event.__dict__ for event in all_events_after_create]}", flush=True)

    return jsonify({'status': 'success', 'message': 'Event created successfully.', 'event_id': new_event.id})



@app.route('/load_events/<template_id>', methods=['GET'])
def load_events(template_id):
    # Fetch events for the given template_id
    events = TemplateEvent.query.filter_by(template_id=template_id).all()

    # Prepare events data to return as JSON
    events_data = []
    for event in events:
        events_data.append({
            'id': event.id,
            'title': event.title,
            'start': event.start.isoformat(),
            'end': event.end.isoformat() if event.end else None,
            'resourceId': event.resource_id,
            'allDay': event.all_day
        })

    # Return the events as a JSON response
    return jsonify(events_data)


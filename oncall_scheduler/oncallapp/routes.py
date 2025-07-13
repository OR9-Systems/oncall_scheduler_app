from flask import render_template, redirect, url_for, flash, request, jsonify, session
from oncallapp import app, db
from oncallapp.forms import CreateUserGroupForm, CreateScheduleForm, CreateUserForm, CreateScheduleTemplateForm, ModifyUserForm, ImportScheduleForm
from oncallapp.models import UserGroup, Schedule, User, ScheduleTemplate, TemplateEvent
from oncallapp.srs_api import get_srs
#from oncallapp.parse_ical import parse_ical
from oncallapp.utils import extra_data_to_csv
from oncallapp.csv_dom_save import create_schedule_template_from_csv

import uuid
#import datetime
from datetime import time, datetime
from dateutil import parser
from icalendar import Calendar
from collections import Counter

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
    if request.form.get('redirect') is not None:
        return jsonify({'status': 'success', 'message': 'User created successfully!'}), 200
    else:
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


@app.route('/import_schedule', methods=['GET', 'POST'])
def import_schedule():
    form = ImportScheduleForm()
    category_to_tags = {}
    matched_tags = {}
    extra_data = {}
    event_types = set()
    extra_data_csv = ""
    csv_data = ""
    if request.method == 'POST':
        if request.form.get('submit') == 'manual_import':
            # Handle manual import
            csv_data = form.extra_data_text.data.strip()
            if not csv_data:
                flash("Please provide extra data in CSV format.", "error")
                return redirect(url_for('import_schedule'))
            #remove the first line  of the csv that starts with #
            if csv_data.startswith('#'):
                csv_data = '\n'.join(csv_data.split('\n')[1:])
            
            category = form.calendars.data
            try:
                # Process the manual CSV input call create_schedule_template_from_csv(
               template = create_schedule_template_from_csv(
                   db.session,
                   csv_data,
                   category
                   )
               flash(f"Template '{template.name}' imported successfully!", "success")
               return redirect(url_for('view_templates'))
                # Flash success message

            except Exception as e:
                flash(f"Error processing manual input: {str(e)}", "error")
                return redirect(url_for('import_schedule'))



        if form.file.data:
            uploaded_file = form.file.data

            try:
                # Read the uploaded file directly without saving it
                result = form.process_ics_file(uploaded_file, extra_data_to_csv)
                matched_tags = result["matched_tags"]
                extra_data = result["extra_data"]
                extra_data_csv = result["extra_data_csv"]
                # Flash success message
                flash(f"File processed successfully! Event types and tags loaded.", "success")

            except Exception as e:
                flash(f"Error processing file: {str(e)}", "error")
                return redirect(url_for('import_schedule'))

        else:
            # Handle form validation errors
            for field, errors in form.errors.items():
                flash(f"Field: {field}, Errors: {errors}", "error")

    # Render the import schedule page with updated form
    return render_template('import_schedule.html', form=form, matched_tags=matched_tags,extra_data=extra_data, extra_data_csv=extra_data_csv)

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

@app.route('/modify_user', methods=['GET', 'POST'])
def modify_user():
    # Determine the group_id: if None, default to the first group
    group_id = request.form.get('group', type=int) if request.method == 'POST' else request.args.get('group', type=int)
    if not group_id:
        print("NO GROUP ID", flush=True)
        first_group = UserGroup.query.first()
        group_id = first_group.id if first_group else None

    form = ModifyUserForm(group_id=group_id)
    users = []
    error_message = None

    # Fetch users from get_srs_data endpoint
    try:
        response = get_srs_data().get_json()
        if response.get('status') == 'success':
            data = eval(response.get('message', '{}'))
            plans = data.get('plans', [])
            for plan in plans:
                plan_users = plan.get('available_users', [])
                for user in plan_users:
                    if user not in users:
                        users.append(user)
        else:
            error_message = response.get('message', 'Failed to fetch users.')
    except Exception as e:
        error_message = f"Failed to fetch users: {str(e)}"

    # Handle button actions (add/remove) directly
    if request.method == 'POST' and 'action' in request.form:
        action = request.form.get('action')
        user_name = request.form.get('user')

        if action == 'add':
            # Check if the user already exists in the group
            existing_user = User.query.filter_by(name=user_name, group_id=group_id).first()
            if not existing_user:
                new_user = User(name=user_name, group_id=group_id)
                db.session.add(new_user)
                db.session.commit()
                flash(f"User {user_name} added successfully!")
            else:
                flash(f"User {user_name} already exists in the group!", 'error')

        elif action == 'remove':
            # Query by name and group ID
            user = User.query.filter_by(name=user_name, group_id=group_id).first()
            if user:
                db.session.delete(user)
                db.session.commit()
                flash(f"User {user.name} removed successfully!")
            else:
                flash(f"User {user_name} not found in group {group_id}!", 'error')

        return redirect(url_for('modify_user', group=group_id))

    # Render the template with the form and users
    return render_template('modify_user.html', form=form, users=users, error_message=error_message)

@app.route('/create_template', methods=['GET', 'POST'])
def create_template():
    form = CreateScheduleTemplateForm()

    template_id = request.args.get('template_id',None)
    if template_id and template_id =='new_session':
        session.clear()
        template_id=str(uuid.uuid4())
        session['template_id'] = template_id
        return redirect(url_for('create_template',template_id=template_id))


    # Check if template_id exists in session; if not, create a new unique ID
    if 'template_id' not in session and not template_id :
        # Generate a new UUID or use the Flask session ID
        session['template_id'] = str(uuid.uuid4())  # Using UUID for uniqueness
    print(f"Session ID:{session['template_id']}", flush=True)

    # Use the session 'template_id'
    template_id = template_id or session['template_id']
    template = ScheduleTemplate.query.filter_by(id=template_id).first()
    #Auto Calculate the event start and end dates based on the events within the window 
    print(f"sdate:{str(session)}", flush=True)
    print(request.form.to_dict(flat=False), flush=True)



    if request.method == 'POST':
        test_mode = request.form.get('test_mode', 'false') == 'true'  # Capture test mode flag
        group_id = request.form.get('group', type=int)

        #Given the condition that we post the 
        if not form.start_date.data or not form.end_date.data:
                events = TemplateEvent.query.filter_by(template_id=template_id).all()
                if events:
                    start_dates = [event.start for event in events if event.start]
                    end_dates = [event.end for event in events if event.end]
                    if start_dates and end_dates:
                        min_start = min(start_dates)
                        max_end  = max(end_dates)
                        #min_start = datetime.combine(min_start.date(), min_start.time() or time(0, 0))
                        #max_end = datetime.combine(max_end.date(), max_end.time() or time(23, 59))

                        form.start_date.data =min_start
                        form.end_date.data = max_end  #datetime.strptime(max_end.strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M')
                    else:
                        flash('Cannot auto-calculate dates: Some events are missing start or end times.', 'error')
                        return redirect(url_for('create_template'))
                else:
                    flash('Cannot auto-calculate dates: No events found.', 'error')
                    return redirect(url_for('create_template'))

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
        #events_from_frontend = request.json.get('events', [])
        #sync_template_events(template.id, events_from_frontend)

        flash('Schedule template created and events synced successfully!')
        return redirect(url_for('view_templates'))

    return render_template('create_template.html', form=form, template=template)

@app.route('/sync_events', methods=['POST'])
def sync_events():
    data = request.get_json()
    template_id = data.get('template_id')
    events = data.get('events', [])
    
    if not template_id:
        return jsonify({'status': 'error', 'message': 'Template ID is required.'}), 400
    
    try:
        sync_template_events(template_id, events)
        return jsonify({'status': 'success', 'message': 'Events synchronized successfully.'})
    except Exception as e:
        print(f"Error during sync: {e}", flush=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500



def sync_template_events(template_id, received_events):
    # Fetch all existing events for this template
    existing_events = TemplateEvent.query.filter_by(template_id=template_id).all()
    
    # Convert existing events to a dict with id as key for fast lookup
    existing_event_dict = {event.id: event for event in existing_events}

    # Track ids of events to keep
    received_event_ids = set()

    # Process received events
    for event_data in received_events:
        event_id = event_data.get('id')
        received_event_ids.add(event_id)

        # Get start and end time strings from the event data
        start_time_str = event_data['start']
        end_time_str = event_data['end']

        # Convert the date strings to datetime objects
        try:
            # Parse ISO 8601 strings using dateutil.parser.parse
            start_time = parser.parse(start_time_str)
            end_time = parser.parse(end_time_str)
        except ValueError as e:
            print(f"Date parsing error: {e}", flush=True)
            return jsonify({'status': 'error', 'message': 'Invalid date format.'}), 400

        if event_id in existing_event_dict:
            # Update existing event
            event = existing_event_dict[event_id]
            event.title = event_data['title']
            event.start = start_time
            event.end = end_time
            event.resource_id = event_data['resourceId']
            event.all_day = event_data.get('allDay', False)
        else:
            # Create new event
            new_event = TemplateEvent(
                id=event_data.get('id'),  # Usually auto-generated, but might be passed
                title=event_data['title'],
                start=start_time,
                end=end_time,
                resource_id=event_data['resourceId'],
                all_day=event_data.get('allDay', False),
                template_id=template_id,
            )
            db.session.add(new_event)

    # Delete events that are not in received_event_ids
    for event in existing_events:
        if event.id not in received_event_ids:
            db.session.delete(event)

    db.session.commit()
    # Reload Existing Events after Commiting Changes
    #existing_events = TemplateEvent.query.filter_by(template_id=template_id).all()
    # Query For Existing Template
    # Commit changes
    #db.session.commit()
    return {"status": "success"}

@app.route('/view_templates')
def view_templates():
    templates = ScheduleTemplate.query.all()
    return render_template('view_templates.html', templates=templates)

@app.route('/save_event', methods=['POST'])
def save_event():
    event_data = request.get_json()
    print(f"Received Event Data: {event_data}", flush=True)

    # Extract data from the incoming event JSON
    event_id = event_data.get('id', None)  # Could be {generated-1}, or None for new events
    start_time_str = event_data.get('start', None)
    end_time_str = event_data.get('end', None)
    resource_id = event_data.get('resourceId', None)
    template_id = event_data.get('template_id', None)
    all_day = event_data.get('all_day', False)
    
    if not template_id:
        return jsonify({'status': 'error', 'message': 'Template ID is required.'}), 400

    if not start_time_str or not end_time_str:
        return jsonify({'status': 'error', 'message': 'Start and end time are required.'}), 400

    # Parse the start and end times
    try:
        start_time = parser.parse(start_time_str)
        end_time = parser.parse(end_time_str)
    except ValueError as e:
        print(f"Date parsing error: {e}", flush=True)
        return jsonify({'status': 'error', 'message': 'Invalid date format.'}), 400

    # Handle the case where event_id is numeric
    if isinstance(event_id, str) and event_id.isnumeric():
        event_id = int(event_id)

    # Update an existing event if the event ID is valid (numeric)
    if event_id and isinstance(event_id, int):
        event = TemplateEvent.query.get(event_id)
        if event:
            print(f"Updating Event: {event_id}", flush=True)
            event.title = event_data.get('title', event.title)
            event.start = start_time
            event.end = end_time
            event.resource_id = resource_id
            event.group_id = event_data.get('group_id', event.group_id)
            event.all_day = all_day
            db.session.commit()
            print(f"Event {event_id} updated successfully.", flush=True)
            return jsonify({'status': 'success', 'message': 'Event updated successfully.', 'event_id': event.id})

    # Create a new event if no valid numeric ID is provided (new event creation)
    print(f"Creating new event", flush=True)
    new_event = TemplateEvent(
        title=event_data.get('title', 'Untitled Event'),
        start=start_time,
        end=end_time,
        resource_id=resource_id,
        template_id=template_id,
        user_id=None,  # Adjust based on your user logic
        group_id=event_data.get('group_id', None),
        all_day=all_day
    )
    db.session.add(new_event)
    db.session.commit()
    print(f"New event created with ID: {new_event.id}", flush=True)
    #For each event saved update the initial template dates data so when we save the template we have dates 
    return jsonify({'status': 'success', 'message': 'Event created successfully.', 'event_id': new_event.id})

@app.route('/load_events/<template_id>', methods=['GET'])
def load_events(template_id):
    # Fetch events for the given template_id
    events = TemplateEvent.query.filter_by(template_id=template_id).all()
    # Fetch all users and groups
    users = {user.name for user in User.query.all()}
    groups = {group.name for group in UserGroup.query.all()}
    events_data = []
    # When reading events if the name is a substring of a user or group name set the event title to the full name


    # When Reading Events Autofill based on the color recognised

    for event in events:
        # When reading events if the name is a substring of a user or group name set the event title to the full name
        sanitized_title = event.title.replace('\r', '').lower()
        if len(sanitized_title) >= 0:
            # Check if the sanitized title is a substring of any user's name
            matched_user = next((user for user in users if sanitized_title in user.lower()), None)
            color = None
            if matched_user:
                event.title = matched_user  # Update the event title to the full user's name
                color = 'green'  # Matches a user's name
            else:
                # Check if the sanitized title is a substring of any group's name
                matched_group = next((group for group in groups if sanitized_title in group.lower()), None)
                if matched_group:
                    event.title = matched_group  # Update the event title to the full group's name
                    color = 'purple'  # Matches a group's name
                else:
                    color = 'blue'  # Default color for no match
        else:
            pass


        events_data.append({
                'id': event.id,
                'title': event.title,
                'start': event.start.isoformat(),
                'end': event.end.isoformat() if event.end else None,
                'resourceId': event.resource_id,
                'all_day': event.all_day,
                'color': color
            })

    # Return the events as a JSON response
    return jsonify(events_data)



# Possibly more complex conditons later so separate. 
@app.route('/activate_template/<template_id>', methods=['POST'])
def activate_template(template_id):
    template = ScheduleTemplate.query.get(template_id)
    if not template:
        return jsonify({'status': 'error', 'message': 'Template not found.'}), 404

    template.test_mode = True
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Template activated.'})


# Possibly more complex conditons later so separate. 
@app.route('/deactivate_template/<template_id>', methods=['POST'])
def deactivate_template(template_id):
    template = ScheduleTemplate.query.get(template_id)
    if not template:
        return jsonify({'status': 'error', 'message': 'Template not found.'}), 404

    template.test_mode = False
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Template deactivated.'})



@app.route('/delete_template/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    template = ScheduleTemplate.query.get(template_id)
    if not template:
        return jsonify({'status': 'error', 'message': 'Template not found.'}), 404

    # Delete associated events
    TemplateEvent.query.filter_by(template_id=template_id).delete()
    db.session.delete(template)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Template and related events deleted.'})








@app.route('/get_srs_data',methods=['GET'])
def get_srs_data():
     try:
        return jsonify({'status': 'success', 'message': f'{get_srs()}'})
     except Exception as e:
         return jsonify({'status': 'error', 'message': f'Issue getting Data from service. Error: {str(e)}'}), 400



@app.route('/delete_event', methods=['DELETE'])
def delete_event():
    event_data = request.get_json()
    event_id = event_data.get('id')
    template_id = event_data.get('template_id')

    if not event_id or not template_id:
        return jsonify({'status': 'error', 'message': 'Event ID and Template ID are required.'}), 400

    # Find the event by its ID and template ID
    event = TemplateEvent.query.filter_by(id=event_id, template_id=template_id).first()

    if not event:
        return jsonify({'status': 'error', 'message': 'Event not found.'}), 404

    # Delete the event
    db.session.delete(event)
    db.session.commit()

    print(f"Deleted event {event_id} from template {template_id}", flush=True)

    return jsonify({'status': 'success', 'message': 'Event deleted successfully.'})

from flask import render_template, redirect, url_for, flash, request, jsonify
from oncallapp import app, db
from oncallapp.forms import CreateUserGroupForm, CreateScheduleForm, CreateUserForm, CreateScheduleTemplateForm
from oncallapp.models import UserGroup, Schedule, User, ScheduleTemplate, TemplateEvent

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
    
    if request.method == 'POST':
        group_id = request.form.get('group', type=int)
    else:
        group_id = request.args.get('group', type=int) or (UserGroup.query.first().id if UserGroup.query.first() else None)


    if form.validate_on_submit():
        template = ScheduleTemplate(
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            repeat_weekly=form.repeat_weekly.data
        )
        db.session.add(template)
        db.session.commit()
        
        # Add the events to the TemplateEvent model
        events = request.json.get('events', [])
        for event in events:
            template_event = TemplateEvent(
                title=event['title'],
                start=event['start'],
                end=event['end'],
                all_day=event.get('all_day', False),
                template_id=template.id,
                user_id=None,
                group_id=event.get('group_id')
            )
            db.session.add(template_event)
        
        db.session.commit()
        flash('Schedule template created successfully!')
        return redirect(url_for('view_templates'))
    
    return render_template('create_template.html', form=form)


@app.route('/view_templates')
def view_templates():
    templates = ScheduleTemplate.query.all()
    return render_template('view_templates.html', templates=templates)





@app.route('/save_event', methods=['POST'])
def save_event():
    event_data = request.get_json()
    print(f"Received Event Data: {event_data}", flush=True)  # Debugging line
    event_id = event_data.get('id',None)
    start_time = event_data.get('start',None)
    end_time = event_data.get('end',None)
    resource_id = event_data.get('resourceId',None)


     # Check if start_time and end_time are in correct format (datetime, etc.)
    if not start_time or not end_time:
        return jsonify({'status': 'error', 'message': 'Invalid time data provided.'}), 400

    # If the event already exists, update it; otherwise, create a new one
    if event_id:
        all_items = Schedule.query.all()
        print(f"Received Items: {all_items}", flush=True)  # The event exists

        event = Schedule.query.get(event_id)
        if event:
            event.start_time = start_time
            event.end_time = end_time
            event.resource_id = resource_id
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Event updated successfully.'})
        else:
            return jsonify({'status': 'error', 'message': 'Event not found.'}), 404
    else:
        event = Schedule(
            start_time=start_time,
            end_time=end_time,
            resource_id=resource_id
        )
        db.session.add(event)
    db.session.commit()
    return jsonify({'status': 'success'})
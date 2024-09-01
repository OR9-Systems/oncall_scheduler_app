from flask import render_template, redirect, url_for, flash, request
from oncallapp import app, db
from oncallapp.forms import CreateUserGroupForm, CreateScheduleForm, CreateUserForm
from oncallapp.models import UserGroup, Schedule, User

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





@app.route('/view_schedule')
def view_schedule():
    schedules = Schedule.query.all()
    return render_template('view_schedule.html', schedules=schedules)
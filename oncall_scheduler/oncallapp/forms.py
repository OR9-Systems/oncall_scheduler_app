from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField
from wtforms.validators import DataRequired
from oncallapp.models import UserGroup, User

class CreateUserGroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired()])
    submit = SubmitField('Create Group')

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



class CreateUserForm(FlaskForm):
    name = StringField('User Name', validators=[DataRequired()])
    group = SelectField('User Group', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Create User')

    def __init__(self, *args, **kwargs):
        super(CreateUserForm, self).__init__(*args, **kwargs)
        self.group.choices = [(group.id, group.name) for group in UserGroup.query.all()]
        print(f"Group Choices: {self.group.choices}", flush=True)  # Debugging line
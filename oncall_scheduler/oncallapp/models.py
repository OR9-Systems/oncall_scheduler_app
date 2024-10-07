from oncallapp import db

class UserGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    users = db.relationship('User', backref='group', lazy=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'), nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time_segment = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='schedules')  # Add this line


class ScheduleTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True,autoincrement=True)
    name = db.Column(db.String(64), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    repeat_weekly = db.Column(db.Boolean, default=True)
    test_mode = db.Column(db.Boolean, default=False) 

    template_items = db.relationship('ScheduleTemplateItem', backref='template', lazy=True)


class ScheduleTemplateItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('schedule_template.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    group = db.relationship('UserGroup', backref='template_items')


class TemplateEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    all_day = db.Column(db.Boolean, default=False)
    template_id = db.Column(db.Integer, db.ForeignKey('schedule_template.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)  # Add this line

    def __repr__(self):
        return f'<TemplateEvent {self.title}>'
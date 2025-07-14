# oncallbackend.py

from crontab import CronTab
from datetime import datetime, timedelta
from oncallapp import app, db
from  oncallapp.models import  TemplateEvent, ScheduleTemplate, User, UserGroup
from sqlalchemy import or_
from oncallapp.srs_api import SRSService
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OnCallScheduler:
    def __init__(self):
        self.cron = CronTab(user=True)
        self.session = db.session  # Assumes Flask app context
        self.users = [user.name.lower() for user in User.query.all()]
        self.groups = [group.name.lower() for group in UserGroup.query.all()]

    def clear_existing_jobs(self):
        logger.info("🔁 Clearing existing scheduled on-call jobs...")
        jobs_removed = 0
        for job in self.cron:
            if "oncall_scheduled_event" in job.comment:
                self.cron.remove(job)
                jobs_removed += 1
        self.cron.write()
        logger.info(f"✅ Removed {jobs_removed} old jobs")

    def sanitize_and_classify_title(self, event):
        title = event.title.replace('\r', '').strip().lower()
        if not title:
            return event.title, 'blue'  # No match

        match_user = next((u for u in self.users if title in u), None)
        if match_user:
            return match_user, 'green' # User match

        match_group = next((g for g in self.groups if title in g), None)
        if match_group:
            return match_group, 'purple' # Group match

        return event.title, 'blue'
    

    def get_normalized_events(self, templates):
        normalized = []
        for template in templates:
            events = TemplateEvent.query.filter_by(template_id=template.id).all()
            for event in events:
                if event.start.year < datetime.now().year:
                    continue
                if event.all_day:
                    event_start = datetime.combine(event.start.date(), datetime.min.time())
                    event_end = datetime.combine(event.end.date(), datetime.min.time()) + timedelta(days=1)
                else:
                    event_start = event.start
                    event_end = event.end

                title, color = self.sanitize_and_classify_title(event)
                normalized.append({
                    'start': event_start,
                    'end': event_end,
                    'duration': (event_end - event_start).total_seconds(),
                    'color': color,
                    'title': title,
                    'template': template,
                })
        return sorted(normalized, key=lambda e: e['start'])
    

    def schedule_segments(self, segments):
        for segment in segments:
            start = segment['start']
            event = segment['event']
            title = event['title']
            color = event['color']
            template = event['template']

            logger.info(f"⏰ Segment from {start} to {segment['end']} for {title} (duration: {event['duration']})")

            if color == 'green':
                self.schedule_user_cron(title, start)
            elif color == 'purple':
                self.schedule_group_cron(title, start, template.start_date)
            else:
                logger.warning(f"⚠️ Unrecognized event color '{color}'")

    def build_schedule_intervals(self, events):
        timeline = []
        for event in events:
            timeline.append(('start', event['start'], event))
            timeline.append(('end', event['end'], event))

        # Sort timeline: ends before starts on same timestamp
        timeline.sort(key=lambda x: (x[1], 0 if x[0] == 'end' else 1))

        active_events = []
        segments = []

        for i in range(len(timeline) - 1):
            _, current_time, event = timeline[i]
            _, next_time, _ = timeline[i + 1]

            if timeline[i][0] == 'start':
                active_events.append(event)
            else:
                if event in active_events:
                    active_events.remove(event)

            if active_events:
                # Choose the shortest-duration active event
                best_event = sorted(active_events, key=lambda e: e['duration'])[0]
                segments.append({
                    'start': current_time,
                    'end': next_time,
                    'event': best_event
                })

        return segments



    def run_scheduler(self):
        logger.info("🚀 Starting test-mode template scheduling...")
        self.clear_existing_jobs()

        templates = ScheduleTemplate.query.filter_by(test_mode=True).all()

        if not templates:
            logger.info("⚠️ No templates found with test_mode=True")
            return

        logger.info("📋 Test-mode templates to be scheduled:")
        for t in templates:
            logger.info(f"    • {t.name} (ID: {t.id})")

        # 🔄 Normalize all TemplateEvents to concrete segments
        events = self.get_normalized_events(templates)

        # 📏 Build handoff intervals, shortest events win overlaps
        segments = self.build_schedule_intervals(events)

        # ⏰ Schedule cron jobs at segment start times
        self.schedule_segments(segments)

        # 💾 Commit all to crontab
        self.cron.write()
        logger.info("✅ All cron jobs written successfully.")


    def schedule_user_cron(self, username, time_dt):
        command = (
            f'/usr/local/bin/python3 /oncall_scheduler/oncall_scheduler/oncallapp/srs_api.py'
            f' --user="{username}"'
        )

        job = self.cron.new(command=command, comment='oncall_scheduled_event')
        job.setall(time_dt)
        logger.info(f"🟢 Cron job created for user {username} at {time_dt}")

    def schedule_group_cron(self, group_name, time_dt,template_start_date):
        group = UserGroup.query.filter(UserGroup.name.ilike(f"%{group_name}%")).first()
        if not group or not group.users:
            logger.warning(f"⚠️ Group '{group_name}' not found or empty.")
            return

        sorted_users = sorted(group.users, key=lambda u: u.id)
        week_index = (time_dt.date() - template_start_date).days // 7
        selected_user = sorted_users[week_index % len(sorted_users)]

        logger.info(f"🟣 Selected {selected_user.name} from group {group.name}")
        self.schedule_user_cron(selected_user.name, time_dt)


if __name__ == "__main__":
      with app.app_context():
        scheduler = OnCallScheduler()
        scheduler.run_scheduler()



from odoo import models, fields, api, _
from datetime import datetime, timedelta


class CourseSession(models.Model):
    _name = 'hallway.course.session'
    _description = 'Course Session'
    _order = 'date, start_time'

    name = fields.Char(string='Session Name', required=True)
    course_id = fields.Many2one('hallway.course', string='Course', required=True, ondelete='cascade')

    # Date and Time
    date = fields.Date(string='Date', required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)

    # Datetime fields for calendar view
    datetime_start = fields.Datetime(string='Start', compute='_compute_datetime', store=True)
    datetime_end = fields.Datetime(string='End', compute='_compute_datetime', store=True)

    # Instructor
    instructor_id = fields.Many2one('res.partner', string='Instructor')
    substitute_instructor_id = fields.Many2one('res.partner', string='Substitute Instructor')

    # Location
    classroom = fields.Char(string='Classroom')
    online_link = fields.Char(string='Online Link')

    # Status
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='scheduled')

    # Attendance
    attendance_ids = fields.One2many('hallway.attendance', 'session_id', string='Attendance')
    present_count = fields.Integer(string='Present', compute='_compute_attendance_stats')
    absent_count = fields.Integer(string='Absent', compute='_compute_attendance_stats')
    attendance_rate = fields.Float(string='Attendance Rate (%)', compute='_compute_attendance_stats')

    # Notes
    notes = fields.Text(string='Session Notes')
    homework = fields.Text(string='Homework')

    # Company
    company_id = fields.Many2one(
        related='course_id.company_id', string="Company", store=True
    )

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.end_time > record.start_time:
                record.duration = record.end_time - record.start_time
            else:
                record.duration = 0

    @api.depends('date', 'start_time', 'end_time')
    def _compute_datetime(self):
        for record in self:
            if record.date:
                # Convert float time to hours and minutes
                start_hours = int(record.start_time)
                start_minutes = int((record.start_time - start_hours) * 60)
                end_hours = int(record.end_time)
                end_minutes = int((record.end_time - end_hours) * 60)

                # Create datetime objects
                start_dt = datetime.combine(record.date, datetime.min.time())
                start_dt = start_dt.replace(hour=start_hours, minute=start_minutes)

                end_dt = datetime.combine(record.date, datetime.min.time())
                end_dt = end_dt.replace(hour=end_hours, minute=end_minutes)

                record.datetime_start = start_dt
                record.datetime_end = end_dt
            else:
                record.datetime_start = False
                record.datetime_end = False

    @api.depends('attendance_ids', 'attendance_ids.status')
    def _compute_attendance_stats(self):
        for record in self:
            present = record.attendance_ids.filtered(lambda a: a.status == 'present')
            absent = record.attendance_ids.filtered(lambda a: a.status == 'absent')

            record.present_count = len(present)
            record.absent_count = len(absent)

            total = len(record.attendance_ids)
            if total > 0:
                record.attendance_rate = (record.present_count / total) * 100
            else:
                record.attendance_rate = 0

    def action_take_attendance(self):
        """Open attendance wizard or generate attendance records"""
        self.ensure_one()

        # Generate attendance records for all enrolled students if not exists
        enrolled_students = self.course_id.enrollment_ids.filtered(
            lambda e: e.state == 'enrolled'
        ).mapped('student_id')

        for student in enrolled_students:
            existing = self.attendance_ids.filtered(lambda a: a.student_id == student)
            if not existing:
                self.env['hallway.attendance'].create({
                    'session_id': self.id,
                    'student_id': student.id,
                    'enrollment_id': self.course_id.enrollment_ids.filtered(
                        lambda e: e.student_id == student and e.state == 'enrolled'
                    )[0].id,
                    'status': 'absent',  # Default to absent
                })

        # Open attendance form
        return {
            'type': 'ir.actions.act_window',
            'name': 'Take Attendance',
            'res_model': 'hallway.attendance',
            'view_mode': 'list',
            'domain': [('session_id', '=', self.id)],
            'context': {
                'default_session_id': self.id,
                'create': False,
                'delete': False,
            }
        }

    def action_complete_session(self):
        """Mark session as completed"""
        self.ensure_one()
        self.state = 'completed'

    def action_cancel_session(self):
        """Cancel the session"""
        self.ensure_one()
        self.state = 'cancelled'
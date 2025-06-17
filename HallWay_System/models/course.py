from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class Course(models.Model):
    _name = 'hallway.course'
    _description = 'Course'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, name'

    name = fields.Char(string='Course Name',  compute='_compute_name', store=True)
    code = fields.Char(string='Course Code', required=True, copy=False, readonly=True, default='New')
    active = fields.Boolean(string='Active', default=True)

    # Subject and Level
    department_id = fields.Many2one('hallway.department', string='Department', required=True)
    subject_id = fields.Many2one('hallway.subject', string='Subject', required=True,
                                 domain="[('department_id', '=', department_id)]")
    level_id = fields.Many2one('hallway.subject.level', string='Level', required=True,
                               domain="[('subject_id', '=', subject_id)]")

    # Schedule
    schedule = fields.Selection([
        ('morning', 'Morning / صباحي'),
        ('afternoon', 'Afternoon / مسائي'),
        ('evening', 'Evening / ليلي'),
        ('weekend', 'Weekend / نهاية الأسبوع')
    ], string='Schedule', required=True)

    schedule_day_ids = fields.Many2many('week.days', string='Class Days', required=True)

    # Dates
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True)
    registration_deadline = fields.Date(string='Registration Deadline')

    # Time
    start_time = fields.Float(string='Start Time', required=True, help='Start time in 24hr format')
    end_time = fields.Float(string='End Time', required=True, help='End time in 24hr format')
    duration_per_session = fields.Float(string='Duration per Session (Hours)', compute='_compute_duration', store=True)

    # Instructor
    instructor_id = fields.Many2one('res.partner', string='Instructor',
                                    domain="[('is_company', '=', False)]")

    # Location
    classroom = fields.Char(string='Classroom')
    location = fields.Selection([
        ('onsite', 'On-site / في الموقع'),
        ('online', 'Online / عبر الإنترنت'),
        ('hybrid', 'Hybrid / مختلط')
    ], string='Location Type', default='onsite', required=True)
    online_link = fields.Char(string='Online Meeting Link')

    # Capacity
    max_students = fields.Integer(string='Maximum Students', default=20, required=True)
    enrolled_students = fields.Integer(string='Enrolled Students', compute='_compute_enrolled_students')
    available_seats = fields.Integer(string='Available Seats', compute='_compute_available_seats')

    # Pricing
    department_price = fields.Float(related='department_id.price', string='Department Price', readonly=True)
    price = fields.Float(string='Course Price', required=True,
                         help='You can override the department price for this specific course')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open for Registration'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    # Enrollments
    enrollment_ids = fields.One2many('hallway.enrollment', 'course_id', string='Enrollments')

    # Sessions
    session_ids = fields.One2many('hallway.course.session', 'course_id', string='Sessions')
    total_sessions = fields.Integer(string='Total Sessions', compute='_compute_total_sessions')

    # Company
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    @api.depends('subject_id', 'level_id', 'schedule', 'start_date')
    def _compute_name(self):
        for record in self:
            if record.subject_id and record.level_id and record.start_date:
                month_year = record.start_date.strftime('%b %Y')
                schedule_abbr = dict(self._fields['schedule'].selection).get(record.schedule, '')
                record.name = f"{record.subject_id.name} - {record.level_id.name} ({schedule_abbr}) - {month_year}"
            else:
                record.name = "New Course"

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.end_time > record.start_time:
                record.duration_per_session = record.end_time - record.start_time
            else:
                record.duration_per_session = 0

    @api.depends('enrollment_ids', 'enrollment_ids.state')
    def _compute_enrolled_students(self):
        for record in self:
            record.enrolled_students = len(record.enrollment_ids.filtered(lambda e: e.state == 'enrolled'))

    @api.depends('max_students', 'enrolled_students')
    def _compute_available_seats(self):
        for record in self:
            record.available_seats = record.max_students - record.enrolled_students

    @api.depends('session_ids')
    def _compute_total_sessions(self):
        for record in self:
            record.total_sessions = len(record.session_ids)

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Set default price from department"""
        if self.department_id:
            self.price = self.department_id.price
            # Clear subject and level when department changes
            self.subject_id = False
            self.level_id = False

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('hallway.course') or 'New'
        course = super(Course, self).create(vals)
        # Auto-generate sessions
        course.generate_sessions()
        return course

    def generate_sessions(self):
        """Generate course sessions based on schedule"""
        self.ensure_one()
        if not self.start_date or not self.end_date:
            return

        # Delete existing sessions
        self.session_ids.unlink()

        # Generate new sessions
        current_date = self.start_date
        session_number = 1

        while current_date <= self.end_date:
            # Check if current day is in schedule days
            weekday = current_date.weekday()  # 0 = Monday, 6 = Sunday

            # Map weekday to week.days (you might need to adjust based on your week.days setup)
            weekday_mapping = {
                0: 'Monday',
                1: 'Tuesday',
                2: 'Wednesday',
                3: 'Thursday',
                4: 'Friday',
                5: 'Saturday',
                6: 'Sunday'
            }

            day_name = weekday_mapping.get(weekday)
            if any(day.name == day_name for day in self.schedule_day_ids):
                session_vals = {
                    'course_id': self.id,
                    'name': f"Session {session_number}",
                    'date': current_date,
                    'start_time': self.start_time,
                    'end_time': self.end_time,
                    'instructor_id': self.instructor_id.id if self.instructor_id else False,
                    'classroom': self.classroom,
                }
                self.env['hallway.course.session'].create(session_vals)
                session_number += 1

            current_date += timedelta(days=1)

    def action_open_registration(self):
        """Open course for registration"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft courses can be opened for registration.'))
        self.state = 'open'

    def action_start_course(self):
        """Start the course"""
        self.ensure_one()
        if self.state != 'open':
            raise UserError(_('Only open courses can be started.'))
        self.state = 'in_progress'

    def action_complete_course(self):
        """Complete the course"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Only in-progress courses can be completed.'))
        self.state = 'completed'

    def action_cancel_course(self):
        """Cancel the course"""
        self.ensure_one()
        if self.state in ['completed', 'cancelled']:
            raise UserError(_('Cannot cancel a completed or already cancelled course.'))
        self.state = 'cancelled'

    def action_view_enrollments(self):
        """View course enrollments"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Enrollments',
            'res_model': 'hallway.enrollment',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id}
        }

    def action_view_sessions(self):
        """View course sessions"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sessions',
            'res_model': 'hallway.course.session',
            'view_mode': 'list,calendar,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id}
        }
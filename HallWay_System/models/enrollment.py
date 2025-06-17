from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class Enrollment(models.Model):
    _name = 'hallway.enrollment'
    _description = 'Course Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'enrollment_date desc'
    _rec_name = 'enrollment_number'

    enrollment_number = fields.Char(string='Enrollment Number', required=True, copy=False, readonly=True, default='New')
    enrollment_date = fields.Date(string='Enrollment Date', required=True, default=fields.Date.today, tracking=True)

    # Student and Course
    student_id = fields.Many2one('hallway.student', string='Student', required=True, ondelete='restrict')
    course_id = fields.Many2one('hallway.course', string='Course', required=True, ondelete='restrict',
                                domain="[('state', '=', 'open')]")

    # Related fields
    department_id = fields.Many2one(related='course_id.department_id', string='Department', store=True)
    subject_id = fields.Many2one(related='course_id.subject_id', string='Subject', store=True)
    level_id = fields.Many2one(related='course_id.level_id', string='Level', store=True)

    # Application
    application_id = fields.Many2one('student.application', string='Application')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    # Financial
    course_price = fields.Float(related='course_id.price', string='Course Price', store=True)
    discount_percent = fields.Float(string='Discount (%)', default=0.0)
    discount_amount = fields.Float(string='Discount Amount', compute='_compute_amounts', store=True)
    final_price = fields.Float(string='Final Price', compute='_compute_amounts', store=True)

    payment_state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid')
    ], string='Payment Status', default='unpaid', tracking=True)

    # Attendance
    attendance_ids = fields.One2many('hallway.attendance', 'enrollment_id', string='Attendance')
    attendance_rate = fields.Float(string='Attendance Rate (%)', compute='_compute_attendance_rate')

    # Performance
    grade = fields.Selection([
        ('A+', 'A+ (95-100%)'),
        ('A', 'A (90-94%)'),
        ('B+', 'B+ (85-89%)'),
        ('B', 'B (80-84%)'),
        ('C+', 'C+ (75-79%)'),
        ('C', 'C (70-74%)'),
        ('D', 'D (60-69%)'),
        ('F', 'F (Below 60%)')
    ], string='Final Grade')

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    # Certificate
    certificate_issued = fields.Boolean(string='Certificate Issued', default=False)
    certificate_date = fields.Date(string='Certificate Date')
    certificate_number = fields.Char(string='Certificate Number')

    # Notes
    notes = fields.Text(string='Notes')
    drop_reason = fields.Text(string='Drop Reason')

    # Company
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('unique_student_course', 'UNIQUE(student_id, course_id)',
         'A student can only be enrolled once in the same course!'),
    ]

    @api.depends('course_price', 'discount_percent')
    def _compute_amounts(self):
        for record in self:
            record.discount_amount = (record.course_price * record.discount_percent) / 100
            record.final_price = record.course_price - record.discount_amount

    @api.depends('attendance_ids', 'attendance_ids.status')
    def _compute_attendance_rate(self):
        for record in self:
            total_sessions = len(record.attendance_ids)
            if total_sessions > 0:
                present_sessions = len(record.attendance_ids.filtered(lambda a: a.status == 'present'))
                record.attendance_rate = (present_sessions / total_sessions) * 100
            else:
                record.attendance_rate = 0

    @api.model
    def create(self, vals):
        if vals.get('enrollment_number', 'New') == 'New':
            vals['enrollment_number'] = self.env['ir.sequence'].next_by_code('hallway.enrollment') or 'New'

        # Check course capacity
        if 'course_id' in vals:
            course = self.env['hallway.course'].browse(vals['course_id'])
            if course.available_seats <= 0:
                raise UserError(_('This course is full. No seats available.'))

        return super(Enrollment, self).create(vals)

    def action_enroll(self):
        """Confirm enrollment"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft enrollments can be confirmed.'))

            # Check course capacity again
            if record.course_id.available_seats <= 0:
                raise UserError(_('This course is full. No seats available.'))

            record.state = 'enrolled'

            # Send notification
            record.message_post(
                body=f"Student {record.student_id.full_name} enrolled in {record.course_id.name}",
                subtype_xmlid="mail.mt_comment"
            )

    def action_start(self):
        """Start the course for this enrollment"""
        for record in self:
            if record.state != 'enrolled':
                raise UserError(_('Only enrolled students can start the course.'))
            record.state = 'in_progress'

    def action_complete(self):
        """Complete the enrollment"""
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Only in-progress enrollments can be completed.'))
            record.state = 'completed'

    def action_drop(self):
        """Drop from course"""
        for record in self:
            if record.state in ['completed', 'dropped', 'cancelled']:
                raise UserError(_('Cannot drop from a completed, dropped, or cancelled enrollment.'))
            record.state = 'dropped'

    def action_cancel(self):
        """Cancel enrollment"""
        for record in self:
            if record.state in ['completed', 'cancelled']:
                raise UserError(_('Cannot cancel a completed or already cancelled enrollment.'))
            record.state = 'cancelled'

    def action_issue_certificate(self):
        """Issue certificate"""
        for record in self:
            if record.state != 'completed':
                raise UserError(_('Certificate can only be issued for completed courses.'))

            if not record.certificate_issued:
                # Generate certificate number
                sequence = self.env['ir.sequence'].next_by_code('hallway.certificate') or 'CERT/00001'
                record.write({
                    'certificate_issued': True,
                    'certificate_date': date.today(),
                    'certificate_number': sequence
                })

    def action_view_attendance(self):
        """View attendance records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendance',
            'res_model': 'hallway.attendance',
            'view_mode': 'list,form',
            'domain': [('enrollment_id', '=', self.id)],
            'context': {'default_enrollment_id': self.id}
        }

    @api.onchange('student_id')
    def _onchange_student_id(self):
        """Get the latest application for the student"""
        if self.student_id:
            latest_application = self.env['student.application'].search([
                ('student_id', '=', self.student_id.id)
            ], order='application_date desc', limit=1)
            if latest_application:
                self.application_id = latest_application
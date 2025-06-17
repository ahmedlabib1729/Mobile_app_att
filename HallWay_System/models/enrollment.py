from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from dateutil.relativedelta import relativedelta


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

    # Financial - Basic
    course_price = fields.Float(related='course_id.price', string='Course Price', store=True)
    discount_percent = fields.Float(string='Discount (%)', default=0.0)
    discount_amount = fields.Float(string='Discount Amount', compute='_compute_amounts', store=True)
    final_price = fields.Float(string='Final Price', compute='_compute_amounts', store=True)

    # Payment Method
    payment_method = fields.Selection([
        ('full', 'Full Payment'),
        ('installments', 'Installments')
    ], string='Payment Method', default='full', required=True, tracking=True)

    # Installment Details
    installment_count = fields.Integer(string='Number of Installments', default=3)
    has_down_payment = fields.Boolean(string='Has Down Payment', default=False)
    down_payment_amount = fields.Float(string='Down Payment Amount', default=0.0)
    down_payment_percentage = fields.Float(string='Down Payment %', default=0.0)
    installment_start_date = fields.Date(string='Installment Start Date', default=fields.Date.today)

    # Computed Payment Fields
    remaining_amount = fields.Float(string='Remaining Amount', compute='_compute_payment_amounts', store=True)
    installment_amount = fields.Float(string='Installment Amount', compute='_compute_payment_amounts', store=True)

    # Payment Lines
    payment_line_ids = fields.One2many('hallway.payment.line', 'enrollment_id', string='Payment Lines')

    # Payment Summary
    total_paid = fields.Float(string='Total Paid', compute='_compute_payment_summary')
    total_pending = fields.Float(string='Total Pending', compute='_compute_payment_summary')
    payment_progress = fields.Float(string='Payment Progress (%)', compute='_compute_payment_summary')
    overdue_count = fields.Integer(string='Overdue Payments', compute='_compute_payment_summary',
                                   search='_search_overdue_count')

    payment_state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid')
    ], string='Payment Status', default='unpaid', compute='_compute_payment_summary', store=True)

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

    @api.depends('final_price', 'has_down_payment', 'down_payment_amount', 'down_payment_percentage',
                 'installment_count')
    def _compute_payment_amounts(self):
        for record in self:
            if record.has_down_payment:
                if record.down_payment_percentage > 0:
                    record.down_payment_amount = (record.final_price * record.down_payment_percentage) / 100
                record.remaining_amount = record.final_price - record.down_payment_amount
            else:
                record.remaining_amount = record.final_price

            if record.payment_method == 'installments' and record.installment_count > 0:
                record.installment_amount = record.remaining_amount / record.installment_count
            else:
                record.installment_amount = 0

    @api.depends('payment_line_ids', 'payment_line_ids.state', 'payment_line_ids.final_amount')
    def _compute_payment_summary(self):
        for record in self:
            paid_lines = record.payment_line_ids.filtered(lambda l: l.state == 'paid')
            pending_lines = record.payment_line_ids.filtered(lambda l: l.state in ['pending', 'overdue'])
            overdue_lines = record.payment_line_ids.filtered(lambda l: l.state == 'overdue')

            record.total_paid = sum(paid_lines.mapped('final_amount'))
            record.total_pending = sum(pending_lines.mapped('final_amount'))
            record.overdue_count = len(overdue_lines)

            if record.final_price > 0:
                record.payment_progress = (record.total_paid / record.final_price) * 100
            else:
                record.payment_progress = 0

            # Update payment state
            if record.payment_progress >= 100:
                record.payment_state = 'paid'
            elif record.payment_progress > 0:
                record.payment_state = 'partial'
            else:
                record.payment_state = 'unpaid'

    def _search_overdue_count(self, operator, value):
        """Make overdue_count searchable"""
        enrollments = self.search([])
        valid_ids = []
        for enrollment in enrollments:
            if operator == '>':
                if enrollment.overdue_count > value:
                    valid_ids.append(enrollment.id)
            elif operator == '=':
                if enrollment.overdue_count == value:
                    valid_ids.append(enrollment.id)
            elif operator == '>=':
                if enrollment.overdue_count >= value:
                    valid_ids.append(enrollment.id)
        return [('id', 'in', valid_ids)]

    @api.depends('attendance_ids', 'attendance_ids.status')
    def _compute_attendance_rate(self):
        for record in self:
            total_sessions = len(record.attendance_ids)
            if total_sessions > 0:
                present_sessions = len(record.attendance_ids.filtered(lambda a: a.status == 'present'))
                record.attendance_rate = (present_sessions / total_sessions) * 100
            else:
                record.attendance_rate = 0

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        if self.payment_method == 'full':
            self.has_down_payment = False
            self.installment_count = 1

    @api.onchange('down_payment_percentage')
    def _onchange_down_payment_percentage(self):
        if self.down_payment_percentage > 0:
            self.down_payment_amount = (self.final_price * self.down_payment_percentage) / 100

    @api.model
    def create(self, vals):
        if vals.get('enrollment_number', 'New') == 'New':
            vals['enrollment_number'] = self.env['ir.sequence'].next_by_code('hallway.enrollment') or 'New'

        # Check course capacity
        if 'course_id' in vals:
            course = self.env['hallway.course'].browse(vals['course_id'])
            if course.available_seats <= 0:
                raise UserError(_('This course is full. No seats available.'))

        enrollment = super(Enrollment, self).create(vals)

        # Generate payment lines after creation
        if enrollment.state == 'enrolled':
            enrollment.generate_payment_lines()

        return enrollment

    def generate_payment_lines(self):
        """Generate payment lines based on payment method"""
        self.ensure_one()

        # Delete existing draft payment lines
        self.payment_line_ids.filtered(lambda l: l.state == 'draft').unlink()

        if self.payment_method == 'full':
            # Create single payment line
            self.env['hallway.payment.line'].create({
                'enrollment_id': self.id,
                'sequence': 1,
                'original_amount': self.final_price,
                'due_date': self.enrollment_date,
                'is_down_payment': False,
                'state': 'pending',
            })
        else:  # installments
            sequence = 1

            # Create down payment line if applicable
            if self.has_down_payment and self.down_payment_amount > 0:
                self.env['hallway.payment.line'].create({
                    'enrollment_id': self.id,
                    'sequence': sequence,
                    'original_amount': self.down_payment_amount,
                    'due_date': self.enrollment_date,
                    'is_down_payment': True,
                    'state': 'pending',
                })
                sequence += 1

            # Calculate installment amount
            if self.installment_count > 0:
                base_amount = self.remaining_amount / self.installment_count
                remainder = self.remaining_amount - (base_amount * self.installment_count)

                # Create installment lines
                for i in range(self.installment_count):
                    amount = base_amount
                    if i == 0 and remainder > 0:
                        amount += remainder  # Add remainder to first installment

                    due_date = self.installment_start_date + relativedelta(months=i)

                    self.env['hallway.payment.line'].create({
                        'enrollment_id': self.id,
                        'sequence': sequence,
                        'original_amount': amount,
                        'due_date': due_date,
                        'is_down_payment': False,
                        'state': 'pending',
                    })
                    sequence += 1

    def action_enroll(self):
        """Confirm enrollment"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft enrollments can be confirmed.'))

            # Check course capacity again
            if record.course_id.available_seats <= 0:
                raise UserError(_('This course is full. No seats available.'))

            record.state = 'enrolled'

            # Generate payment lines
            record.generate_payment_lines()

            # Send notification
            record.message_post(
                body=f"Student {record.student_id.full_name} enrolled in {record.course_id.name}",
                subtype_xmlid="mail.mt_comment"
            )

    def action_regenerate_payment_lines(self):
        """Regenerate payment lines (only for unpaid lines)"""
        for record in self:
            # Check if there are paid lines
            paid_lines = record.payment_line_ids.filtered(lambda l: l.state == 'paid')
            if paid_lines:
                raise UserError(_('Cannot regenerate payment lines when there are already paid installments!'))

            record.generate_payment_lines()

    def action_view_payment_lines(self):
        """View payment lines"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Schedule',
            'res_model': 'hallway.payment.line',
            'view_mode': 'list,form',
            'domain': [('enrollment_id', '=', self.id)],
            'context': {
                'default_enrollment_id': self.id,
                'create': False,
            }
        }

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
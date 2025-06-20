
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class Enrollment(models.Model):
    _name = 'hallway.enrollment'
    _description = 'Student Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'enrollment_number'
    _order = 'enrollment_date desc, id desc'

    # Basic Information
    enrollment_number = fields.Char(string='Enrollment Number', required=True, copy=False, readonly=True, default='New')
    student_id = fields.Many2one('hallway.student', string='Student', required=True,
                                 ondelete='restrict', tracking=True)
    application_id = fields.Many2one('student.application', string='Application',
                                     domain="[('student_id', '=', student_id)]")

    # Program Information
    application_program_id = fields.Many2one('application.program', string='Program Selection',
                                             required=True, ondelete='restrict')
    program_id = fields.Many2one('hallway.program', string='Program',
                                 compute='_compute_program_info', store=True)
    level_ids = fields.Many2many('program.level', string='Enrolled Levels',
                                 compute='_compute_program_info', store=True)

    # Dates
    enrollment_date = fields.Date(string='Enrollment Date', required=True,
                                  default=fields.Date.today, tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    expected_end_date = fields.Date(string='Expected End Date', compute='_compute_expected_end_date',
                                    store=True)
    actual_end_date = fields.Date(string='Actual End Date', readonly=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    # Financial Information
    total_amount = fields.Monetary(string='Total Amount', required=True, tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Cash - Full Payment'),
        ('installment', 'Installment Plan')
    ], string='Payment Method', required=True, default='cash')

    installment_count = fields.Integer(string='Number of Installments', default=1)
    amount_paid = fields.Monetary(string='Amount Paid', compute='_compute_payment_info', store=True)
    amount_remaining = fields.Monetary(string='Amount Remaining', compute='_compute_payment_info', store=True)
    payment_percentage = fields.Float(string='Payment %', compute='_compute_payment_info', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id, required=True)

    # Relations
    payment_plan_id = fields.Many2one('enrollment.payment.plan', string='Payment Plan',
                                      ondelete='restrict', copy=False)
    installment_ids = fields.One2many('enrollment.installment', 'enrollment_id', string='Installments')
    payment_ids = fields.One2many('enrollment.payment', 'enrollment_id', string='Payments')

    # Additional Info
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)

    # Computed display fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    has_overdue = fields.Boolean(string='Has Overdue', compute='_compute_has_overdue', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('enrollment_number', 'New') == 'New':
                vals['enrollment_number'] = self.env['ir.sequence'].next_by_code('hallway.enrollment') or 'New'

        return super().create(vals_list)

    @api.depends('application_program_id')
    def _compute_program_info(self):
        for record in self:
            if record.application_program_id:
                record.program_id = record.application_program_id.program_id
                record.level_ids = record.application_program_id.level_ids
            else:
                record.program_id = False
                record.level_ids = [(5, 0, 0)]  # Clear all

    @api.depends('student_id', 'enrollment_number', 'program_id')
    def _compute_display_name(self):
        for record in self:
            if record.student_id and record.program_id:
                record.display_name = f"{record.enrollment_number} - {record.student_id.full_name} - {record.program_id.display_name}"
            else:
                record.display_name = record.enrollment_number or 'New'

    @api.depends('start_date', 'level_ids')
    def _compute_expected_end_date(self):
        for record in self:
            if record.start_date and record.level_ids:
                # Assume each level takes 3 months (can be customized)
                months = len(record.level_ids) * 3
                record.expected_end_date = record.start_date + relativedelta(months=months)
            else:
                record.expected_end_date = False

    @api.depends('payment_ids.amount', 'payment_ids.state', 'total_amount')
    def _compute_payment_info(self):
        for record in self:
            confirmed_payments = record.payment_ids.filtered(lambda p: p.state == 'confirmed')
            record.amount_paid = sum(confirmed_payments.mapped('amount'))
            record.amount_remaining = record.total_amount - record.amount_paid
            record.payment_percentage = (record.amount_paid / record.total_amount * 100) if record.total_amount else 0

    @api.onchange('application_program_id')
    def _onchange_application_program_id(self):
        if self.application_program_id:
            self.total_amount = self.application_program_id.total_price

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        if self.payment_method == 'cash':
            self.installment_count = 1
        elif self.payment_method == 'installment' and self.installment_count <= 1:
            self.installment_count = 2

    @api.constrains('installment_count')
    def _check_installment_count(self):
        for record in self:
            if record.payment_method == 'installment' and record.installment_count < 2:
                raise ValidationError(_('Installment plan must have at least 2 installments.'))

    @api.constrains('start_date', 'enrollment_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.enrollment_date:
                if record.start_date < record.enrollment_date:
                    raise ValidationError(_('Start date cannot be before enrollment date.'))

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft enrollments can be confirmed.'))

            # Validate required fields
            if not record.level_ids:
                raise UserError(_('Please select at least one level.'))

            record.state = 'confirmed'

            # Create payment plan if installment method
            if record.payment_method == 'installment' and not record.payment_plan_id:
                record._create_payment_plan()

    def _create_payment_plan(self):
        """Create payment plan"""
        self.ensure_one()

        # Create payment plan
        plan_vals = {
            'enrollment_id': self.id,
            'total_amount': self.total_amount,
            'installment_count': self.installment_count,
            'payment_frequency': 'monthly',  # Default
        }

        payment_plan = self.env['enrollment.payment.plan'].create(plan_vals)
        self.payment_plan_id = payment_plan
        payment_plan.action_activate()

    def action_activate(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Only confirmed enrollments can be activated.'))

            record.state = 'active'

    def action_suspend(self):
        for record in self:
            if record.state != 'active':
                raise UserError(_('Only active enrollments can be suspended.'))
            record.state = 'suspended'

    def action_resume(self):
        for record in self:
            if record.state != 'suspended':
                raise UserError(_('Only suspended enrollments can be resumed.'))
            record.state = 'active'

    def action_complete(self):
        for record in self:
            if record.state not in ['active', 'suspended']:
                raise UserError(_('Only active or suspended enrollments can be completed.'))

            # Check if all payments are made
            if record.amount_remaining > 0:
                raise UserError(_('Cannot complete enrollment with pending payments. Remaining amount: %s %s') %
                                (record.amount_remaining, record.currency_id.symbol))

            record.state = 'completed'
            record.actual_end_date = fields.Date.today()

    def action_cancel(self):
        for record in self:
            if record.state in ['completed', 'cancelled']:
                raise UserError(_('Cannot cancel completed or already cancelled enrollments.'))
            record.state = 'cancelled'

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'enrollment.payment',
            'view_mode': 'list,form',
            'domain': [('enrollment_id', '=', self.id)],
            'context': {'default_enrollment_id': self.id}
        }

    def action_view_installments(self):
        self.ensure_one()
        return {
            'name': _('Installments'),
            'type': 'ir.actions.act_window',
            'res_model': 'enrollment.installment',
            'view_mode': 'list,form',
            'domain': [('enrollment_id', '=', self.id)],
            'context': {'default_enrollment_id': self.id}
        }

    @api.depends('installment_ids.state', 'installment_ids.due_date')
    def _compute_has_overdue(self):
        today = fields.Date.today()
        for record in self:
            overdue_installments = record.installment_ids.filtered(
                lambda i: i.state == 'pending' and i.due_date < today
            )
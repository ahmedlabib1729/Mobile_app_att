from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
import math


class EnrollmentPaymentPlan(models.Model):
    _name = 'enrollment.payment.plan'
    _description = 'Enrollment Payment Plan'
    _rec_name = 'display_name'
    _order = 'create_date desc'

    enrollment_id = fields.Many2one('hallway.enrollment', string='Enrollment',
                                    required=True, ondelete='cascade')
    student_id = fields.Many2one('hallway.student', related='enrollment_id.student_id',
                                 store=True, string='Student')

    # Plan Details
    total_amount = fields.Monetary(string='Total Amount', required=True)
    installment_count = fields.Integer(string='Number of Installments', required=True, default=2)
    payment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual')
    ], string='Payment Frequency', required=True, default='monthly')

    # Installment Details
    installment_amount = fields.Monetary(string='Installment Amount',
                                         compute='_compute_installment_amount', store=True)
    first_payment_date = fields.Date(string='First Payment Date', required=True,
                                     default=fields.Date.today)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)

    # Relations
    installment_ids = fields.One2many('enrollment.installment', 'payment_plan_id', string='Installments')

    # Additional fields
    currency_id = fields.Many2one('res.currency', related='enrollment_id.currency_id',
                                  store=True, string='Currency')
    notes = fields.Text(string='Notes')

    # Display
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    progress = fields.Float(string='Payment Progress', compute='_compute_progress', store=True)

    @api.depends('enrollment_id', 'installment_count', 'payment_frequency')
    def _compute_display_name(self):
        for record in self:
            if record.enrollment_id:
                record.display_name = f"{record.enrollment_id.enrollment_number} - {record.installment_count} {record.payment_frequency} installments"
            else:
                record.display_name = f"{record.installment_count} installments"

    @api.depends('total_amount', 'installment_count')
    def _compute_installment_amount(self):
        for record in self:
            if record.installment_count > 0:
                # Calculate base amount per installment
                base_amount = record.total_amount / record.installment_count
                # Round to 2 decimal places
                record.installment_amount = math.ceil(base_amount * 100) / 100
            else:
                record.installment_amount = 0

    @api.constrains('installment_count')
    def _check_installment_count(self):
        for record in self:
            if record.installment_count < 2:
                raise ValidationError(_('Payment plan must have at least 2 installments.'))
            if record.installment_count > 12:
                raise ValidationError(_('Payment plan cannot have more than 12 installments.'))

    @api.constrains('total_amount')
    def _check_total_amount(self):
        for record in self:
            if record.total_amount <= 0:
                raise ValidationError(_('Total amount must be greater than zero.'))

    @api.depends('installment_ids.state')
    def _compute_progress(self):
        for record in self:
            if record.installment_ids:
                paid_count = len(record.installment_ids.filtered(lambda i: i.state == 'paid'))
                total_count = len(record.installment_ids)
                record.progress = (paid_count / total_count * 100) if total_count else 0
            else:
                record.progress = 0

    def generate_installments(self):
        """Generate installment records based on the payment plan"""
        self.ensure_one()

        # Delete existing installments
        self.installment_ids.unlink()

        # Calculate installment amounts
        installments_data = self._prepare_installments_data()

        # Create installments
        for data in installments_data:
            self.env['enrollment.installment'].create(data)

        return True

    def _prepare_installments_data(self):
        """Prepare data for creating installments"""
        self.ensure_one()

        installments_data = []
        remaining_amount = self.total_amount
        current_date = self.first_payment_date

        for i in range(self.installment_count):
            # Calculate amount for this installment
            if i == self.installment_count - 1:  # Last installment
                # Assign remaining amount to avoid rounding issues
                amount = remaining_amount
            else:
                amount = self.installment_amount

            # Prepare installment data
            installment_data = {
                'enrollment_id': self.enrollment_id.id,
                'payment_plan_id': self.id,
                'sequence': i + 1,
                'amount': amount,
                'due_date': current_date,
                'state': 'pending',
                'currency_id': self.currency_id.id,
            }

            installments_data.append(installment_data)

            # Update remaining amount
            remaining_amount -= amount

            # Calculate next due date
            if self.payment_frequency == 'monthly':
                current_date = current_date + relativedelta(months=1)
            elif self.payment_frequency == 'quarterly':
                current_date = current_date + relativedelta(months=3)
            elif self.payment_frequency == 'semi_annual':
                current_date = current_date + relativedelta(months=6)

        return installments_data

    def action_activate(self):
        """Activate the payment plan"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft payment plans can be activated.'))

            # Generate installments if not exists
            if not record.installment_ids:
                record.generate_installments()

            record.state = 'active'

    def action_complete(self):
        """Mark payment plan as completed"""
        for record in self:
            if record.state != 'active':
                raise UserError(_('Only active payment plans can be completed.'))
            record.state = 'completed'

    def action_cancel(self):
        """Cancel payment plan"""
        for record in self:
            if record.state == 'completed':
                raise UserError(_('Cannot cancel completed payment plan.'))
            record.state = 'cancelled'

    @api.model
    def get_payment_frequency_months(self, frequency):
        """Get number of months for payment frequency"""
        mapping = {
            'monthly': 1,
            'quarterly': 3,
            'semi_annual': 6
        }
        return mapping.get(frequency, 1)
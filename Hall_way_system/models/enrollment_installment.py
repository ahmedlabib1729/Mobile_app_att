from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class EnrollmentInstallment(models.Model):
    _name = 'enrollment.installment'
    _description = 'Enrollment Installment'
    _order = 'enrollment_id, sequence'
    _rec_name = 'display_name'

    # Relations
    enrollment_id = fields.Many2one('hallway.enrollment', string='Enrollment',
                                    required=True, ondelete='cascade')
    payment_plan_id = fields.Many2one('enrollment.payment.plan', string='Payment Plan',
                                      ondelete='cascade')
    student_id = fields.Many2one('hallway.student', related='enrollment_id.student_id',
                                 store=True, string='Student')

    # Installment Details
    sequence = fields.Integer(string='Installment Number', required=True, default=1)
    amount = fields.Monetary(string='Amount', required=True)
    due_date = fields.Date(string='Due Date', required=True)
    payment_date = fields.Date(string='Payment Date', readonly=True)

    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', required=True)

    # Payment Details
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('card', 'Credit/Debit Card'),
        ('transfer', 'Bank Transfer')
    ], string='Payment Method')

    receipt_number = fields.Char(string='Receipt Number')
    payment_reference = fields.Char(string='Payment Reference')

    # Additional Fields
    currency_id = fields.Many2one('res.currency', related='enrollment_id.currency_id',
                                  store=True, string='Currency')
    notes = fields.Text(string='Notes')

    # Computed Fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    days_overdue = fields.Integer(string='Days Overdue', compute='_compute_overdue_info')
    is_overdue = fields.Boolean(string='Is Overdue', compute='_compute_overdue_info', store=True)

    # Related payment
    payment_ids = fields.One2many('enrollment.payment', 'installment_id', string='Payments')
    paid_amount = fields.Monetary(string='Paid Amount', compute='_compute_paid_amount', store=True)
    remaining_amount = fields.Monetary(string='Remaining Amount', compute='_compute_paid_amount', store=True)

    @api.depends('enrollment_id', 'sequence', 'amount')
    def _compute_display_name(self):
        for record in self:
            if record.enrollment_id:
                record.display_name = f"{record.enrollment_id.enrollment_number} - Installment {record.sequence} - {record.currency_id.symbol}{record.amount:,.2f}"
            else:
                record.display_name = f"Installment {record.sequence}"

    @api.depends('due_date', 'state')
    def _compute_overdue_info(self):
        today = fields.Date.today()
        for record in self:
            if record.state == 'pending' and record.due_date:
                if record.due_date < today:
                    record.is_overdue = True
                    record.days_overdue = (today - record.due_date).days
                else:
                    record.is_overdue = False
                    record.days_overdue = 0
            else:
                record.is_overdue = False
                record.days_overdue = 0

    @api.depends('payment_ids.amount', 'payment_ids.state')
    def _compute_paid_amount(self):
        for record in self:
            confirmed_payments = record.payment_ids.filtered(lambda p: p.state == 'confirmed')
            record.paid_amount = sum(confirmed_payments.mapped('amount'))
            record.remaining_amount = record.amount - record.paid_amount

    @api.constrains('sequence')
    def _check_sequence(self):
        for record in self:
            if record.sequence <= 0:
                raise ValidationError(_('Installment number must be greater than zero.'))

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('Installment amount must be greater than zero.'))

    def mark_as_paid(self, payment_method=None, reference=None, receipt=None):
        """Mark installment as paid"""
        self.ensure_one()

        if self.state != 'pending':
            raise UserError(_('Only pending installments can be marked as paid.'))

        vals = {
            'state': 'paid',
            'payment_date': fields.Date.today(),
        }

        if payment_method:
            vals['payment_method'] = payment_method
        if reference:
            vals['payment_reference'] = reference
        if receipt:
            vals['receipt_number'] = receipt

        self.write(vals)

        # Check if all installments are paid
        if self.payment_plan_id:
            all_paid = all(inst.state == 'paid' for inst in self.payment_plan_id.installment_ids)
            if all_paid:
                self.payment_plan_id.action_complete()

        return True

    def action_register_payment(self):
        """Open wizard to register payment"""
        self.ensure_one()

        if self.state != 'pending':
            raise UserError(_('Payment can only be registered for pending installments.'))

        # Create payment record
        payment_vals = {
            'enrollment_id': self.enrollment_id.id,
            'installment_id': self.id,
            'amount': self.remaining_amount,
            'payment_date': fields.Date.today(),
            'payment_method': 'cash',  # Default
            'state': 'draft',
        }

        payment = self.env['enrollment.payment'].create(payment_vals)

        # Open payment form
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'enrollment.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_enrollment_id': self.enrollment_id.id,
                'default_installment_id': self.id,
                'default_amount': self.remaining_amount,
            }
        }

    def action_send_reminder(self):
        """Send payment reminder"""
        self.ensure_one()

        if self.state != 'pending':
            raise UserError(_('Reminders can only be sent for pending installments.'))

        # Implement reminder logic (email/SMS/notification)
        # For now, just create an activity
        self.enrollment_id.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=_('Payment Reminder: Installment %s due on %s') % (self.sequence, self.due_date),
            date_deadline=self.due_date,
            user_id=self.enrollment_id.create_uid.id,
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reminder Sent'),
                'message': _('Payment reminder has been scheduled.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def update_overdue_status(self):
        """Cron job to update overdue status"""
        today = fields.Date.today()

        # Find all pending installments with past due dates
        overdue_installments = self.search([
            ('state', '=', 'pending'),
            ('due_date', '<', today)
        ])

        # Update status to overdue
        overdue_installments.write({'state': 'overdue'})

        # Create activities for overdue installments
        for installment in overdue_installments:
            # Check if activity already exists
            existing_activity = installment.enrollment_id.activity_ids.filtered(
                lambda a: a.summary and f'Overdue: Installment {installment.sequence}' in a.summary
            )

            if not existing_activity:
                installment.enrollment_id.activity_schedule(
                    'mail.mail_activity_data_warning',
                    summary=_('Overdue: Installment %s - %s days overdue') %
                            (installment.sequence, installment.days_overdue),
                    date_deadline=today,
                    user_id=installment.enrollment_id.create_uid.id,
                )

        return True
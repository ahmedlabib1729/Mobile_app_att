from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class EnrollmentPayment(models.Model):
    _name = 'enrollment.payment'
    _description = 'Enrollment Payment'
    _order = 'payment_date desc, id desc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Relations
    enrollment_id = fields.Many2one('hallway.enrollment', string='Enrollment',
                                    required=True, ondelete='restrict', tracking=True)
    student_id = fields.Many2one('hallway.student', related='enrollment_id.student_id',
                                 store=True, string='Student')
    installment_id = fields.Many2one('enrollment.installment', string='Installment',
                                     domain="[('enrollment_id', '=', enrollment_id), ('state', '=', 'pending')]")

    # Payment Details
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    payment_date = fields.Date(string='Payment Date', required=True,
                               default=fields.Date.today, tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('card', 'Credit/Debit Card'),
        ('transfer', 'Bank Transfer')
    ], string='Payment Method', required=True, default='cash', tracking=True)

    # Reference Information
    reference = fields.Char(string='Payment Reference', tracking=True)
    check_number = fields.Char(string='Check Number')
    bank_name = fields.Char(string='Bank Name')
    transaction_id = fields.Char(string='Transaction ID')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True)

    # Additional Fields
    currency_id = fields.Many2one('res.currency', related='enrollment_id.currency_id',
                                  store=True, string='Currency')
    notes = fields.Text(string='Notes')
    receipt_number = fields.Char(string='Receipt Number', readonly=True, copy=False)

    # Computed Fields
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    remaining_amount = fields.Monetary(string='Enrollment Remaining',
                                       related='enrollment_id.amount_remaining')

    # Company
    company_id = fields.Many2one('res.company', related='enrollment_id.company_id',
                                 store=True, string='Company')

    @api.depends('enrollment_id', 'amount', 'payment_date')
    def _compute_display_name(self):
        for record in self:
            if record.enrollment_id:
                record.display_name = f"{record.enrollment_id.enrollment_number} - {record.currency_id.symbol}{record.amount:,.2f} - {record.payment_date}"
            else:
                record.display_name = f"Payment {record.currency_id.symbol}{record.amount:,.2f}"

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('Payment amount must be greater than zero.'))

    @api.constrains('amount', 'enrollment_id')
    def _check_overpayment(self):
        for record in self:
            if record.state == 'confirmed' and record.enrollment_id:
                # Calculate total with this payment
                other_payments = record.enrollment_id.payment_ids.filtered(
                    lambda p: p.state == 'confirmed' and p.id != record.id
                )
                total_paid = sum(other_payments.mapped('amount')) + record.amount

                if total_paid > record.enrollment_id.total_amount:
                    raise ValidationError(
                        _('Payment amount exceeds remaining balance. '
                          'Remaining amount: %s %s') %
                        (record.enrollment_id.amount_remaining, record.currency_id.symbol)
                    )

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        # Clear fields based on payment method
        if self.payment_method != 'check':
            self.check_number = False
            self.bank_name = False
        if self.payment_method not in ['card', 'transfer']:
            self.transaction_id = False

    @api.onchange('installment_id')
    def _onchange_installment_id(self):
        if self.installment_id:
            self.amount = self.installment_id.remaining_amount

    def action_confirm(self):
        """Confirm payment"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft payments can be confirmed.'))

            # Generate receipt number if not exists
            if not record.receipt_number:
                record.receipt_number = self.env['ir.sequence'].next_by_code('enrollment.payment.receipt') or 'New'

            # Update state
            record.state = 'confirmed'

            # Update installment if linked
            if record.installment_id:
                # Check if installment is fully paid
                if record.installment_id.remaining_amount <= record.amount:
                    record.installment_id.mark_as_paid(
                        payment_method=record.payment_method,
                        reference=record.reference,
                        receipt=record.receipt_number
                    )

            # Check if enrollment is fully paid
            if record.enrollment_id.amount_remaining <= 0:
                # Send notification or perform action
                pass

    def action_cancel(self):
        """Cancel payment"""
        for record in self:
            if record.state == 'cancelled':
                raise UserError(_('Payment is already cancelled.'))

            if record.state == 'confirmed':
                # If linked to installment, revert its status
                if record.installment_id and record.installment_id.state == 'paid':
                    # Check if this was the only payment for the installment
                    other_payments = record.installment_id.payment_ids.filtered(
                        lambda p: p.state == 'confirmed' and p.id != record.id
                    )
                    if not other_payments:
                        record.installment_id.write({
                            'state': 'pending',
                            'payment_date': False,
                            'payment_method': False,
                            'payment_reference': False,
                            'receipt_number': False,
                        })

            record.state = 'cancelled'

    def action_print_receipt(self):
        """Print payment receipt"""
        self.ensure_one()

        if self.state != 'confirmed':
            raise UserError(_('Receipt can only be printed for confirmed payments.'))

        # Return report action
        # TODO: Create report template
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Receipt printing feature will be available soon.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_send_receipt(self):
        """Send receipt by email"""
        self.ensure_one()

        if self.state != 'confirmed':
            raise UserError(_('Receipt can only be sent for confirmed payments.'))

        # TODO: Implement email sending logic
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Info'),
                'message': _('Email feature will be available soon.'),
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def create_from_installment(self, installment_id):
        """Helper method to create payment from installment"""
        installment = self.env['enrollment.installment'].browse(installment_id)

        if not installment.exists():
            raise UserError(_('Installment not found.'))

        if installment.state != 'pending':
            raise UserError(_('Payment can only be created for pending installments.'))

        vals = {
            'enrollment_id': installment.enrollment_id.id,
            'installment_id': installment.id,
            'amount': installment.remaining_amount,
            'payment_date': fields.Date.today(),
            'state': 'draft',
        }

        return self.create(vals)

    def get_payment_summary(self):
        """Get payment summary for reporting"""
        self.ensure_one()

        return {
            'student_name': self.student_id.full_name,
            'enrollment_number': self.enrollment_id.enrollment_number,
            'program': self.enrollment_id.program_id.display_name,
            'payment_date': self.payment_date,
            'amount': self.amount,
            'payment_method': dict(self._fields['payment_method'].selection).get(self.payment_method),
            'receipt_number': self.receipt_number,
            'reference': self.reference or '',
            'status': dict(self._fields['state'].selection).get(self.state),
        }
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class PaymentLine(models.Model):
    _name = 'hallway.payment.line'
    _description = 'Payment Installment Line'
    _order = 'enrollment_id, sequence, due_date'
    _rec_name = 'description'

    # Basic Information
    enrollment_id = fields.Many2one('hallway.enrollment', string='Enrollment', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Installment #', required=True, default=1)
    description = fields.Char(string='Description', compute='_compute_description', store=True)

    # Amounts
    original_amount = fields.Float(string='Original Amount', required=True)
    discount_amount = fields.Float(string='Discount', default=0.0)
    final_amount = fields.Float(string='Final Amount', compute='_compute_final_amount', store=True)

    # Dates
    due_date = fields.Date(string='Due Date', required=True)
    payment_date = fields.Date(string='Payment Date')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('overdue', 'Overdue'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)

    # Flags
    is_down_payment = fields.Boolean(string='Is Down Payment', default=False)

    # Invoice Link
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_state = fields.Selection(related='invoice_id.state', string='Invoice Status', readonly=True)

    # Related Fields
    student_id = fields.Many2one(related='enrollment_id.student_id', string='Student', store=True)
    course_id = fields.Many2one(related='enrollment_id.course_id', string='Course', store=True)
    currency_id = fields.Many2one(related='enrollment_id.currency_id', string='Currency', store=True)

    # Company
    company_id = fields.Many2one(
        'res.company', string="Company", required=True,
        default=lambda self: self.env.company
    )

    @api.depends('sequence', 'due_date', 'is_down_payment')
    def _compute_description(self):
        for record in self:
            if record.is_down_payment:
                record.description = _("Down Payment")
            elif record.due_date:
                month_year = record.due_date.strftime('%B %Y')
                record.description = _("Installment %s - %s") % (record.sequence, month_year)
            else:
                record.description = _("Installment %s") % record.sequence

    @api.depends('original_amount', 'discount_amount')
    def _compute_final_amount(self):
        for record in self:
            record.final_amount = record.original_amount - record.discount_amount

    @api.model
    def create(self, vals):
        payment_line = super(PaymentLine, self).create(vals)
        payment_line._update_state()
        return payment_line

    def write(self, vals):
        res = super(PaymentLine, self).write(vals)
        if 'payment_date' in vals or 'invoice_id' in vals:
            self._update_state()
        return res

    def _update_state(self):
        """Update payment line state based on conditions"""
        today = date.today()
        for record in self:
            if record.state == 'cancelled':
                continue

            if record.invoice_id and record.invoice_id.payment_state == 'paid':
                record.state = 'paid'
                if not record.payment_date:
                    record.payment_date = fields.Date.today()
            elif record.payment_date:
                record.state = 'paid'
            elif record.due_date and record.due_date < today and record.state not in ['paid', 'cancelled']:
                record.state = 'overdue'
            elif record.state == 'draft':
                record.state = 'pending'

    def action_create_invoice(self):
        """Create invoice for this payment line"""
        self.ensure_one()

        if self.invoice_id:
            raise UserError(_("Invoice already exists for this payment line!"))

        if self.state == 'cancelled':
            raise UserError(_("Cannot create invoice for cancelled payment line!"))

        # Prepare invoice values
        partner = self.student_id.partner_id
        if not partner:
            raise UserError(_("Student must have a contact partner to create invoice!"))

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': self.due_date,
            'ref': f"{self.enrollment_id.enrollment_number} - {self.description}",
            'invoice_line_ids': [(0, 0, {
                'name': f"{self.course_id.name} - {self.description}",
                'quantity': 1,
                'price_unit': self.final_amount,
            })],
        }

        # Create invoice
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice

        # Return action to view invoice
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        """View the related invoice"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice created for this payment line!"))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Cancel this payment line"""
        for record in self:
            if record.state == 'paid':
                raise UserError(_("Cannot cancel paid payment lines!"))
            if record.invoice_id and record.invoice_id.state != 'cancel':
                raise UserError(_("Please cancel the related invoice first!"))
            record.state = 'cancelled'

    @api.model
    def update_overdue_payments(self):
        """Cron job to update overdue payments"""
        today = date.today()
        pending_payments = self.search([
            ('state', '=', 'pending'),
            ('due_date', '<', today)
        ])
        pending_payments.write({'state': 'overdue'})
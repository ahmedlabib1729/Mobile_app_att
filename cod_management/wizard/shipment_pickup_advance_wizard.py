# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ShipmentPickupAdvanceWizard(models.TransientModel):
    """Wizard لتأكيد الدفعة المخططة عند Pickup"""
    _name = 'shipment.pickup.advance.wizard'
    _description = 'Pickup Advance Payment Wizard'

    shipment_id = fields.Many2one(
        'shipment.order',
        string='Shipment',
        required=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    customer_invoice_id = fields.Many2one(
        'account.move',
        string='Customer Invoice',
        readonly=True,
        help='Invoice created for this shipment'
    )

    # المبلغ المخطط (للعرض فقط)
    planned_amount = fields.Float(
        string='Planned Amount',
        readonly=True,
        help='Originally planned advance amount'
    )

    # المبلغ الفعلي (قابل للتعديل)
    amount = fields.Float(
        string='Actual Amount',
        required=True,
        help='Actual amount to be paid (can be different from planned)'
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        required=True,
        domain=[('type', 'in', ['cash', 'bank'])]
    )

    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today
    )

    reference = fields.Char(
        string='Reference/Memo',
        help='Payment reference or receipt number'
    )

    # حقول سبب التخطي
    skip_reason = fields.Selection([
        ('customer_not_paid', 'Customer Did Not Pay'),
        ('postponed', 'Postponed'),
        ('cancelled', 'Cancelled'),
        ('other', 'Other'),
    ], string='Skip Reason')

    skip_notes = fields.Text(
        string='Skip Notes'
    )

    # معلومات إضافية للعرض
    shipment_total = fields.Float(
        string='Shipment Total',
        related='shipment_id.total_company_cost',
        readonly=True
    )

    invoice_amount = fields.Float(
        string='Invoice Amount',
        related='customer_invoice_id.amount_total',
        readonly=True
    )

    difference = fields.Float(
        string='Difference from Planned',
        compute='_compute_difference'
    )

    @api.model
    def default_get(self, fields_list):
        """تعيين القيم الافتراضية"""
        res = super().default_get(fields_list)

        # الحصول على journal افتراضي
        journal = self.env['account.journal'].search([
            ('type', 'in', ['cash', 'bank'])
        ], limit=1)

        if journal:
            res['journal_id'] = journal.id

        return res

    @api.depends('amount', 'planned_amount')
    def _compute_difference(self):
        """حساب الفرق بين المبلغ المخطط والفعلي"""
        for record in self:
            record.difference = record.amount - record.planned_amount

    def action_confirm_payment(self):
        """تأكيد الدفعة وإنشاء Payment"""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_('Amount must be greater than zero!'))

        if not self.journal_id:
            raise UserError(_('Please select a payment journal!'))

        # إنشاء الدفعة
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'currency_id': self.env.company.currency_id.id,
            'journal_id': self.journal_id.id,
            'date': self.payment_date,
            'memo': self.reference or f'Advance - {self.shipment_id.order_number}',
            'shipment_advance_id': self.shipment_id.id,
        }

        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        # ربط الدفعة بالفاتورة (Auto Reconcile)
        reconciled = False
        if self.customer_invoice_id and self.customer_invoice_id.state == 'posted':
            if self.customer_invoice_id.payment_state != 'paid' and self.customer_invoice_id.amount_residual > 0:
                try:
                    # سطور الدفعة (Receivable)
                    payment_lines = payment.move_id.line_ids.filtered(
                        lambda l: l.account_id.account_type == 'asset_receivable'
                                  and not l.reconciled
                    )

                    # سطور الفاتورة (Receivable)
                    invoice_lines = self.customer_invoice_id.line_ids.filtered(
                        lambda l: l.account_id.account_type == 'asset_receivable'
                                  and not l.reconciled
                    )

                    if payment_lines and invoice_lines:
                        (payment_lines + invoice_lines).reconcile()
                        reconciled = True

                except Exception as e:
                    self.shipment_id.message_post(
                        body=f"<b>Warning:</b> Could not auto-reconcile with invoice: {str(e)}",
                        subject="Reconciliation Warning"
                    )

        # تحديث الشحنة
        self.shipment_id.write({
            'planned_advance_status': 'confirmed',
        })

        # تحديث COD Amount
        self.shipment_id._update_cod_after_advance()

        # رسالة على الشحنة
        message_body = f"""
        <b>✓ Advance Payment Confirmed at Pickup</b><br/>
        <table style="margin-top:10px;">
            <tr><td><b>Planned Amount:</b></td><td>{self.planned_amount:.2f} EGP</td></tr>
            <tr><td><b>Actual Paid:</b></td><td>{self.amount:.2f} EGP</td></tr>
            <tr><td><b>Difference:</b></td><td>{self.difference:.2f} EGP</td></tr>
            <tr><td><b>Payment:</b></td><td>{payment.name}</td></tr>
            <tr><td><b>Journal:</b></td><td>{self.journal_id.name}</td></tr>
        </table>
        """

        if reconciled:
            message_body += f"""
            <br/><b style="color: green;">✓ Auto-Reconciled with Invoice {self.customer_invoice_id.name}</b>
            """

        self.shipment_id.message_post(body=message_body, subject="Advance Payment Confirmed")

        # إكمال Pickup
        return self.shipment_id._complete_pickup()

    def action_skip(self):
        """تخطي الدفعة المخططة"""
        self.ensure_one()

        if not self.skip_reason:
            raise UserError(_('Please select a skip reason!'))

        # تحديث الشحنة
        self.shipment_id.write({
            'planned_advance_status': 'skipped',
            'advance_skip_reason': self.skip_reason,
            'advance_skip_notes': self.skip_notes,
        })

        # رسالة على الشحنة
        reason_display = dict(self._fields['skip_reason'].selection).get(self.skip_reason, self.skip_reason)
        message_body = f"""
        <b style="color: orange;">⚠ Planned Advance Payment Skipped</b><br/>
        <table style="margin-top:10px;">
            <tr><td><b>Planned Amount:</b></td><td>{self.planned_amount:.2f} EGP</td></tr>
            <tr><td><b>Reason:</b></td><td>{reason_display}</td></tr>
        </table>
        """

        if self.skip_notes:
            message_body += f"<br/><b>Notes:</b> {self.skip_notes}"

        self.shipment_id.message_post(body=message_body, subject="Advance Payment Skipped")

        # إكمال Pickup
        return self.shipment_id._complete_pickup()


class ShipmentPlannedAdvanceWizard(models.TransientModel):
    """Wizard لتسجيل دفعة مخططة (معلومة فقط)"""
    _name = 'shipment.planned.advance.wizard'
    _description = 'Set Planned Advance Wizard'

    shipment_id = fields.Many2one(
        'shipment.order',
        string='Shipment',
        required=True
    )

    amount = fields.Float(
        string='Planned Amount',
        required=True,
        help='Amount the customer plans to pay in advance'
    )

    notes = fields.Text(
        string='Notes'
    )

    # معلومات للعرض
    shipment_total = fields.Float(
        string='Shipment Total',
        related='shipment_id.total_company_cost',
        readonly=True
    )

    def action_confirm(self):
        """تأكيد تسجيل الدفعة المخططة"""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_('Amount must be greater than zero!'))

        self.shipment_id.write({
            'planned_advance_amount': self.amount,
            'planned_advance_status': 'planned',
            'planned_advance_date': fields.Date.today(),
        })

        self.shipment_id.message_post(
            body=f"""
            <b>Planned Advance Payment Registered</b><br/>
            Amount: {self.amount:.2f} EGP<br/>
            <i>Note: This is information only. Actual payment will be confirmed at pickup.</i>
            """,
            subject="Planned Advance"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Planned advance of {self.amount:.2f} EGP registered'),
                'type': 'success',
            }
        }

    def action_clear(self):
        """إلغاء الدفعة المخططة"""
        self.ensure_one()

        self.shipment_id.write({
            'planned_advance_amount': 0,
            'planned_advance_status': 'none',
            'planned_advance_date': False,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cleared'),
                'message': _('Planned advance has been cleared'),
                'type': 'info',
            }
        }
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CODCustomerPayment(models.Model):
    """دفعات COD للعملاء"""
    _name = 'cod.customer.payment'
    _description = 'COD Customer Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    batch_id = fields.Many2one(
        'cod.batch',
        string='COD Batch',
        required=True
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )

    shipment_ids = fields.Many2many(
        'shipment.order',
        string='Shipments'
    )

    shipment_count = fields.Integer(
        string='Shipment Count',
        compute='_compute_counts'
    )

    total_cod_products = fields.Float(
        string='Total COD Products',
        help='Total COD amount for products only'
    )

    total_cod = fields.Float(
        string='Total COD',
        readonly=True
    )

    total_deductions = fields.Float(
        string='Total Deductions',
        readonly=True
    )

    net_amount = fields.Float(
        string='Net Amount',
        readonly=True
    )

    payment_date = fields.Date(
        string='Payment Date'
    )

    payment_reference = fields.Char(
        string='Payment Reference'
    )

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('check', 'Check')
    ], string='Payment Method', default='bank')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid')
    ], default='draft', tracking=True)

    invoice_ids = fields.Many2many(
        'account.move',
        'cod_payment_invoice_rel',
        'payment_id',
        'invoice_id',
        string='Related Invoices',
        domain="[('partner_id', '=', customer_id), ('move_type', '=', 'out_invoice'), ('payment_state', '!=', 'paid')]"
    )

    total_invoice_amount = fields.Float(
        string='Total Invoice Amount',
        compute='_compute_invoice_amounts',
        store=True
    )

    remaining_credit = fields.Float(
        string='Remaining Credit',
        compute='_compute_invoice_amounts',
        store=True,
        help='Amount remaining after settling invoices'
    )

    amount_from_shipping = fields.Float(
        string='Amount from Shipping',
        compute='_compute_shipping_amounts',
        store=True,
        help='Total amount we will receive from shipping company for this customer'
    )

    shipping_charges = fields.Float(
        string='Shipping Charges',
        compute='_compute_shipping_amounts',
        store=True,
        help='Total shipping charges for this customer shipments'
    )

    notes = fields.Text('Notes')

    @api.depends('shipment_ids', 'shipment_ids.cod_amount_sheet_excel', 'shipment_ids.shipping_cost')  # تغيير
    def _compute_shipping_amounts(self):
        """حساب المبلغ المستلم من شركة الشحن"""
        for record in self:
            if record.shipment_ids:
                # إجمالي COD للعميل
                total_cod = sum(record.shipment_ids.mapped('cod_amount_sheet_excel'))  # هنا التغيير
                # إجمالي تكاليف الشحن
                total_shipping = sum(record.shipment_ids.mapped('shipping_cost'))
                # المبلغ اللي هنستلمه من شركة الشحن
                record.amount_from_shipping = total_cod - total_shipping
                record.shipping_charges = total_shipping
            else:
                record.amount_from_shipping = 0
                record.shipping_charges = 0

    @api.depends('invoice_ids', 'net_amount')
    def _compute_invoice_amounts(self):
        for record in self:
            record.total_invoice_amount = sum(record.invoice_ids.mapped('amount_residual'))
            record.remaining_credit = record.net_amount - record.total_invoice_amount

    @api.onchange('shipment_ids')
    def _onchange_shipment_ids(self):
        """عند تغيير الشحنات، جلب الفواتير المرتبطة تلقائياً"""
        if self.shipment_ids:
            # جلب كل الفواتير المرتبطة بهذه الشحنات
            invoice_ids = self.shipment_ids.mapped('invoice_ids').filtered(
                lambda inv: inv.state == 'posted' and inv.payment_state != 'paid'
            )
            if invoice_ids:
                self.invoice_ids = [(6, 0, invoice_ids.ids)]

    def action_mark_paid(self):
        """تسجيل الدفع للعميل مع خصم الفواتير"""
        self.ensure_one()

        # أولاً: خصم الفواتير إن وجدت
        if self.invoice_ids:
            self._reconcile_invoices()

        # ثانياً: إذا كان هناك مبلغ متبقي، سجله كرصيد دائن
        if self.remaining_credit > 0:
            self._create_customer_credit()

        # تحديث الشحنات
        self.shipment_ids.write({
            'cod_status': 'settled',
            'cod_settled_date': fields.Datetime.now()
        })

        self.write({
            'state': 'paid',
            'payment_date': fields.Date.today()
        })

        # رسالة تفصيلية
        message = f"""
        <b>COD Settlement Complete</b><br/>
        Customer: {self.customer_id.name}<br/>
        Net COD Amount: {self.net_amount:.2f} EGP<br/>
        """

        if self.invoice_ids:
            message += f"Invoices Settled: {len(self.invoice_ids)}<br/>"
            message += f"Invoice Amount: {self.total_invoice_amount:.2f} EGP<br/>"

        if self.remaining_credit > 0:
            message += f"<b>Credit Balance: {self.remaining_credit:.2f} EGP</b><br/>"

        self.message_post(body=message, subject="COD Settlement")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Settlement complete. Net: {self.net_amount:.2f} EGP'),
                'type': 'success',
            }
        }

    def _reconcile_invoices(self):
        """خصم الفواتير من مبلغ COD"""
        payment_journal = self.env['account.journal'].search([
            ('type', 'in', ['cash', 'bank'])
        ], limit=1)

        if not payment_journal:
            raise UserError(_('Please configure a payment journal!'))

        # المبلغ المتاح للدفع
        available_amount = min(self.net_amount, self.total_invoice_amount)

        # إنشاء الدفعة
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer_id.id,
            'amount': available_amount,
            'currency_id': self.env.company.currency_id.id,
            'journal_id': payment_journal.id,
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
        }

        payment = self.env['account.payment'].create(payment_vals)

        # إضافة المرجع
        if hasattr(payment, 'memo'):
            payment.memo = f'COD Settlement - {self.batch_id.name}'

        payment.action_post()

        # المطابقة مع الفواتير
        for invoice in self.invoice_ids:
            if invoice.amount_residual > 0:
                # سطور الدفعة
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                              and not l.reconciled
                )

                # سطور الفاتورة
                invoice_lines = invoice.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                              and not l.reconciled
                )

                if payment_lines and invoice_lines:
                    (payment_lines + invoice_lines).reconcile()

    def _create_customer_credit(self, amount):
        """إنشاء رصيد دائن للعميل"""
        if amount <= 0:
            return

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale')
        ], limit=1)

        if not journal:
            return

        # إنشاء إشعار دائن
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.customer_id.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'ref': f'COD Credit - Batch {self.batch_id.name}',
            'invoice_line_ids': [(0, 0, {
                'name': f'COD Settlement Credit - {len(self.shipment_ids)} shipments\nBatch: {self.batch_id.name}',
                'quantity': 1,
                'price_unit': amount,
                'account_id': self._get_income_account().id,
            })]
        })

        credit_note.action_post()

        self.message_post(
            body=f"Credit Note Created: {credit_note.name} for {amount:.2f} EGP",
            subject="Customer Credit"
        )

    def _get_income_account(self):
        """الحصول على حساب الإيرادات"""
        account = self.env['account.account'].search([
            ('account_type', '=', 'income')
        ], limit=1)

        if not account:
            account = self.env['account.account'].search([
                ('account_type', 'in', ['income', 'income_other'])
            ], limit=1)

        return account

    @api.depends('shipment_ids')
    def _compute_counts(self):
        for record in self:
            record.shipment_count = len(record.shipment_ids)

    def action_confirm(self):
        """تأكيد الدفعة"""
        self.state = 'confirmed'

    def action_mark_paid(self):
        """تسجيل الدفع للعميل مع خصم الفواتير تلقائياً - يراعي الدفعات المقدمة"""
        self.ensure_one()

        # تأكد من إعادة حساب المبالغ بالنظام الجديد
        for shipment in self.shipment_ids:
            shipment._compute_cod_amounts()

        # إعادة حساب إجماليات الدفعة
        self.total_cod = sum(self.shipment_ids.mapped('cod_amount_sheet_excel'))
        self.total_deductions = sum(self.shipment_ids.mapped('total_deductions'))
        self.net_amount = sum(self.shipment_ids.mapped('cod_net_for_customer'))

        # البحث عن فواتير العميل المفتوحة من الشحنات
        customer_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('partner_id', '=', self.customer_id.id),
            ('shipment_id', 'in', self.shipment_ids.ids),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid')
        ])

        total_paid_to_invoices = 0
        invoices_details = []

        if customer_invoices:
            # ===== حساب المبلغ المتبقي فعلياً في الفواتير (بعد أي دفعات مقدمة) =====
            # amount_residual = المتبقي الفعلي بعد خصم أي دفعات سابقة
            total_invoices_residual = sum(customer_invoices.mapped('amount_residual'))

            if total_invoices_residual > 0:
                # المبلغ المتاح للخصم من صافي COD
                available_for_invoices = min(self.net_amount, total_invoices_residual)

                # إنشاء دفعة لخصم الفواتير
                payment_journal = self.env['account.journal'].search([
                    ('type', 'in', ['cash', 'bank'])
                ], limit=1)

                if not payment_journal:
                    raise UserError(_('Please configure a payment journal!'))

                payment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': self.customer_id.id,
                    'amount': available_for_invoices,
                    'currency_id': self.env.company.currency_id.id,
                    'journal_id': payment_journal.id,
                    'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                }

                payment = self.env['account.payment'].create(payment_vals)

                # إضافة المرجع
                if hasattr(payment, 'memo'):
                    payment.memo = f'COD Settlement - Batch {self.batch_id.name}'

                # ترحيل الدفعة
                payment.action_post()

                # ===== مطابقة الفواتير - كل فاتورة حسب المتبقي فيها =====
                remaining_payment = available_for_invoices

                for invoice in customer_invoices:
                    # المتبقي الفعلي في هذه الفاتورة (بعد أي دفعات مقدمة)
                    invoice_residual = invoice.amount_residual

                    if invoice_residual > 0 and remaining_payment > 0:
                        # المبلغ الذي سيتم دفعه لهذه الفاتورة
                        amount_for_this_invoice = min(invoice_residual, remaining_payment)

                        # تسجيل التفاصيل للرسالة
                        advance_paid = invoice.amount_total - invoice_residual
                        invoices_details.append({
                            'name': invoice.name,
                            'total': invoice.amount_total,
                            'advance_paid': advance_paid,
                            'residual_before': invoice_residual,
                            'paid_now': amount_for_this_invoice
                        })

                        # سطور الدفعة
                        payment_lines = payment.move_id.line_ids.filtered(
                            lambda l: l.account_id.account_type == 'asset_receivable'
                                      and l.partner_id == self.customer_id
                                      and not l.reconciled
                        )

                        # سطور الفاتورة
                        invoice_lines = invoice.line_ids.filtered(
                            lambda l: l.account_id.account_type == 'asset_receivable'
                                      and not l.reconciled
                        )

                        if payment_lines and invoice_lines:
                            try:
                                (payment_lines + invoice_lines).reconcile()
                                total_paid_to_invoices += amount_for_this_invoice
                                remaining_payment -= amount_for_this_invoice
                            except Exception as e:
                                # لو فشل الـ Reconcile لفاتورة معينة، كمّل للباقي
                                pass

                # حساب المبلغ المتبقي بعد خصم الفواتير
                remaining_after_invoices = self.net_amount - total_paid_to_invoices
            else:
                # كل الفواتير مدفوعة بالكامل (من دفعات مقدمة)
                remaining_after_invoices = self.net_amount
        else:
            remaining_after_invoices = self.net_amount

        # إذا كان هناك مبلغ متبقي بعد سداد الفواتير
        if remaining_after_invoices > 0:
            # إنشاء إشعار دائن أو تسجيل كرصيد للعميل
            self._create_customer_credit(remaining_after_invoices)

        # تحديث حالة الشحنات
        self.shipment_ids.write({
            'cod_status': 'settled',
            'cod_settled_date': fields.Datetime.now()
        })

        # تحديث حالة الدفعة
        self.write({
            'state': 'paid',
            'payment_date': fields.Date.today()
        })

        # ===== رسالة تفصيلية محسنة =====
        message = f"""
        <b>COD Settlement Complete</b><br/>
        Customer: {self.customer_id.name}<br/>
        <br/>
        <b>COD Summary:</b><br/>
        Total COD Amount: {self.total_cod:.2f} EGP<br/>
        Total Deductions: {self.total_deductions:.2f} EGP<br/>
        Net Amount for Customer: {self.net_amount:.2f} EGP<br/>
        """

        # تفاصيل الفواتير مع الدفعات المقدمة
        if invoices_details:
            message += f"""
            <br/>
            <b>Invoices Settlement Details:</b><br/>
            <table style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f0f0f0;">
                <th style="border: 1px solid #ddd; padding: 5px;">Invoice</th>
                <th style="border: 1px solid #ddd; padding: 5px;">Total</th>
                <th style="border: 1px solid #ddd; padding: 5px;">Advance Paid</th>
                <th style="border: 1px solid #ddd; padding: 5px;">Was Due</th>
                <th style="border: 1px solid #ddd; padding: 5px;">Paid Now</th>
            </tr>
            """
            for inv in invoices_details:
                message += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 5px;">{inv['name']}</td>
                    <td style="border: 1px solid #ddd; padding: 5px;">{inv['total']:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 5px;">{inv['advance_paid']:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 5px;">{inv['residual_before']:.2f}</td>
                    <td style="border: 1px solid #ddd; padding: 5px;">{inv['paid_now']:.2f}</td>
                </tr>
                """
            message += f"""
            </table>
            <br/>
            <b>Total Paid to Invoices: {total_paid_to_invoices:.2f} EGP</b><br/>
            """

        if remaining_after_invoices > 0:
            message += f"""
            <br/>
            <b style="color: green;">✓ Credit Balance Created: {remaining_after_invoices:.2f} EGP</b><br/>
            """

        self.message_post(body=message, subject="COD Customer Settlement")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    f'Settlement complete. Net: {self.net_amount:.2f} EGP. Paid to invoices: {total_paid_to_invoices:.2f} EGP'),
                'type': 'success',
                'sticky': True,
            }
        }

    def _create_journal_entry(self):
        """إنشاء قيد محاسبي للدفع"""
        journal = self.env['account.journal'].search([
            ('type', '=', 'cash')
        ], limit=1)

        if not journal:
            return

        move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f'COD Payment - {self.customer_id.name}',
            'line_ids': [
                (0, 0, {
                    'name': f'COD Settlement - Batch {self.batch_id.name}',
                    'debit': self.net_amount,
                    'credit': 0,
                    'partner_id': self.customer_id.id,
                }),
                (0, 0, {
                    'name': f'COD Payment to Customer',
                    'debit': 0,
                    'credit': self.net_amount,
                    'partner_id': self.customer_id.id,
                })
            ]
        }

        move = self.env['account.move'].create(move_vals)
        move.action_post()
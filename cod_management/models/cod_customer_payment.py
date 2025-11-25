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
        """تسجيل الدفع للعميل مع خصم الفواتير تلقائياً"""
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

        if customer_invoices:
            # حساب المبلغ المستحق في الفواتير
            total_invoices = sum(customer_invoices.mapped('amount_residual'))

            if total_invoices > 0:
                # المبلغ المتاح للخصم (صافي COD)
                amount_to_pay = min(self.net_amount, total_invoices)

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
                    'amount': amount_to_pay,
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

                # مطابقة الفواتير
                for invoice in customer_invoices:
                    if invoice.amount_residual > 0 and amount_to_pay > 0:
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
                            (payment_lines + invoice_lines).reconcile()
                            amount_to_pay -= min(invoice.amount_residual, amount_to_pay)

                # حساب المبلغ المتبقي بعد خصم الفواتير
                remaining_after_invoices = self.net_amount - min(self.net_amount, total_invoices)
            else:
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

        # رسالة تفصيلية مع توضيح النظام الجديد
        message = f"""
        <b>COD Settlement Complete (New System)</b><br/>
        Customer: {self.customer_id.name}<br/>
        <br/>
        <b>COD Calculation:</b><br/>
        Total COD Amount: {self.total_cod:.2f} EGP<br/>
        """

        # إضافة تفاصيل الحساب الجديد
        for shipment in self.shipment_ids[:3]:  # عرض أول 3 شحنات كمثال
            shipping_cost = shipment.shipping_cost or 0
            company_cost = shipment.total_company_cost or 0
            deduction = shipping_cost - company_cost
            actual_deduction = max(0, deduction)

            message += f"""
            <br/>Shipment {shipment.order_number}:<br/>
            - Shipping Cost: {shipping_cost:.2f} EGP<br/>
            - Company Cost: {company_cost:.2f} EGP<br/>
            - Deduction (Shipping - Company): {deduction:.2f} EGP<br/>
            - Applied Deduction: {actual_deduction:.2f} EGP<br/>
            """

        if len(self.shipment_ids) > 3:
            message += f"<br/>... and {len(self.shipment_ids) - 3} more shipments<br/>"

        message += f"""
        <br/>
        <b>Summary:</b><br/>
        Total Deductions: {self.total_deductions:.2f} EGP<br/>
        Net Amount for Customer: {self.net_amount:.2f} EGP<br/>
        """

        if customer_invoices:
            paid_invoices = customer_invoices.filtered(lambda inv: inv.payment_state == 'paid')
            total_invoices = sum(customer_invoices.mapped('amount_residual'))
            message += f"""
            <br/>
            <b>Invoices Settled:</b> {len(paid_invoices)} of {len(customer_invoices)}<br/>
            Invoice Amount Paid: {min(self.net_amount, total_invoices):.2f} EGP<br/>
            """

        if remaining_after_invoices > 0:
            message += f"""
            <br/>
            <b style="color: green;">Credit Balance Created: {remaining_after_invoices:.2f} EGP</b><br/>
            """

        self.message_post(body=message, subject="COD Customer Settlement - New System")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    f'Settlement complete. Net amount: {self.net_amount:.2f} EGP. {len(customer_invoices) if customer_invoices else 0} invoices processed.'),
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
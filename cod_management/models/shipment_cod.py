# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class ShipmentOrderCOD(models.Model):
    _inherit = 'shipment.order'

    # ===== حقول حالة COD =====
    cod_status = fields.Selection([
        ('na', 'Not Applicable'),
        ('pending', 'Pending'),
        ('collected_at_courier', 'Collected at Courier'),
        ('received_from_courier', 'Received from Courier'),
        ('settled', 'Settled with Customer'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled')
    ], string='COD Status',
        default='na',
        tracking=True,
        compute='_compute_cod_status',
        store=True,
        readonly=False,
        help='Current status of COD amount in the collection cycle')

    # ===== التواريخ الأساسية =====
    cod_collected_date = fields.Datetime(
        string='COD Collected Date',
        tracking=True,
        help='Date when COD was collected from recipient'
    )

    cod_received_date = fields.Datetime(
        string='COD Received Date',
        tracking=True,
        help='Date when we received COD from shipping company'
    )

    cod_settled_date = fields.Datetime(
        string='COD Settled Date',
        tracking=True,
        help='Date when COD was settled with customer'
    )

    # ===== حقول محسوبة للمبالغ =====
    cod_net_for_customer = fields.Float(
        string='Net Amount for Customer',
        compute='_compute_cod_amounts',
        store=True,
        help='COD amount after deducting all charges'
    )

    total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_cod_amounts',
        store=True,
        help='Total amount deducted (our charges + shipping charges)'
    )

    # ===== ملاحظات التتبع =====
    cod_notes = fields.Text(
        string='COD Notes',
        help='Internal notes for COD tracking'
    )

    # ===== مؤشرات =====
    is_cod_order = fields.Boolean(
        string='Is COD Order',
        compute='_compute_is_cod_order',
        store=True
    )

    days_since_collection = fields.Integer(
        string='Days Since Collection',
        compute='_compute_days_since_collection'
    )

    cod_vendor_settled_date = fields.Datetime(
        string='Vendor Settlement Date',
        help='Date when COD was settled with shipping company'
    )

    vendor_bill_status = fields.Selection([
        ('no_bill', 'No Bill'),
        ('to_bill', 'To Bill'),
        ('billed', 'Billed'),
        ('paid', 'Paid'),
    ], string='Vendor Bill Status',
        compute='_compute_vendor_bill_status',
        store=True,
        default='no_bill'
    )

    cod_amount_from_shipping = fields.Float(
        string='Amount from Shipping Company',
        compute='_compute_cod_breakdown',
        store=True,
        help='Amount we receive from shipping company (COD - Shipping Cost)'
    )

    cod_our_profit = fields.Float(
        string='Our Net Profit',
        compute='_compute_cod_breakdown',
        store=True,
        help='Our profit (Company Cost - Shipping Cost)'
    )

    cod_calculation_breakdown = fields.Text(
        string='COD Calculation Breakdown',
        compute='_compute_cod_breakdown',
        store=True
    )

    # ===== حقول الدفعة المقدمة (جديد) =====
    advance_payment_ids = fields.One2many(
        'account.payment',
        'shipment_advance_id',
        string='Advance Payments',
        domain=[('payment_type', '=', 'inbound')]
    )

    total_advance_paid = fields.Float(
        string='Total Advance Paid',
        compute='_compute_advance_payment',
        store=True,
        tracking=True
    )

    advance_payment_count = fields.Integer(
        string='Advance Payments Count',
        compute='_compute_advance_payment',
        store=True
    )

    advance_payment_status = fields.Selection([
        ('no_payment', 'No Advance'),
        ('partial', 'Partial Advance'),
        ('full', 'Full Advance'),
    ], string='Advance Status',
        compute='_compute_advance_payment',
        store=True
    )

    remaining_to_pay = fields.Float(
        string='Remaining to Pay',
        compute='_compute_advance_payment',
        store=True,
        help='Remaining amount after advance payments'
    )

    prepaid_amount_due = fields.Float(
        string='Prepaid Amount Due',
        compute='_compute_prepaid_amount_due',
        store=True,
        help='Remaining amount to pay for prepaid orders after advance payments'
    )

    # ===== Compute Methods =====

    @api.depends('advance_payment_ids', 'advance_payment_ids.state',
                 'advance_payment_ids.amount', 'total_company_cost')
    def _compute_advance_payment(self):
        """حساب إجمالي الدفعات المقدمة"""
        for record in self:
            # تغيير الفلتر ليشمل كل الحالات ماعدا draft و cancelled
            confirmed_payments = record.advance_payment_ids.filtered(
                lambda p: p.state not in ['draft', 'cancelled']
            )
            record.advance_payment_count = len(confirmed_payments)
            record.total_advance_paid = sum(confirmed_payments.mapped('amount'))

            # حساب المتبقي
            total_price = record.total_company_cost or 0
            record.remaining_to_pay = max(0, total_price - record.total_advance_paid)

            # تحديد الحالة
            if record.total_advance_paid <= 0:
                record.advance_payment_status = 'no_payment'
            elif record.total_advance_paid >= total_price and total_price > 0:
                record.advance_payment_status = 'full'
            else:
                record.advance_payment_status = 'partial'

        # ===== Override _compute_cod_amount لخصم الدفعات المقدمة =====
        @api.depends('total_value', 'total_company_cost', 'total_additional_fees', 'discount_amount',
                     'payment_method', 'company_base_cost', 'company_weight_cost', 'include_services_in_cod',
                     'advance_payment_ids', 'advance_payment_ids.state', 'advance_payment_ids.amount')
        def _compute_cod_amount(self):
            """Override: حساب مبلغ COD مع خصم الدفعات المقدمة"""
            for record in self:
                if record.payment_method == 'cod':
                    record.cod_amount = record.total_value

                    if record.include_services_in_cod:
                        base_cod = round(record.total_value + record.total_company_cost)
                    else:
                        base_cod = round(record.total_value + record.company_base_cost)

                    # حساب الدفعات المقدمة المؤكدة
                    confirmed_payments = record.advance_payment_ids.filtered(
                        lambda p: p.state not in ['draft', 'cancelled']
                    )
                    advance = sum(confirmed_payments.mapped('amount'))
                    record.cod_amount_sheet_excel = max(0, base_cod - advance)
                else:
                    record.cod_amount = 0
                    record.cod_amount_sheet_excel = 0

    @api.depends('payment_method', 'total_company_cost', 'advance_payment_ids',
                 'advance_payment_ids.state', 'advance_payment_ids.amount')
    def _compute_prepaid_amount_due(self):
        """حساب المبلغ المتبقي للدفع في حالة Prepaid"""
        for record in self:
            if record.payment_method == 'prepaid':
                # حساب الدفعات المقدمة المؤكدة
                confirmed_payments = record.advance_payment_ids.filtered(
                    lambda p: p.state not in ['draft', 'cancelled']
                )
                advance = sum(confirmed_payments.mapped('amount'))

                # المبلغ المتبقي = تكلفة الشركة - الدفعات المقدمة
                record.prepaid_amount_due = max(0, (record.total_company_cost or 0) - advance)
            else:
                record.prepaid_amount_due = 0

    def _update_cod_after_advance(self):
        """تحديث المبالغ بعد إضافة دفعة مقدمة"""
        for record in self:
            # حساب الدفعات المقدمة المؤكدة
            confirmed_payments = record.advance_payment_ids.filtered(
                lambda p: p.state not in ['draft', 'cancelled']
            )
            advance = sum(confirmed_payments.mapped('amount'))

            if record.payment_method == 'cod':
                # تحديث COD Amount
                if record.include_services_in_cod:
                    base_cod = round(record.total_value + record.total_company_cost)
                else:
                    base_cod = round(record.total_value + record.company_base_cost)

                new_cod = max(0, base_cod - advance)
                record.write({'cod_amount_sheet_excel': new_cod})

            elif record.payment_method == 'prepaid':
                # تحديث Prepaid Amount Due
                new_prepaid = max(0, (record.total_company_cost or 0) - advance)
                record.write({'prepaid_amount_due': new_prepaid})

    @api.depends('cod_amount', 'total_company_cost', 'shipping_cost', 'payment_method')
    def _compute_cod_breakdown(self):
        """تفصيل حسابات COD"""
        for record in self:
            if record.payment_method == 'cod':
                record.cod_amount_from_shipping = record.cod_amount_sheet_excel - record.shipping_cost
                record.cod_our_profit = record.total_company_cost - record.shipping_cost

                breakdown = []
                breakdown.append("=== COD Calculation Breakdown ===")
                breakdown.append(f"1. Total COD Amount: {record.cod_amount_sheet_excel:.2f} EGP")
                breakdown.append(f"2. Shipping Company Cost: -{record.shipping_cost:.2f} EGP")
                breakdown.append(f"3. We receive from shipping: {record.cod_amount_from_shipping:.2f} EGP")
                breakdown.append("")
                breakdown.append(f"4. Our Total Company Cost: {record.total_company_cost:.2f} EGP")
                breakdown.append(f"5. Less Shipping Cost: -{record.shipping_cost:.2f} EGP")
                breakdown.append(f"6. Our Net Profit: {record.cod_our_profit:.2f} EGP")
                breakdown.append("")
                breakdown.append(
                    f"7. Customer receives: {record.cod_amount_from_shipping:.2f} - {record.cod_our_profit:.2f}")
                breakdown.append(f"8. Final to Customer: {record.cod_net_for_customer:.2f} EGP")

                record.cod_calculation_breakdown = '\n'.join(breakdown)
            else:
                record.cod_amount_from_shipping = 0
                record.cod_our_profit = 0
                record.cod_calculation_breakdown = ''

    @api.depends('vendor_bill_ids', 'vendor_bill_ids.state', 'shipping_company_id')
    def _compute_vendor_bill_status(self):
        for record in self:
            if not record.shipping_company_id:
                record.vendor_bill_status = 'no_bill'
            else:
                valid_bills = record.vendor_bill_ids.filtered(lambda bill: bill.state != 'cancel')

                if not valid_bills:
                    if record.state in ['confirmed', 'picked', 'in_transit', 'out_for_delivery', 'delivered']:
                        record.vendor_bill_status = 'to_bill'
                    else:
                        record.vendor_bill_status = 'no_bill'
                else:
                    if all(bill.payment_state == 'paid' for bill in valid_bills):
                        record.vendor_bill_status = 'paid'
                    else:
                        record.vendor_bill_status = 'billed'

    @api.depends('payment_method')
    def _compute_is_cod_order(self):
        """تحديد إذا كان الطلب COD"""
        for record in self:
            record.is_cod_order = (record.payment_method == 'cod')

    @api.depends('payment_method', 'state')
    def _compute_cod_status(self):
        """حساب حالة COD بناءً على حالة الشحنة"""
        for record in self:
            if record.payment_method != 'cod':
                record.cod_status = 'na'
            elif record.cod_status in ['na', False]:
                if record.state in ['draft', 'confirmed', 'picked', 'in_transit', 'out_for_delivery']:
                    record.cod_status = 'pending'
                elif record.state == 'delivered':
                    record.cod_status = 'collected_at_courier'
                elif record.state == 'cancelled':
                    record.cod_status = 'cancelled'
                elif record.state == 'returned':
                    record.cod_status = 'refunded'

    @api.depends('cod_amount_sheet_excel', 'total_company_cost', 'shipping_cost')
    def _compute_cod_amounts(self):
        """حساب المبالغ الصافية"""
        for record in self:
            if record.payment_method == 'cod':
                amount_from_shipping = record.cod_amount_sheet_excel - record.shipping_cost
                our_profit = record.total_company_cost - record.shipping_cost
                record.total_deductions = our_profit if our_profit > 0 else 0
                record.cod_net_for_customer = amount_from_shipping - record.total_deductions
            else:
                record.total_deductions = 0
                record.cod_net_for_customer = 0

    @api.depends('cod_collected_date')
    def _compute_days_since_collection(self):
        """حساب عدد الأيام منذ التحصيل"""
        for record in self:
            if record.cod_collected_date:
                delta = datetime.now() - record.cod_collected_date
                record.days_since_collection = delta.days
            else:
                record.days_since_collection = 0

    # ===== Action Methods للدفعة المقدمة =====

    def action_register_advance_payment(self):
        """فتح wizard لتسجيل دفعة مقدمة"""
        self.ensure_one()

        if not self.sender_id:
            raise UserError(_('Please select a customer (sender) first!'))

        # الحصول على journal افتراضي
        journal = self.env['account.journal'].search([
            ('type', 'in', ['cash', 'bank'])
        ], limit=1)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Advance Payment'),
            'res_model': 'shipment.advance.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shipment_id': self.id,
                'default_partner_id': self.sender_id.id,
                'default_amount': self.remaining_to_pay or self.total_company_cost,  # ✅ تغيير هنا
                'default_journal_id': journal.id if journal else False,
            }
        }

    def action_view_advance_payments(self):
        """عرض الدفعات المقدمة"""
        self.ensure_one()

        action = {
            'type': 'ir.actions.act_window',
            'name': _('Advance Payments'),
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('shipment_advance_id', '=', self.id)],
            'context': {
                'default_shipment_advance_id': self.id,
                'default_partner_id': self.sender_id.id,
                'default_payment_type': 'inbound',
            }
        }

        if len(self.advance_payment_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.advance_payment_ids.id

        return action

    # ===== Override Methods =====

    def action_deliver(self):
        """Override لتحديث حالة COD عند التسليم"""
        res = super(ShipmentOrderCOD, self).action_deliver()
        for record in self:
            if record.payment_method == 'cod':
                record.write({
                    'cod_status': 'collected_at_courier',
                    'cod_collected_date': fields.Datetime.now(),
                })
                record.message_post(
                    body=f"""
                    <b>COD Status Update:</b><br/>
                    Status: Collected at Courier<br/>
                    Amount: {record.cod_amount_sheet_excel:.2f} EGP<br/>
                    Net for Customer: {record.cod_net_for_customer:.2f} EGP<br/>
                    Total Deductions: {record.total_deductions:.2f} EGP
                    """,
                    subject="COD Collected"
                )
        return res

    def action_return(self):
        """Override لتحديث حالة COD عند الإرجاع"""
        res = super(ShipmentOrderCOD, self).action_return()
        for record in self:
            if record.payment_method == 'cod':
                record.write({
                    'cod_status': 'refunded',
                })
                record.message_post(
                    body="COD Status: Refunded due to return",
                    subject="COD Refunded"
                )
        return res

    def action_cancel(self):
        """Override لتحديث حالة COD عند الإلغاء"""
        res = super(ShipmentOrderCOD, self).action_cancel()
        for record in self:
            if record.payment_method == 'cod':
                record.write({
                    'cod_status': 'cancelled',
                })
        return res

    # ===== COD Action Methods =====

    def action_mark_cod_received(self):
        """تحديد أنه تم استلام COD من شركة الشحن"""
        self.ensure_one()
        if self.cod_status != 'collected_at_courier':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invalid Status'),
                    'message': _('COD must be collected at courier first'),
                    'type': 'warning',
                }
            }

        self.write({
            'cod_status': 'received_from_courier',
            'cod_received_date': fields.Datetime.now(),
        })

        self.message_post(
            body=f"COD received from {self.shipping_company_id.name if self.shipping_company_id else 'shipping company'}",
            subject="COD Received"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('COD marked as received from courier'),
                'type': 'success',
            }
        }

    def action_settle_with_customer(self):
        """تسوية COD مع العميل"""
        self.ensure_one()
        if self.cod_status not in ['received_from_courier', 'collected_at_courier']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invalid Status'),
                    'message': _('COD must be received first'),
                    'type': 'warning',
                }
            }

        self.write({
            'cod_status': 'settled',
            'cod_settled_date': fields.Datetime.now(),
        })

        self.message_post(
            body=f"""
            <b>COD Settlement Complete:</b><br/>
            Original COD: {self.cod_amount:.2f} EGP<br/>
            Total Deductions: {self.total_deductions:.2f} EGP<br/>
            Net Paid to Customer: {self.cod_net_for_customer:.2f} EGP
            """,
            subject="COD Settled"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'COD settled: {self.cod_net_for_customer:.2f} EGP paid to customer'),
                'type': 'success',
                'sticky': True,
            }
        }


class AccountPayment(models.Model):
    """إضافة ربط الدفعة بالشحنة"""
    _inherit = 'account.payment'

    shipment_advance_id = fields.Many2one(
        'shipment.order',
        string='Shipment (Advance)',
        help='Shipment this advance payment is for',
        tracking=True
    )

    is_shipment_advance = fields.Boolean(
        string='Is Shipment Advance',
        compute='_compute_is_shipment_advance',
        store=True
    )

    @api.depends('shipment_advance_id')
    def _compute_is_shipment_advance(self):
        for record in self:
            record.is_shipment_advance = bool(record.shipment_advance_id)


class ShipmentAdvancePaymentWizard(models.TransientModel):
    """Wizard لتسجيل دفعة مقدمة"""
    _name = 'shipment.advance.payment.wizard'
    _description = 'Shipment Advance Payment Wizard'

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

    amount = fields.Float(
        string='Amount',
        required=True
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

    # معلومات للعرض - تغيير هنا
    shipment_total = fields.Float(
        string='Shipment Total',
        related='shipment_id.total_company_cost',  # تغيير من calculated_customer_price
        readonly=True
    )

    already_paid = fields.Float(
        string='Already Paid',
        related='shipment_id.total_advance_paid',
        readonly=True
    )

    remaining = fields.Float(
        string='Remaining',
        related='shipment_id.remaining_to_pay',
        readonly=True
    )

    def action_confirm(self):
        """تأكيد وإنشاء الدفعة مع Auto Reconcile للفاتورة إن وجدت"""
        self.ensure_one()

        if self.amount <= 0:
            raise UserError(_('Amount must be greater than zero!'))

        # ===== التحقق من وجود فاتورة أولاً =====
        existing_invoice = self.env['account.move'].search([
            ('shipment_id', '=', self.shipment_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ], limit=1)

        if not existing_invoice:
            raise UserError(_(
                '⚠️ Invoice Required!\n\n'
                'You must create and post an invoice for this shipment before registering an advance payment.\n\n'
                '📋 Shipment: %s\n'
                '👤 Customer: %s\n'
                '💰 Amount: %.2f EGP\n\n'
                '👉 Please go to the shipment and click "Create Invoice" first.'
            ) % (self.shipment_id.order_number, self.partner_id.name, self.shipment_total or 0))

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

        # ✅ تحديث COD Amount مباشرة
        self.shipment_id._update_cod_after_advance()

        # ===== Auto Reconcile مع فاتورة العميل =====
        reconciled_amount = 0
        invoice_name = ''

        # الفاتورة موجودة (تم التحقق منها أعلاه) - نتحقق إنها لسه مش مدفوعة بالكامل
        if existing_invoice.payment_state != 'paid' and existing_invoice.amount_residual > 0:
            try:
                # سطور الدفعة (Receivable)
                payment_lines = payment.move_id.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                              and not l.reconciled
                )

                # سطور الفاتورة (Receivable)
                invoice_lines = existing_invoice.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                              and not l.reconciled
                )

                if payment_lines and invoice_lines:
                    (payment_lines + invoice_lines).reconcile()
                    reconciled_amount = min(self.amount, existing_invoice.amount_residual)
                    invoice_name = existing_invoice.name

            except Exception as e:
                # لو فشل الـ Reconcile، سجل رسالة بس متوقفش
                self.shipment_id.message_post(
                    body=f"<b>Warning:</b> Could not auto-reconcile with invoice: {str(e)}",
                    subject="Reconciliation Warning"
                )

        # رسالة على الشحنة
        message_body = f"""
        <b>Advance Payment Registered</b><br/>
        Amount: {self.amount:.2f} EGP<br/>
        Journal: {self.journal_id.name}<br/>
        Reference: {payment.name}<br/>
        Date: {self.payment_date}
        """

        if reconciled_amount > 0:
            message_body += f"""
            <br/><br/>
            <b style="color: green;">✓ Auto-Reconciled with Invoice {invoice_name}</b><br/>
            Reconciled Amount: {reconciled_amount:.2f} EGP
            """

        self.shipment_id.message_post(body=message_body, subject="Advance Payment")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Advance payment of {self.amount:.2f} EGP registered successfully' +
                             (f' and reconciled with invoice' if reconciled_amount > 0 else '')),
                'type': 'success',
            }
        }
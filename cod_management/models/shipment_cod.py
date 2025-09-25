# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
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
        ('billed', 'Billed'),  # تأكد أن هذه القيمة موجودة
        ('paid', 'Paid'),  # أضف هذه القيمة أيضاً
    ], string='Vendor Bill Status',
        compute='_compute_vendor_bill_status',
        store=True,
        default='no_bill'
    )

    # ===== Compute Methods =====

    @api.depends('vendor_bill_ids', 'vendor_bill_ids.state', 'shipping_company_id')
    def _compute_vendor_bill_status(self):
        for record in self:
            if not record.shipping_company_id:
                record.vendor_bill_status = 'no_bill'
            else:
                valid_bills = record.vendor_bill_ids.filtered(lambda bill: bill.state != 'cancel')

                if not valid_bills:
                    # إذا لم توجد فواتير
                    if record.state in ['confirmed', 'picked', 'in_transit', 'out_for_delivery', 'delivered']:
                        record.vendor_bill_status = 'to_bill'
                    else:
                        record.vendor_bill_status = 'no_bill'
                else:
                    # إذا وجدت فواتير، تحقق من حالة الدفع
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

    @api.depends('cod_amount', 'total_company_cost', 'shipping_cost')
    def _compute_cod_amounts(self):
        """حساب المبالغ الصافية"""
        for record in self:
            if record.payment_method == 'cod':
                record.total_deductions = record.total_company_cost + record.shipping_cost
                record.cod_net_for_customer = record.cod_amount - record.total_deductions
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
                    Amount: {record.cod_amount:.2f} EGP<br/>
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

    # ===== Action Methods =====

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
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

import logging
_logger = logging.getLogger(__name__)

class ShippingCompanyCOD(models.Model):
    """إضافة إعدادات التحصيل لشركة الشحن"""
    _inherit = 'shipping.company'

    # أيام التحصيل
    collection_sunday = fields.Boolean('Sunday')
    collection_monday = fields.Boolean('Monday')
    collection_tuesday = fields.Boolean('Tuesday')
    collection_wednesday = fields.Boolean('Wednesday')
    collection_thursday = fields.Boolean('Thursday')
    collection_friday = fields.Boolean('Friday')
    collection_saturday = fields.Boolean('Saturday')

    auto_create_batch = fields.Boolean(
        string='Auto Create Batches',
        default=False,
        help='Automatically create collection batches'
    )

    batch_cutoff_hour = fields.Float(
        string='Batch Cutoff Hour',
        default=18.0,
        help='Hour to close batch (24h format, e.g., 18.0 = 6PM)'
    )

    def get_collection_days(self):
        """إرجاع قائمة بأيام التحصيل"""
        days = []
        day_fields = [
            (0, 'collection_monday', 'Monday'),
            (1, 'collection_tuesday', 'Tuesday'),
            (2, 'collection_wednesday', 'Wednesday'),
            (3, 'collection_thursday', 'Thursday'),
            (4, 'collection_friday', 'Friday'),
            (5, 'collection_saturday', 'Saturday'),
            (6, 'collection_sunday', 'Sunday'),
        ]
        for day_num, field_name, day_name in day_fields:
            if getattr(self, field_name):
                days.append((day_num, day_name))
        return days


class CODBatch(models.Model):
    """دفعات تحصيل COD من شركات الشحن"""
    _name = 'cod.batch'
    _description = 'COD Collection Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'collection_date desc, create_date desc'

    name = fields.Char(
        string='Batch Number',
        required=True,
        copy=False,

        index=True,
        default=lambda self: _('New')
    )

    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        tracking=True,

        states={'draft': [('readonly', False)]}
    )

    collection_date = fields.Date(
        string='Collection Date',
        required=True,
        tracking=True,

        states={'draft': [('readonly', False)]},
        help='Expected collection date from shipping company'
    )

    shipment_ids = fields.Many2many(
        'shipment.order',
        'cod_batch_shipment_rel',
        'batch_id',
        'shipment_id',
        string='Shipments',

        states={'draft': [('readonly', False)]},
        domain="[('payment_method', '=', 'cod'), ('cod_status', '=', 'collected_at_courier')]"
    )

    shipment_count = fields.Integer(
        string='Number of Shipments',
        compute='_compute_amounts',
        store=True
    )

    # المبالغ
    total_cod_amount = fields.Float(
        string='Total COD Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    total_company_charges = fields.Float(
        string='Total Company Charges',
        compute='_compute_amounts',
        store=True
    )

    total_shipping_charges = fields.Float(
        string='Total Shipping Charges',
        compute='_compute_amounts',
        store=True
    )

    expected_net_amount = fields.Float(
        string='Expected Net Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True,
        help='Amount we expect to receive from shipping company'
    )

    actual_amount_received = fields.Float(
        string='Actual Amount Received',
        tracking=True,

        states={'confirmed': [('readonly', False)]}
    )

    difference_amount = fields.Float(
        string='Difference',
        compute='_compute_difference',
        store=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('collected', 'Collected'),
        ('vendor_settled', 'Vendor Settled'),
        ('customer_payments', 'Customer Payments'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    vendor_settlement_date = fields.Datetime(
        string='Vendor Settlement Date'
    )

    notes = fields.Text('Notes')

    collection_receipt = fields.Binary('Collection Receipt')
    collection_receipt_filename = fields.Char('Receipt Filename')

    auto_created = fields.Boolean(
        string='Auto Created',
        default=False,
        help='This batch was created automatically'
    )

    amount_from_shipping = fields.Float(
        string='Amount to Receive from Shipping',
        compute='_compute_amounts',
        store=True,
        help='Amount we should receive from shipping company (COD - their charges)'
    )

    # المبلغ المستحق للعملاء (بعد خصم تكاليفنا)
    amount_for_customers = fields.Float(
        string='Amount to Pay Customers',
        compute='_compute_customer_amounts',
        store=True,
        help='Total amount to be paid to customers (COD - our charges)'
    )

    # تفاصيل العملاء
    customer_payment_ids = fields.One2many(
        'cod.customer.payment',
        'batch_id',
        string='Customer Payments'
    )

    customer_count = fields.Integer(
        string='Number of Customers',
        compute='_compute_customer_amounts',
        store=True
    )

    # حقول الربح
    our_profit = fields.Float(
        string='Our Profit',
        compute='_compute_profit',
        store=True,
        help='Difference between what we receive and what we pay'
    )

    total_cod_amount_products_only = fields.Float(
        string='Total Products Value (COD)',
        compute='_compute_amounts',
        store=True,
        readonly=True,
        help='Total COD amount for products only (without shipping or company charges)'
    )

    @api.depends('amount_from_shipping', 'amount_for_customers')
    def _compute_profit(self):
        for batch in self:
            # ربحنا = ما نستلمه من الشحن - ما ندفعه للعملاء
            batch.our_profit = batch.amount_from_shipping - batch.amount_for_customers

    def action_prepare_all_customer_payments(self):
        """تحضير دفعات لكل العملاء"""
        self.ensure_one()

        # حذف الدفعات القديمة غير المدفوعة
        old_payments = self.customer_payment_ids.filtered(lambda p: p.state == 'draft')
        old_payments.unlink()

        # تجميع الشحنات حسب العميل
        customer_shipments = {}
        for shipment in self.shipment_ids:
            customer = shipment.sender_id
            if customer:
                if customer not in customer_shipments:
                    customer_shipments[customer] = self.env['shipment.order']
                customer_shipments[customer] |= shipment

        # إنشاء دفعة لكل عميل
        for customer, shipments in customer_shipments.items():
            # حساب المبالغ
            total_cod = sum(shipments.mapped('cod_amount_sheet_excel'))  # هنا التغيير
            total_cod_products = sum(shipments.mapped('cod_amount'))
            total_shipping = sum(shipments.mapped('shipping_cost'))
            amount_from_shipping = total_cod - total_shipping

            payment_vals = {
                'batch_id': self.id,
                'customer_id': customer.id,
                'shipment_ids': [(6, 0, shipments.ids)],
                'total_cod': total_cod,
                'total_cod_products': total_cod_products,
                'shipping_charges': total_shipping,
                'amount_from_shipping': amount_from_shipping,
                'total_deductions': sum(shipments.mapped('total_deductions')),
                'net_amount': sum(shipments.mapped('cod_net_for_customer')),
                'state': 'draft'
            }
            self.env['cod.customer.payment'].create(payment_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Prepared payments for {len(customer_shipments)} customers'),
                'type': 'success',
            }
        }
    def action_settle_all_customers(self):
        """تسوية كل فواتير العملاء دفعة واحدة"""
        self.ensure_one()

        if self.state != 'vendor_settled':
            raise UserError(_('Please settle vendor bills first!'))

        settled_count = 0
        for payment in self.customer_payment_ids:
            if payment.state == 'draft':
                payment.action_confirm()
            if payment.state == 'confirmed':
                payment.action_mark_paid()
                settled_count += 1

        if settled_count > 0:
            self.state = 'completed'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Settled payments for {settled_count} customers'),
                'type': 'success',
                'sticky': True,
            }
        }

    @api.depends('shipment_ids', 'shipment_ids.cod_net_for_customer')
    def _compute_customer_amounts(self):
        for batch in self:
            # تجميع حسب العملاء
            customer_data = {}
            for shipment in batch.shipment_ids:
                if shipment.sender_id:
                    if shipment.sender_id not in customer_data:
                        customer_data[shipment.sender_id] = 0
                    customer_data[shipment.sender_id] += shipment.cod_net_for_customer

            batch.customer_count = len(customer_data)
            batch.amount_for_customers = sum(customer_data.values())

    @api.depends('shipment_ids', 'shipment_ids.cod_amount', 'shipment_ids.cod_amount_sheet_excel',
                 'shipment_ids.shipping_cost', 'shipment_ids.total_company_cost')
    def _compute_amounts(self):
        for batch in self:
            shipments = batch.shipment_ids
            batch.shipment_count = len(shipments)

            # المبلغ الأصلي (قيمة المنتجات فقط)
            batch.total_cod_amount_products_only = sum(shipments.mapped('cod_amount'))

            # المبلغ الذي يُرسل لشركة الشحن (مع الإضافات)
            batch.total_cod_amount = sum(shipments.mapped('cod_amount_sheet_excel'))

            batch.total_shipping_charges = sum(shipments.mapped('shipping_cost'))
            batch.total_company_charges = sum(shipments.mapped('total_company_cost'))

            # المبلغ من شركة الشحن = COD الكامل - تكاليف الشحن
            batch.amount_from_shipping = batch.total_cod_amount - batch.total_shipping_charges
            batch.expected_net_amount = batch.amount_from_shipping

    @api.depends('expected_net_amount', 'actual_amount_received')
    def _compute_difference(self):
        for batch in self:
            batch.difference_amount = batch.actual_amount_received - batch.expected_net_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                # إنشاء رقم الدفعة
                company = self.env['shipping.company'].browse(vals.get('shipping_company_id'))
                date = fields.Date.from_string(vals.get('collection_date', fields.Date.today()))
                sequence = self.search_count([
                    ('shipping_company_id', '=', vals.get('shipping_company_id')),
                    ('collection_date', '=', vals.get('collection_date'))
                ]) + 1
                vals['name'] = f"{company.code}-{date.strftime('%Y%m%d')}-{sequence:03d}"
        return super(CODBatch, self).create(vals_list)

    def action_confirm(self):
        """تأكيد الدفعة"""
        for batch in self:
            if not batch.shipment_ids:
                raise UserError(_('Cannot confirm batch without shipments!'))

            # تحديث حالة الشحنات
            batch.shipment_ids.write({
                'cod_status': 'received_from_courier',
                'cod_received_date': fields.Datetime.now()
            })

            batch.state = 'confirmed'

            # رسالة
            batch.message_post(
                body=f"""
                <b>Batch Confirmed</b><br/>
                Shipments: {batch.shipment_count}<br/>
                Expected Amount: {batch.expected_net_amount:.2f} EGP
                """,
                subject="Batch Confirmed"
            )

    def action_mark_collected(self):
        """تسجيل استلام المبلغ"""
        for batch in self:
            if batch.actual_amount_received <= 0:
                raise UserError(_('Please enter the actual amount received!'))

            batch.state = 'collected'

            # إذا كان هناك فرق
            if abs(batch.difference_amount) > 0.01:
                batch.message_post(
                    body=f"""
                    <b style="color: {'red' if batch.difference_amount < 0 else 'green'};">
                    Difference Detected: {batch.difference_amount:.2f} EGP
                    </b><br/>
                    Expected: {batch.expected_net_amount:.2f} EGP<br/>
                    Received: {batch.actual_amount_received:.2f} EGP
                    """,
                    subject="Amount Difference"
                )

    def action_settle(self):
        """تسوية الدفعة"""
        for batch in self:
            batch.state = 'settled'

    def action_cancel(self):
        """إلغاء الدفعة"""
        for batch in self:
            if batch.state not in ['draft', 'confirmed']:
                raise UserError(_('Cannot cancel batch in this state!'))

            # إرجاع حالة الشحنات
            if batch.state == 'confirmed':
                batch.shipment_ids.write({
                    'cod_status': 'collected_at_courier',
                    'cod_received_date': False
                })

            batch.state = 'cancelled'

    def action_add_shipments(self):
        """فتح wizard لإضافة شحنات"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Shipments',
            'res_model': 'shipment.order',
            'view_mode': 'list',
            'target': 'current',
            'domain': [
                ('payment_method', '=', 'cod'),
                ('cod_status', '=', 'collected_at_courier'),
                ('shipping_company_id', '=', self.shipping_company_id.id),
                ('id', 'not in', self.shipment_ids.ids)
            ],
            'context': {
                'default_batch_id': self.id,
                'search_default_delivered': 1
            }
        }

    def action_print_report(self):
        """طباعة تقرير الدفعة"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Report'),
                'message': _('Report will be implemented in next phase'),
                'type': 'info',
            }
        }

    @api.model
    def create_batch_for_company(self, company_id, collection_date=None):
        """إنشاء دفعة لشركة معينة"""
        company = self.env['shipping.company'].browse(company_id)

        if not collection_date:
            collection_date = fields.Date.today()

        # جمع الشحنات المؤهلة
        shipments = self.env['shipment.order'].search([
            ('shipping_company_id', '=', company_id),
            ('payment_method', '=', 'cod'),
            ('cod_status', '=', 'collected_at_courier'),
            ('state', '=', 'delivered')
        ])

        if not shipments:
            return False

        # إنشاء الدفعة
        batch = self.create({
            'shipping_company_id': company_id,
            'collection_date': collection_date,
            'shipment_ids': [(6, 0, shipments.ids)],
            'auto_created': True
        })

        return batch

    def action_settle_with_shipping(self):
        """تسوية مع شركة الشحن وإقفال فواتيرهم"""
        self.ensure_one()

        if self.state != 'collected':
            raise UserError(_('Batch must be collected first!'))

        # البحث عن فواتير شركة الشحن المفتوحة
        vendor_bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('shipment_vendor_id', 'in', self.shipment_ids.ids),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid')
        ])

        if vendor_bills:
            # حساب المبلغ الإجمالي للفواتير
            total_bills = sum(vendor_bills.mapped('amount_residual'))

            if total_bills <= 0:
                raise UserError(_('No outstanding amount to pay!'))

            # إنشاء دفعة payment لإقفال الفواتير
            payment_vals = {
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': self._get_shipping_vendor_partner().id,
                'amount': min(self.actual_amount_received, total_bills),
                'currency_id': self.env.company.currency_id.id,
                'journal_id': self._get_payment_journal().id,
                'payment_method_id': self.env.ref('account.account_payment_method_manual_out').id,
            }

            payment = self.env['account.payment'].create(payment_vals)

            # إضافة المرجع بعد الإنشاء
            if hasattr(payment, 'memo'):
                payment.memo = f'COD Settlement - Batch {self.name}'

            # ترحيل الدفعة
            payment.action_post()

            # طريقة المطابقة الصحيحة في Odoo 18
            # استخدام wizard للمطابقة
            for bill in vendor_bills:
                if bill.amount_residual > 0:
                    # البحث عن سطور المطابقة
                    payment_move_line = payment.move_id.line_ids.filtered(
                        lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
                                     and line.partner_id == bill.partner_id
                                     and not line.reconciled
                    )

                    bill_move_line = bill.line_ids.filtered(
                        lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
                                     and not line.reconciled
                    )

                    if payment_move_line and bill_move_line:
                        (payment_move_line + bill_move_line).reconcile()

            # تحديث حالة الشحنات
            self.shipment_ids.write({
                'vendor_bill_status': 'paid',
                'cod_vendor_settled_date': fields.Datetime.now()
            })

            # رسالة تأكيد
            payment_ref = payment.memo if hasattr(payment, 'memo') else payment.name
            self.message_post(
                body=f"""
                <b>Vendor Bills Settled</b><br/>
                Bills Count: {len(vendor_bills)}<br/>
                Total Amount: {total_bills:.2f} EGP<br/>
                Payment: {payment_ref}
                """,
                subject="Vendor Settlement Complete"
            )

        # تحديث حالة الدفعة
        self.write({
            'state': 'vendor_settled',
            'vendor_settlement_date': fields.Datetime.now()
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Vendor bills settled successfully'),
                'type': 'success',
            }
        }

    def action_prepare_customer_payments(self):
        """تحضير المبالغ للدفع للعملاء"""
        self.ensure_one()

        # تجميع حسب العميل
        customer_amounts = {}
        for shipment in self.shipment_ids:
            customer = shipment.sender_id
            if customer not in customer_amounts:
                customer_amounts[customer] = {
                    'shipments': self.env['shipment.order'],
                    'total_cod': 0,
                    'total_deductions': 0,
                    'net_amount': 0
                }

            customer_amounts[customer]['shipments'] |= shipment
            customer_amounts[customer]['total_cod'] += shipment.cod_amount
            customer_amounts[customer]['total_deductions'] += shipment.total_deductions
            customer_amounts[customer]['net_amount'] += shipment.cod_net_for_customer

        # إنشاء سجلات دفع للعملاء
        payment_records = []
        for customer, data in customer_amounts.items():
            payment_record = self.env['cod.customer.payment'].create({
                'batch_id': self.id,
                'customer_id': customer.id,
                'shipment_ids': [(6, 0, data['shipments'].ids)],
                'total_cod': data['total_cod'],
                'total_deductions': data['total_deductions'],
                'net_amount': data['net_amount'],
                'state': 'draft'
            })
            payment_records.append(payment_record)

        # فتح نافذة المدفوعات
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Payments',
            'res_model': 'cod.customer.payment',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'default_batch_id': self.id}
        }

    def _get_shipping_vendor_partner(self):
        """الحصول على partner الخاص بشركة الشحن"""
        partner = self.env['res.partner'].search([
            ('name', '=', self.shipping_company_id.name),
            ('supplier_rank', '>', 0)
        ], limit=1)

        if not partner:
            # إنشاء partner جديد
            partner = self.env['res.partner'].create({
                'name': self.shipping_company_id.name,
                'supplier_rank': 1,
                'is_company': True,
            })

        return partner

    def _get_payment_journal(self):
        """الحصول على دفتر المدفوعات"""
        journal = self.env['account.journal'].search([
            ('type', 'in', ['cash', 'bank'])
        ], limit=1)

        if not journal:
            raise UserError(_('Please configure a payment journal first!'))

        return journal

    import logging
    _logger = logging.getLogger(__name__)

    # في class CODBatch أضف:

    @api.model
    def auto_create_batches_for_all_companies(self):
        """دالة تشتغل يومياً لإنشاء batches للشركات"""
        _logger.info("Starting auto creation of COD batches...")

        # جيب كل شركات الشحن اللي مفعل عندها auto_create_batch
        companies = self.env['shipping.company'].search([
            ('auto_create_batch', '=', True)
        ])

        created_batches = 0
        today = fields.Date.today()
        current_weekday = today.weekday()  # 0=Monday, 6=Sunday

        for company in companies:
            try:
                # تحقق هل اليوم من أيام التحصيل للشركة
                collection_days = company.get_collection_days()
                is_collection_day = any(day[0] == current_weekday for day in collection_days)

                if not is_collection_day:
                    _logger.info(f"Today is not a collection day for {company.name}")
                    continue

                # تحقق من وجود batch لنفس اليوم
                existing_batch = self.search([
                    ('shipping_company_id', '=', company.id),
                    ('collection_date', '=', today),
                    ('state', '!=', 'cancelled')
                ])

                if existing_batch:
                    _logger.info(f"Batch already exists for {company.name} on {today}")
                    continue

                # جمع الشحنات المؤهلة
                shipments = self.env['shipment.order'].search([
                    ('shipping_company_id', '=', company.id),
                    ('payment_method', '=', 'cod'),
                    ('cod_status', '=', 'collected_at_courier'),
                    ('state', '=', 'delivered')
                ])

                if not shipments:
                    _logger.info(f"No eligible shipments for {company.name}")
                    continue

                # إنشاء الدفعة
                batch_vals = {
                    'shipping_company_id': company.id,
                    'collection_date': today,
                    'shipment_ids': [(6, 0, shipments.ids)],
                    'auto_created': True,
                    'state': 'draft',
                    'notes': f'Auto-created on {today} at {fields.Datetime.now()}'
                }

                batch = self.create(batch_vals)
                created_batches += 1

                _logger.info(f"Created batch {batch.name} for {company.name} with {len(shipments)} shipments")

                # إرسال إشعار
                batch.message_post(
                    body=f"""
                    <b>Batch Auto-Created</b><br/>
                    Company: {company.name}<br/>
                    Shipments: {len(shipments)}<br/>
                    Total COD: {sum(shipments.mapped('cod_amount')):.2f} EGP<br/>
                    Expected Amount: {batch.expected_net_amount:.2f} EGP
                    """,
                    subject="Auto-Created COD Batch"
                )
            except Exception as e:
                _logger.error(f"Error creating batch for {company.name}: {str(e)}")
                continue

        _logger.info(f"Auto batch creation completed. Created {created_batches} batches.")
        return True

    @api.model
    def check_and_create_overdue_batches(self, days_threshold=7):
        """إنشاء batches للشحنات المتأخرة"""
        from datetime import timedelta

        cutoff_date = fields.Date.today() - timedelta(days=days_threshold)

        # البحث عن الشحنات المتأخرة
        overdue_shipments = self.env['shipment.order'].search([
            ('payment_method', '=', 'cod'),
            ('cod_status', '=', 'collected_at_courier'),
            ('state', '=', 'delivered'),
            ('cod_collected_date', '<=', cutoff_date)
        ])

        # تجميع حسب شركة الشحن
        company_shipments = {}
        for shipment in overdue_shipments:
            company = shipment.shipping_company_id
            if company:
                if company not in company_shipments:
                    company_shipments[company] = self.env['shipment.order']
                company_shipments[company] |= shipment

        created_count = 0
        # إنشاء batch لكل شركة
        for company, shipments in company_shipments.items():
            # تحقق من عدم وجود هذه الشحنات في batch آخر
            already_in_batch = self.env['cod.batch'].search([
                ('shipment_ids', 'in', shipments.ids),
                ('state', '!=', 'cancelled')
            ])

            # فلتر الشحنات غير الموجودة في batches
            available_shipments = shipments
            for batch in already_in_batch:
                available_shipments = available_shipments - batch.shipment_ids

            if available_shipments:
                batch = self.create({
                    'shipping_company_id': company.id,
                    'collection_date': fields.Date.today(),
                    'shipment_ids': [(6, 0, available_shipments.ids)],
                    'auto_created': True,
                    'notes': f'Auto-created for overdue shipments (>{days_threshold} days)'
                })
                created_count += 1

                batch.message_post(
                    body=f"""
                    <b>Overdue Batch Created</b><br/>
                    Reason: Shipments overdue > {days_threshold} days<br/>
                    Shipments Count: {len(available_shipments)}<br/>
                    Total Amount: {sum(available_shipments.mapped('cod_amount')):.2f} EGP
                    """,
                    subject="Overdue COD Batch"
                )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Created {created_count} overdue batches'),
                'type': 'success',
            }
        }
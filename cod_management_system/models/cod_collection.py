# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class CODCollection(models.Model):
    """نموذج تتبع استحقاقات COD"""
    _name = 'cod.collection'
    _description = 'COD Collection Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'expected_settlement_date desc, id desc'

    # ===== الحقول الأساسية =====
    display_name = fields.Char(
        string='Reference',
        compute='_compute_display_name',
        store=True
    )

    shipment_id = fields.Many2one(
        'shipment.order',
        string='Shipment',
        required=True,
        ondelete='cascade',
        tracking=True,
        domain=[('payment_method', '=', 'cod')]
    )

    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        related='shipment_id.shipping_company_id',
        store=True,
        readonly=True
    )

    sender_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='shipment_id.sender_id',
        store=True,
        readonly=True
    )

    # ===== المبالغ المالية =====
    cod_amount = fields.Float(
        string='COD Amount',
        required=True,
        tracking=True,
        help='Original COD amount to be collected from recipient'
    )

    shipping_cost = fields.Float(
        string='Shipping Cost',
        help='Shipping cost if included in COD'
    )

    # إضافة الحقول المفقودة
    product_value = fields.Float(
        string='Product Value',
        help='Value of products'
    )

    shipping_paid_by = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'COD')
    ], string='Shipping Paid By',
        default='cod'
    )

    cod_commission = fields.Float(
        string='COD Commission',
        compute='_compute_cod_commission',
        store=True,
        tracking=True,
        help='COD commission for the shipping company'
    )

    total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_amounts',
        store=True,
        help='Total deductions from COD amount'
    )

    customer_refund_amount = fields.Float(
        string='Customer Refund',
        compute='_compute_amounts',
        store=True,
        help='Amount to refund to customer if any'
    )

    commission_amount = fields.Float(
        string='Commission',
        compute='_compute_cod_commission',
        store=True,
        tracking=True,
        help='Commission for the shipping company (alias for cod_commission)'
    )

    net_amount = fields.Float(
        string='Net Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True,
        help='Amount to be received after commission'
    )

    # ===== الحالات =====
    collection_state = fields.Selection([
        ('pending', 'Pending Delivery'),
        ('delivered', 'Delivered'),
        ('collected', 'Collected by Company'),
        ('in_settlement', 'In Settlement'),
        ('settled', 'Settled'),
        ('reconciled', 'Reconciled'),
        ('disputed', 'Disputed'),
        ('cancelled', 'Cancelled')
    ], string='Status',
        default='pending',
        required=True,
        tracking=True,
        help='Current status of the COD collection'
    )

    # ===== التواريخ =====
    order_date = fields.Datetime(
        string='Order Date',
        related='shipment_id.create_date',
        store=True,
        readonly=True
    )

    delivered_date = fields.Datetime(
        string='Delivered Date',
        tracking=True
    )

    collected_date = fields.Datetime(
        string='Collection Date',
        tracking=True,
        help='Date when shipping company collected from recipient'
    )

    expected_settlement_date = fields.Date(
        string='Expected Settlement',
        compute='_compute_expected_settlement_date',
        store=True,
        help='Expected date for settlement with shipping company'
    )

    actual_settlement_date = fields.Date(
        string='Actual Settlement',
        tracking=True
    )

    # ===== الربط بالتسويات =====
    settlement_batch_id = fields.Many2one(
        'cod.settlement.batch',
        string='Settlement Batch',
        tracking=True,
        ondelete='set null'
    )

    is_in_batch = fields.Boolean(
        string='In Batch',
        compute='_compute_is_in_batch',
        store=True
    )

    # ===== معلومات الدفع =====
    payment_reference = fields.Char(
        string='Payment Reference',
        help='Bank transfer or payment reference'
    )

    payment_method_used = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('wallet', 'E-Wallet')
    ], string='Payment Method')

    # ===== حقول إضافية =====
    is_disputed = fields.Boolean(
        string='Disputed',
        default=False,
        tracking=True
    )

    dispute_reason = fields.Text(
        string='Dispute Reason'
    )

    dispute_resolution = fields.Text(
        string='Dispute Resolution'
    )

    notes = fields.Text(
        string='Notes'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )

    # ===== حقول محسوبة للمتابعة =====
    days_since_delivery = fields.Integer(
        string='Days Since Delivery',
        compute='_compute_days_tracking',
        store=False
    )

    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_days_tracking',
        store=False
    )

    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_days_tracking',
        store=False
    )

    shipping_company_total_cost = fields.Float(
        string='Shipping Company Total Cost',
        compute='_compute_amounts',
        store=True,
        help='Total cost charged by shipping company (shipping + COD fee + insurance + pickup)'
    )

    # الصافي من شركة الشحن
    net_from_shipping = fields.Float(
        string='Net from Shipping Company',
        compute='_compute_amounts',
        store=True,
        help='Amount to receive from shipping company after their deductions'
    )

    # تكلفة شركتك
    our_company_cost = fields.Float(
        string='Our Company Cost',
        compute='_compute_amounts',
        store=True,
        help='Our company service cost'
    )

    # الصافي النهائي لك
    final_net_profit = fields.Float(
        string='Final Net Profit',
        compute='_compute_amounts',
        store=True,
        help='Final profit after all deductions'
    )

    customer_return_amount = fields.Float(
        string='Amount to Return to Customer',
        compute='_compute_financial_amounts',
        store=True,
        help='Amount to return to customer after deducting your profit'
    )

    # ربح الشركة (شركتك)
    company_profit = fields.Float(
        string='Your Company Profit',
        compute='_compute_financial_amounts',
        store=True,
        help='Your company profit from this transaction'
    )

    # صافي من شركة الشحن
    net_from_shipping_company = fields.Float(
        string='Net from Shipping Company',
        compute='_compute_financial_amounts',
        store=True,
        help='Amount received from shipping company after their deductions'
    )

    # ===== Compute Methods =====

    @api.depends('cod_amount', 'shipment_id.shipping_cost', 'shipment_id.total_company_cost',
                 'shipment_id.cod_fee_amount', 'shipment_id.insurance_fee_amount',
                 'shipment_id.pickup_fee', 'shipment_id.base_shipping_cost',
                 'shipment_id.weight_shipping_cost')
    def _compute_financial_amounts(self):
        """حساب المبالغ المالية بطريقة صحيحة"""
        for record in self:
            if record.shipment_id:
                shipment = record.shipment_id

                # 1️⃣ حساب إجمالي تكاليف شركة الشحن
                total_shipping_costs = (
                        (shipment.base_shipping_cost or 0) +
                        (shipment.weight_shipping_cost or 0) +
                        (shipment.cod_fee_amount or 0) +
                        (shipment.insurance_fee_amount or 0) +
                        (shipment.pickup_fee or 0)
                )

                # 2️⃣ الصافي من شركة الشحن
                record.net_from_shipping_company = record.cod_amount - total_shipping_costs

                # 3️⃣ ربح شركتك (المبلغ اللي انت كشركة هتاخده)
                record.company_profit = shipment.total_company_cost or 0

                # 4️⃣ المبلغ المرتجع للعميل
                record.customer_return_amount = record.net_from_shipping_company - record.company_profit

                # للتوافق مع الحقول القديمة
                record.net_amount = record.net_from_shipping_company
            else:
                record.net_from_shipping_company = record.cod_amount
                record.company_profit = 0
                record.customer_return_amount = record.cod_amount
                record.net_amount = record.cod_amount

    @api.depends('shipment_id.order_number', 'cod_amount')
    def _compute_display_name(self):
        """حساب اسم العرض"""
        for record in self:
            if record.shipment_id:
                record.display_name = f"{record.shipment_id.order_number} - {record.cod_amount:.2f} EGP"
            else:
                record.display_name = f"COD - {record.cod_amount:.2f} EGP"

    @api.depends('cod_amount', 'shipping_company_id', 'shipping_company_id.cod_cash_percentage', 'shipping_paid_by')
    def _compute_cod_commission(self):
        """حساب عمولة COD فقط (بدون تكلفة الشحن)"""
        for record in self:
            if record.shipping_company_id and record.cod_amount > 0:
                # حساب عمولة COD
                cod_base = record.cod_amount
                if record.shipping_paid_by == 'cod' and record.shipping_cost:
                    # إذا كان الشحن مدفوع COD، نخصم قيمة الشحن من الأساس لحساب العمولة
                    cod_base = record.cod_amount - record.shipping_cost

                result = record.shipping_company_id.calculate_cod_fee(
                    cod_amount=cod_base,
                    payment_type='cash',
                    include_shipping_cost=False,
                    shipping_cost=0
                )
                record.cod_commission = result.get('fee_amount', 0)
                record.commission_amount = record.cod_commission  # للتوافق
            else:
                record.cod_commission = 0
                record.commission_amount = 0

    @api.depends('cod_amount', 'shipment_id.shipping_cost', 'shipment_id.total_company_cost',
                 'shipment_id.cod_fee_amount', 'shipment_id.insurance_fee_amount',
                 'shipment_id.pickup_fee')
    def _compute_amounts(self):
        """حساب المبالغ الصافية بطريقة صحيحة"""
        for record in self:
            if record.shipment_id:
                shipment = record.shipment_id

                # 1️⃣ حساب إجمالي تكاليف شركة الشحن
                record.shipping_company_total_cost = (
                        shipment.base_shipping_cost +
                        shipment.weight_shipping_cost +
                        shipment.cod_fee_amount +
                        shipment.insurance_fee_amount +
                        shipment.pickup_fee
                )

                # 2️⃣ الصافي من شركة الشحن
                # COD Amount - تكاليف شركة الشحن
                record.net_from_shipping = record.cod_amount - record.shipping_company_total_cost

                # 3️⃣ تكلفة شركتك
                record.our_company_cost = shipment.total_company_cost

                # 4️⃣ الربح النهائي
                # الصافي من شركة الشحن - تكلفة شركتك
                record.final_net_profit = record.net_from_shipping - record.our_company_cost

                # الحقول القديمة للتوافق
                record.cod_commission = shipment.cod_fee_amount
                record.commission_amount = shipment.cod_fee_amount
                record.total_deductions = record.shipping_company_total_cost
                record.net_amount = record.net_from_shipping  # للتوافق مع الكود القديم
            else:
                record.shipping_company_total_cost = 0
                record.net_from_shipping = record.cod_amount
                record.our_company_cost = 0
                record.final_net_profit = 0
                record.cod_commission = 0
                record.commission_amount = 0
                record.total_deductions = 0
                record.net_amount = record.cod_amount

    @api.depends('delivered_date', 'shipping_company_id.cod_settlement_day',
                 'shipping_company_id.cod_payment_delay_days')
    def _compute_expected_settlement_date(self):
        """حساب تاريخ التسوية المتوقع"""
        for record in self:
            if record.delivered_date and record.shipping_company_id:
                # إضافة أيام التأخير
                delay_days = record.shipping_company_id.cod_payment_delay_days or 3
                base_date = record.delivered_date + timedelta(days=delay_days)

                # حساب يوم التسوية القادم
                if record.shipping_company_id.cod_settlement_day:
                    settlement_day = int(record.shipping_company_id.cod_settlement_day)
                    # البحث عن أقرب يوم تسوية
                    days_ahead = (settlement_day - base_date.weekday()) % 7
                    if days_ahead == 0:  # نفس اليوم
                        days_ahead = 7  # الأسبوع القادم

                    record.expected_settlement_date = base_date + timedelta(days=days_ahead)
                else:
                    record.expected_settlement_date = base_date
            else:
                record.expected_settlement_date = False

    @api.depends('settlement_batch_id')
    def _compute_is_in_batch(self):
        """تحديد إذا كان في دفعة تسوية"""
        for record in self:
            record.is_in_batch = bool(record.settlement_batch_id)

    @api.depends('delivered_date', 'expected_settlement_date', 'collection_state')
    def _compute_days_tracking(self):
        """حساب أيام التتبع"""
        today = fields.Date.today()
        for record in self:
            # أيام منذ التسليم
            if record.delivered_date:
                delta = today - record.delivered_date.date()
                record.days_since_delivery = delta.days
            else:
                record.days_since_delivery = 0

            # أيام التأخير
            if record.expected_settlement_date and record.collection_state in ['delivered', 'collected']:
                if today > record.expected_settlement_date:
                    delta = today - record.expected_settlement_date
                    record.days_overdue = delta.days
                    record.is_overdue = True
                else:
                    record.days_overdue = 0
                    record.is_overdue = False
            else:
                record.days_overdue = 0
                record.is_overdue = False

    # ===== Action Methods =====

    def action_mark_delivered(self):
        """تحديد كتم التسليم"""
        self.ensure_one()
        if self.collection_state != 'pending':
            raise UserError(_('Only pending collections can be marked as delivered.'))

        self.write({
            'collection_state': 'delivered',
            'delivered_date': fields.Datetime.now()
        })

        # تحديث حالة الشحنة
        if self.shipment_id and self.shipment_id.state != 'delivered':
            self.shipment_id.action_deliver()

        self.message_post(
            body=_('COD shipment delivered to recipient. Amount to collect: %s EGP') % self.cod_amount,
            subject=_('Delivered')
        )

        return True

    def action_mark_collected(self):
        """تحديد كتم التحصيل من العميل"""
        self.ensure_one()
        if self.collection_state not in ['delivered', 'disputed']:
            raise UserError(_('Only delivered collections can be marked as collected.'))

        self.write({
            'collection_state': 'collected',
            'collected_date': fields.Datetime.now(),
            'is_disputed': False
        })

        self.message_post(
            body=_('COD amount collected by shipping company: %s EGP') % self.cod_amount,
            subject=_('Collected')
        )

        return True

    def action_mark_settled(self):
        """تحديد كتم التسوية"""
        self.ensure_one()
        if self.collection_state != 'in_settlement':
            raise UserError(_('Only collections in settlement can be marked as settled.'))

        self.write({
            'collection_state': 'settled',
            'actual_settlement_date': fields.Date.today()
        })

        # محاولة المطابقة المحاسبية
        self._try_auto_reconcile()

        self.message_post(
            body=_('Settlement completed. Net amount received: %s EGP') % self.net_amount,
            subject=_('Settled')
        )

        return True

    def action_mark_disputed(self):
        """تحديد كمتنازع عليه"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Mark as Disputed'),
            'res_model': 'cod.dispute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_collection_id': self.id,
            }
        }

    def action_resolve_dispute(self):
        """حل النزاع"""
        self.ensure_one()
        if not self.is_disputed:
            raise UserError(_('This collection is not disputed.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Resolve Dispute'),
            'res_model': 'cod.resolve.dispute.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_collection_id': self.id,
            }
        }

    def action_add_to_batch(self):
        """إضافة لدفعة تسوية"""
        self.ensure_one()
        if self.settlement_batch_id:
            raise UserError(_('This collection is already in a settlement batch.'))

        if self.collection_state not in ['collected', 'disputed']:
            raise UserError(_('Only collected items can be added to settlement batch.'))

        # البحث عن دفعة مفتوحة أو إنشاء جديدة
        batch = self.env['cod.settlement.batch'].search([
            ('shipping_company_id', '=', self.shipping_company_id.id),
            ('state', '=', 'draft')
        ], limit=1)

        if not batch:
            batch = self.env['cod.settlement.batch'].create({
                'shipping_company_id': self.shipping_company_id.id,
                'settlement_date': self.expected_settlement_date or fields.Date.today()
            })

        self.settlement_batch_id = batch
        self.collection_state = 'in_settlement'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Batch'),
            'res_model': 'cod.settlement.batch',
            'res_id': batch.id,
            'view_mode': 'form',
        }

    def action_remove_from_batch(self):
        """إزالة من دفعة التسوية"""
        self.ensure_one()
        if not self.settlement_batch_id:
            raise UserError(_('This collection is not in any batch.'))

        if self.settlement_batch_id.state != 'draft':
            raise UserError(_('Cannot remove from confirmed batch.'))

        self.settlement_batch_id = False
        self.collection_state = 'collected'

        return True

    def _try_auto_reconcile(self):
        """محاولة المطابقة المحاسبية التلقائية"""
        self.ensure_one()

        # TODO: تنفيذ المطابقة مع الحسابات
        # سيتم تنفيذها في المرحلة الثانية
        pass

    # ===== CRUD Methods =====

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set initial values"""
        for vals in vals_list:
            # التأكد من وجود shipment_id
            if 'shipment_id' in vals:
                shipment = self.env['shipment.order'].browse(vals['shipment_id'])
                if shipment.payment_method != 'cod':
                    raise ValidationError(_('Cannot create COD collection for non-COD shipment.'))

                # أخذ القيم من الشحنة
                vals['cod_amount'] = shipment.cod_amount
                vals['shipping_cost'] = shipment.shipping_cost if shipment.cod_includes_shipping else 0
                vals['product_value'] = shipment.total_value
                vals['shipping_paid_by'] = 'cod' if shipment.cod_includes_shipping else 'prepaid'

        return super().create(vals_list)

    def unlink(self):
        """Check before deletion"""
        for record in self:
            if record.collection_state not in ['pending', 'cancelled']:
                raise UserError(_('Cannot delete collection that is not pending or cancelled.'))
            if record.settlement_batch_id:
                raise UserError(_('Cannot delete collection that is in a settlement batch.'))

        return super().unlink()

    # ===== Constraints =====

    @api.constrains('cod_amount')
    def _check_cod_amount(self):
        """التحقق من صحة المبلغ"""
        for record in self:
            if record.cod_amount <= 0:
                raise ValidationError(_('COD amount must be greater than zero.'))

    _sql_constraints = [
        ('unique_shipment_collection',
         'UNIQUE(shipment_id)',
         'Each shipment can have only one COD collection record.'),
    ]
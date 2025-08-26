# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ShippingOrder(models.Model):
    _name = 'shipping.order'
    _description = 'Shipping Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'order_number'

    # ===== Basic Information =====
    order_number = fields.Char(
        string='Order Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        domain=[('is_company', '=', False)]
    )

    customer_type = fields.Selection(
        related='customer_id.customer_type',
        string='Customer Type',
        store=True
    )

    order_date = fields.Datetime(
        string='Order Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )

    # ===== Sender Information =====
    sender_name = fields.Char(
        string='Sender Name',
        required=True,
        tracking=True
    )

    sender_phone = fields.Char(
        string='Sender Phone',
        required=True,
        tracking=True
    )

    sender_email = fields.Char(
        string='Sender Email',
        tracking=True
    )

    sender_governorate = fields.Many2one(
        'res.country.state',
        string='Sender Governorate',
        domain="[('country_id.code', '=', 'EG')]",
        required=True
    )

    sender_city = fields.Char(
        string='Sender City',
        required=True
    )

    sender_address = fields.Text(
        string='Sender Address',
        required=True
    )

    # ===== Receiver Information =====
    receiver_name = fields.Char(
        string='Receiver Name',
        required=True,
        tracking=True
    )

    receiver_phone = fields.Char(
        string='Receiver Phone',
        required=True,
        tracking=True
    )

    receiver_email = fields.Char(
        string='Receiver Email',
        tracking=True
    )

    receiver_governorate = fields.Many2one(
        'res.country.state',
        string='Receiver Governorate',
        domain="[('country_id.code', '=', 'EG')]",
        required=True
    )

    receiver_city = fields.Char(
        string='Receiver City',
        required=True
    )

    receiver_address = fields.Text(
        string='Receiver Address',
        required=True
    )

    same_as_sender = fields.Boolean(
        string='Same as Sender',
        help='Check if receiver address is same as sender (for returns)'
    )

    # ===== Shipping Details (UPDATED) =====
    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        tracking=True
    )

    # NEW: Shipping service instead of type
    shipping_service_id = fields.Many2one(
        'shipping.company.service',
        string='Shipping Service',
        required=True,
        tracking=True,
        domain="[('company_id', '=', shipping_company_id), ('active', '=', True)]"
    )

    # Service details (readonly fields for display)
    service_type = fields.Selection(
        related='shipping_service_id.service_type',
        string='Service Type',
        store=True
    )

    delivery_time = fields.Char(
        related='shipping_service_id.delivery_time',
        string='Delivery Time',
        readonly=True
    )

    max_weight = fields.Float(
        related='shipping_service_id.max_weight',
        string='Max Weight (kg)',
        readonly=True
    )

    tracking_number = fields.Char(
        string='Tracking Number',
        readonly=True,
        copy=False,
        tracking=True
    )

    external_tracking_number = fields.Char(
        string='External Tracking Number',
        help='Tracking number from shipping company',
        tracking=True
    )

    # ===== Products =====
    order_line_ids = fields.One2many(
        'shipping.order.line',
        'order_id',
        string='Products'
    )

    # ===== Additional Services =====
    special_packaging = fields.Boolean(
        string='Special Packaging (+20 EGP)'
    )

    insurance = fields.Boolean(
        string='Insurance'
    )

    open_package = fields.Boolean(
        string='Open Package on Delivery (+15 EGP)'
    )

    # ===== Financial Information (UPDATED) =====
    products_value = fields.Float(
        string='Products Value',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    base_shipping_cost = fields.Float(
        string='Base Shipping Cost',
        compute='_compute_amounts',
        store=True
    )

    weight_cost = fields.Float(
        string='Weight Cost',
        compute='_compute_amounts',
        store=True
    )

    cod_fee = fields.Float(
        string='COD Fee',
        compute='_compute_amounts',
        store=True
    )

    insurance_cost = fields.Float(
        string='Insurance Cost',
        compute='_compute_amounts',
        store=True
    )

    additional_services_cost = fields.Float(
        string='Additional Services Cost',
        compute='_compute_amounts',
        store=True
    )

    total_shipping_cost = fields.Float(
        string='Total Shipping Cost',
        compute='_compute_amounts',
        store=True
    )

    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('credit', 'Credit Account')
    ], string='Payment Method', required=True, default='prepaid', tracking=True)

    # ===== Status =====
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('picked', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, index=True)

    delivery_date = fields.Datetime(
        string='Delivery Date',
        tracking=True
    )

    expected_delivery_date = fields.Date(
        string='Expected Delivery Date',
        compute='_compute_expected_delivery',
        store=True
    )

    # ===== Notes =====
    internal_notes = fields.Text(
        string='Internal Notes'
    )

    delivery_notes = fields.Text(
        string='Delivery Notes'
    )

    # ===== Computed Fields for Analysis =====
    total_weight = fields.Float(
        string='Total Weight (kg)',
        compute='_compute_total_weight',
        store=True
    )

    products_count = fields.Integer(
        string='Products Count',
        compute='_compute_products_count',
        store=True
    )

    loyalty_discount = fields.Float(
        string='Loyalty Discount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    special_discount = fields.Float(
        string='Special Discount',
        compute='_compute_amounts',
        store=True,
        tracking=True
    )

    points_earned = fields.Integer(
        string='Points Earned',
        readonly=True,
        tracking=True
    )

    applied_discount_ids = fields.Many2many(
        'customer.discount',
        string='Applied Discounts',
        readonly=True
    )

    # ===== Accounting Fields =====
    invoice_id = fields.Many2one(
        'account.move',
        string='Customer Invoice',
        readonly=True,
        copy=False
    )

    invoice_state = fields.Selection([
        ('not_invoiced', 'Not Invoiced'),
        ('invoiced', 'Invoiced'),
        ('paid', 'Paid'),
    ], string='Invoice Status', default='not_invoiced', tracking=True)

    vendor_bill_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        readonly=True,
        copy=False
    )

    vendor_bill_state = fields.Selection([
        ('not_billed', 'Not Billed'),
        ('billed', 'Billed'),
        ('paid', 'Paid'),
    ], string='Bill Status', default='not_billed', tracking=True)

    # تكلفة الشحن الفعلية من شركة الشحن
    actual_shipping_cost = fields.Float(
        string='Actual Shipping Cost',
        help='Real cost from shipping company'
    )

    profit_margin = fields.Float(
        string='Profit Margin',
        compute='_compute_profit_margin',
        store=True
    )

    # للـ COD
    cod_collected = fields.Float(
        string='COD Amount Collected',
        help='Total amount collected by shipping company'
    )

    cod_settled = fields.Boolean(
        string='COD Settled',
        default=False
    )

    @api.depends('total_shipping_cost', 'actual_shipping_cost')
    def _compute_profit_margin(self):
        for order in self:
            if order.actual_shipping_cost > 0:
                order.profit_margin = order.total_shipping_cost - order.actual_shipping_cost
            else:
                # حساب تقديري من الـ service
                if order.shipping_service_id:
                    estimated_cost = (
                            order.shipping_service_id.base_price +
                            (order.shipping_service_id.price_per_kg * order.total_weight)
                    )
                    if order.payment_method == 'cod':
                        estimated_cost += order.shipping_service_id.cod_fee
                    if order.insurance:
                        estimated_cost += (order.products_value * order.shipping_service_id.insurance_rate / 100)

                    order.actual_shipping_cost = estimated_cost
                    order.profit_margin = order.total_shipping_cost - estimated_cost
                else:
                    order.profit_margin = 0

    def create_customer_invoice(self):
        """Create invoice for shipping services only"""
        self.ensure_one()

        if self.invoice_id:
            raise UserError(_('Invoice already created for this order'))

        # إنشاء الفاتورة
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.customer_id.id,
            'invoice_date': fields.Date.today(),
            'ref': f'Shipping Order: {self.order_number}',
            'invoice_line_ids': []
        }

        # سطور الفاتورة - خدمات الشحن فقط
        lines = []

        # 1. خدمة الشحن الأساسية
        shipping_line = {
            'name': f'Shipping Service - {self.shipping_service_id.name}',
            'quantity': 1,
            'price_unit': self.base_shipping_cost + self.weight_cost,
        }
        lines.append((0, 0, shipping_line))

        # 2. رسوم COD (إن وجدت)
        if self.cod_fee > 0:
            cod_line = {
                'name': 'Cash on Delivery Fee',
                'quantity': 1,
                'price_unit': self.cod_fee,
            }
            lines.append((0, 0, cod_line))

        # 3. التأمين (إن وجد)
        if self.insurance_cost > 0:
            insurance_line = {
                'name': f'Insurance ({self.shipping_service_id.insurance_rate}% of {self.products_value} EGP)',
                'quantity': 1,
                'price_unit': self.insurance_cost,
            }
            lines.append((0, 0, insurance_line))

        # 4. خدمات إضافية
        if self.additional_services_cost > 0:
            additional_line = {
                'name': 'Additional Services (Special Packaging, etc.)',
                'quantity': 1,
                'price_unit': self.additional_services_cost,
            }
            lines.append((0, 0, additional_line))

        # 5. خصومات (كسطور سالبة)
        if self.loyalty_discount > 0:
            discount_line = {
                'name': 'Loyalty Discount',
                'quantity': 1,
                'price_unit': -self.loyalty_discount,
            }
            lines.append((0, 0, discount_line))

        if self.special_discount > 0:
            special_line = {
                'name': 'Special Customer Discount',
                'quantity': 1,
                'price_unit': -self.special_discount,
            }
            lines.append((0, 0, special_line))

        invoice_vals['invoice_line_ids'] = lines

        # إنشاء الفاتورة
        invoice = self.env['account.move'].create(invoice_vals)

        # ربط الفاتورة بالطلب
        self.invoice_id = invoice
        self.invoice_state = 'invoiced'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_invoice(self):
        """View customer invoice"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice created yet'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


    @api.onchange('shipping_company_id')
    def _onchange_shipping_company(self):
        """Clear service when company changes"""
        self.shipping_service_id = False

        # Set default service if company has only one active service
        if self.shipping_company_id:
            services = self.env['shipping.company.service'].search([
                ('company_id', '=', self.shipping_company_id.id),
                ('active', '=', True)
            ])
            if len(services) == 1:
                self.shipping_service_id = services[0]

    @api.constrains('total_weight', 'shipping_service_id')
    def _check_weight_limit(self):
        """Check if weight exceeds service limit"""
        for order in self:
            if order.shipping_service_id and order.total_weight:
                if order.total_weight > order.shipping_service_id.max_weight:
                    raise ValidationError(_(
                        'Total weight (%.2f kg) exceeds maximum weight limit (%.2f kg) for %s service.'
                    ) % (order.total_weight, order.shipping_service_id.max_weight, order.shipping_service_id.name))


    @api.depends('order_line_ids.subtotal', 'shipping_service_id', 'total_weight',
                 'payment_method', 'insurance', 'special_packaging', 'open_package',
                 'customer_id', 'customer_id.customer_profile_id.loyalty_tier_id')
    def _compute_amounts(self):
        for order in self:
            # Products value
            order.products_value = sum(order.order_line_ids.mapped('subtotal'))

            # Shipping costs calculation
            if order.shipping_service_id:
                service = order.shipping_service_id

                # Base shipping cost
                order.base_shipping_cost = service.base_price

                # Weight cost
                order.weight_cost = service.price_per_kg * order.total_weight

                # COD fee (only if payment method is COD)
                if order.payment_method == 'cod':
                    order.cod_fee = service.cod_fee
                else:
                    order.cod_fee = 0

                # Insurance cost (percentage of products value)
                if order.insurance:
                    order.insurance_cost = (service.insurance_rate * order.products_value) / 100
                else:
                    order.insurance_cost = 0

                # Additional services
                additional = 0
                if order.special_packaging:
                    additional += 20.0
                if order.open_package:
                    additional += 15.0

                order.additional_services_cost = additional

                # Total shipping cost
                order.total_shipping_cost = (
                        order.base_shipping_cost +
                        order.weight_cost +
                        order.cod_fee +
                        order.insurance_cost +
                        order.additional_services_cost
                )
            else:
                # No service selected
                order.base_shipping_cost = 0
                order.weight_cost = 0
                order.cod_fee = 0
                order.insurance_cost = 0
                order.additional_services_cost = 0
                order.total_shipping_cost = 0

            # Calculate customer discounts
            loyalty_discount = 0.0
            special_discount = 0.0

            if order.customer_id:
                # 1. Loyalty tier discount
                if order.customer_id.customer_profile_id:
                    profile = order.customer_id.customer_profile_id
                    if profile.loyalty_tier_id and profile.loyalty_tier_id.discount_percentage:
                        loyalty_discount = order.products_value * (profile.loyalty_tier_id.discount_percentage / 100)

                # 2. Special customer discounts
                valid_discounts = order.customer_id.customer_discount_ids.filtered(
                    lambda d: d._is_valid() and order.products_value >= d.min_order_amount
                )

                for discount in valid_discounts:
                    if discount.discount_type == 'percentage':
                        disc_amount = order.products_value * (discount.discount_value / 100)
                        if discount.max_discount_amount:
                            disc_amount = min(disc_amount, discount.max_discount_amount)
                    else:
                        disc_amount = min(discount.discount_value, order.products_value)

                    special_discount += disc_amount

            order.loyalty_discount = loyalty_discount
            order.special_discount = special_discount

            # Total amount (products + shipping - discounts)
            order.total_amount = (
                    order.products_value +
                    order.total_shipping_cost -
                    order.loyalty_discount -
                    order.special_discount
            )

            # Ensure total is not negative
            if order.total_amount < 0:
                order.total_amount = 0

    @api.depends('order_line_ids.weight')
    def _compute_total_weight(self):
        for order in self:
            order.total_weight = sum(order.order_line_ids.mapped('weight'))

    @api.depends('order_line_ids')
    def _compute_products_count(self):
        for order in self:
            order.products_count = len(order.order_line_ids)

    @api.depends('order_date', 'shipping_service_id')
    def _compute_expected_delivery(self):
        for order in self:
            if order.order_date and order.shipping_service_id:
                # Parse delivery time from service
                delivery_time = order.shipping_service_id.delivery_time

                # Simple parsing based on common patterns
                if 'Same Day' in delivery_time:
                    days = 0
                elif 'Next' in delivery_time or '1' in delivery_time:
                    days = 1
                elif '2' in delivery_time:
                    days = 2
                elif '3' in delivery_time:
                    days = 3
                elif '5' in delivery_time:
                    days = 5
                else:
                    days = 4  # Default

                order.expected_delivery_date = order.order_date.date() + timedelta(days=days)
            else:
                order.expected_delivery_date = False

    @api.onchange('same_as_sender')
    def _onchange_same_as_sender(self):
        if self.same_as_sender:
            self.receiver_name = self.sender_name
            self.receiver_phone = self.sender_phone
            self.receiver_email = self.sender_email
            self.receiver_governorate = self.sender_governorate
            self.receiver_city = self.sender_city
            self.receiver_address = self.sender_address

    @api.model
    def create(self, vals):
        if vals.get('order_number', _('New')) == _('New'):
            vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or _('New')

        result = super(ShippingOrder, self).create(vals)

        # إنشاء customer profile إذا لم يكن موجود
        if result.customer_id and not result.customer_id.customer_profile_id:
            result.customer_id.is_shipping_customer = True
            profile = self.env['customer.profile'].create({
                'customer_id': result.customer_id.id
            })
            result.customer_id.customer_profile_id = profile

        # Update customer profile
        result._update_customer_profile()

        # Create product analysis records
        result._create_product_analysis()

        return result

    def _calculate_loyalty_points(self):
        """حساب النقاط بناءً على القواعد المعرّفة"""
        for order in self:
            if not order.customer_id.customer_profile_id:
                continue

            profile = order.customer_id.customer_profile_id
            total_points = 0

            # 1. نقاط حسب قيمة الطلب
            amount_rules = self.env['loyalty.points.rule'].search([
                ('rule_type', '=', 'order_amount'),
                ('active', '=', True),
                ('min_order_amount', '<=', order.total_amount)
            ])
            for rule in amount_rules:
                points = order.total_amount * rule.points_per_currency
                total_points += points

            # 2. نقاط حسب نوع الشحن
            shipping_rules = self.env['loyalty.points.rule'].search([
                ('rule_type', '=', 'shipping_type'),
                ('shipping_type', '=', order.service_type),
                ('active', '=', True)
            ])
            for rule in shipping_rules:
                total_points += rule.shipping_bonus_points

            # 3. نقاط حسب طريقة الدفع
            payment_rules = self.env['loyalty.points.rule'].search([
                ('rule_type', '=', 'payment_method'),
                ('payment_method', '=', order.payment_method),
                ('active', '=', True)
            ])
            for rule in payment_rules:
                total_points += rule.payment_bonus_points

            # 4. نقاط أول طلب
            if profile.total_orders == 0:
                first_order_rules = self.env['loyalty.points.rule'].search([
                    ('rule_type', '=', 'first_order'),
                    ('active', '=', True)
                ])
                for rule in first_order_rules:
                    total_points += rule.fixed_points

            # 5. نقاط حسب فئات المنتجات
            for line in order.order_line_ids:
                if line.category_id:
                    cat_rules = self.env['loyalty.points.rule'].search([
                        ('rule_type', '=', 'product_category'),
                        ('category_id', '=', line.category_id.id),
                        ('active', '=', True)
                    ])
                    for rule in cat_rules:
                        line_points = (line.subtotal * rule.points_per_currency * rule.category_multiplier)
                        total_points += line_points

            # حفظ النقاط المكتسبة
            order.points_earned = int(total_points)

            # إضافة النقاط للعميل
            if total_points > 0:
                profile.add_loyalty_points(
                    int(total_points),
                    f'Order {order.order_number}'
                )
                # ربط السجل بالطلب
                history = self.env['loyalty.points.history'].search([
                    ('profile_id', '=', profile.id)
                ], limit=1, order='date desc')
                if history:
                    history.order_id = order.id

    def _apply_customer_discounts(self):
        """تطبيق خصومات العميل على الطلب"""
        for order in self:
            loyalty_discount = 0.0
            special_discount = 0.0

            if order.customer_id:
                # 1. خصم مستوى الولاء
                if order.customer_id.customer_profile_id:
                    profile = order.customer_id.customer_profile_id
                    if profile.loyalty_tier_id and profile.loyalty_tier_discount:
                        loyalty_discount = order.products_value * (profile.loyalty_tier_discount / 100)

                # 2. الخصومات الخاصة
                valid_discounts = order._get_applicable_discounts()
                for discount in valid_discounts:
                    disc_amount = discount.calculate_discount(order.products_value)
                    special_discount += disc_amount
                    # تحديث مرات الاستخدام سيتم في action_confirm

            order.loyalty_discount = loyalty_discount
            order.special_discount = special_discount

    def _get_applicable_discounts(self):
        """جلب الخصومات المتاحة للعميل"""
        self.ensure_one()
        if not self.customer_id:
            return self.env['customer.discount']

        return self.customer_id.customer_discount_ids.filtered(lambda d: d._is_valid())


    def write(self, vals):
        result = super(ShippingOrder, self).write(vals)

        if 'state' in vals and vals['state'] == 'delivered':
            self.delivery_date = fields.Datetime.now()
            self._update_customer_metrics()

        return result

    def _update_customer_profile(self):
        """Update customer profile with new order data"""
        for order in self:
            if order.customer_id:
                # Set customer as shipping customer
                if not order.customer_id.is_shipping_customer:
                    order.customer_id.is_shipping_customer = True

                # Get or create profile
                profile = self.env['customer.profile'].search([
                    ('customer_id', '=', order.customer_id.id)
                ], limit=1)

                if not profile:
                    profile = self.env['customer.profile'].create({
                        'customer_id': order.customer_id.id
                    })

                # Update statistics
                if hasattr(profile, 'update_statistics'):
                    profile.update_statistics()

    def _create_product_analysis(self):
        """Create product analysis records for ordered products"""
        for order in self:
            for line in order.order_line_ids:
                # تأكد من وجود فئة افتراضية
                if not line.category_id:
                    default_category = self.env['product.category'].search([], limit=1)
                    if not default_category:
                        default_category = self.env['product.category'].create({
                            'name': 'General',
                            'complete_name': 'General'
                        })
                    line.category_id = default_category

                # إنشاء سجل التحليل
                vals = {
                    'product_name': line.product_name or 'Unknown Product',
                    'category_id': line.category_id.id,
                    'quantity': line.quantity,
                    'unit_price': line.unit_price,
                    'order_id': order.id,
                    'customer_id': order.customer_id.id,
                    'shipping_date': order.order_date,
                    'governorate_id': order.receiver_governorate.id if order.receiver_governorate else False,
                    'city': order.receiver_city or 'Unknown',
                }

                # إضافة الحقول الاختيارية
                if line.brand:
                    vals['brand'] = line.brand

                if line.subcategory_id:
                    vals['subcategory_id'] = line.subcategory_id.id

                try:
                    self.env['product.analysis'].create(vals)
                    _logger.info(f"Created product analysis for {line.product_name}")
                except Exception as e:
                    _logger.error(f"Error creating product analysis: {e}")
                    # Continue with next line instead of stopping
                    continue

    def _update_customer_metrics(self):
        """Update customer metrics when order is delivered"""
        for order in self:
            if order.customer_id and order.customer_id.customer_profile_id:
                profile = order.customer_id.customer_profile_id
                if hasattr(profile, 'update_statistics'):
                    profile.update_statistics()

    # ===== Action Methods =====
    def action_view_customer_profile(self):
        """View customer profile"""
        self.ensure_one()
        profile = self.env['customer.profile'].search([
            ('customer_id', '=', self.customer_id.id)
        ], limit=1)

        if not profile:
            profile = self.env['customer.profile'].create({
                'customer_id': self.customer_id.id
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Profile'),
            'res_model': 'customer.profile',
            'view_mode': 'form',
            'res_id': profile.id,
            'target': 'current'
        }

    def action_view_product_analysis(self):
        """View product analysis for this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product Analysis'),
            'res_model': 'product.analysis',
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id}
        }

    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('Only draft orders can be confirmed.'))

            # Validate order lines
            if not order.order_line_ids:
                raise ValidationError(_('Please add at least one product.'))

            # Validate shipping service
            if not order.shipping_service_id:
                raise ValidationError(_('Please select a shipping service.'))

            # تحديث مرات استخدام الخصومات
            for discount in order._get_applicable_discounts():
                discount.times_used += 1
                order.applied_discount_ids = [(4, discount.id)]

            # حساب وإضافة نقاط الولاء
            order._calculate_loyalty_points()

            # Send to shipping company API
            order._send_to_shipping_company()

            order.state = 'confirmed'

            # Send confirmation email
            order._send_confirmation_email()

    def action_cancel(self):
        for order in self:
            if order.state in ['delivered', 'returned']:
                raise UserError(_('Cannot cancel delivered or returned orders.'))
            order.state = 'cancelled'

    def action_set_delivered(self):
        for order in self:
            order.state = 'delivered'
            order.delivery_date = fields.Datetime.now()

            # تحديث إحصائيات العميل
            order._update_customer_metrics()

            # تحديث profile statistics
            if order.customer_id.customer_profile_id:
                order.customer_id.customer_profile_id.update_statistics()

    def action_return(self):
        for order in self:
            if order.state != 'delivered':
                raise UserError(_('Only delivered orders can be returned.'))
            order.state = 'returned'

    def _send_to_shipping_company(self):
        """Mark order as sent to shipping company"""
        for order in self:
            # Generate a dummy tracking number for now
            order.tracking_number = f"TRK-{order.order_number}"
            _logger.info(f"Order {order.order_number} sent to {order.shipping_company_id.name}")

    def _send_confirmation_email(self):
        """Send confirmation email to customer"""
        for order in self:
            _logger.info(f"Confirmation email sent for order {order.order_number}")

    def action_print_label(self):
        """Print shipping label"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Shipping Label'),
                'message': _('Shipping label will be printed'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_track_shipment(self):
        """Open tracking URL or show tracking info"""
        for order in self:
            if order.tracking_number:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Tracking Number'),
                        'message': f'Tracking Number: {order.tracking_number}',
                        'type': 'info',
                        'sticky': False,
                    }
                }
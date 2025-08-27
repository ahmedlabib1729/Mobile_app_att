# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class ShipmentOrder(models.Model):
    _name = 'shipment.order'
    _description = 'Shipment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'order_number'

    # الرقم المرجعي
    order_number = fields.Char(
        string='Order Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True
    )

    # معلومات المرسل (العميل)
    sender_id = fields.Many2one(
        'res.partner',
        string='Sender (Customer)',
        required=True,
        tracking=True
    )
    sender_name = fields.Char(
        related='sender_id.name',
        string='Sender Name',
        readonly=True
    )
    sender_phone = fields.Char(
        related='sender_id.phone',
        string='Sender Phone',
        readonly=True
    )
    sender_mobile = fields.Char(
        related='sender_id.mobile',
        string='Sender Mobile',
        readonly=True
    )
    sender_email = fields.Char(
        related='sender_id.email',
        string='Sender Email',
        readonly=True
    )
    sender_address = fields.Text(
        string='Pickup Address',
        required=True,
        help='Full address for pickup location'
    )
    sender_city = fields.Char(string='Sender City')
    sender_state_id = fields.Many2one('res.country.state', string='Sender State')
    sender_country_id = fields.Many2one('res.country', string='Sender Country')
    sender_zip = fields.Char(string='Sender ZIP')

    # معلومات المرسل إليه
    recipient_id = fields.Many2one(
        'res.partner',
        string='Recipient',
        required=True,
        tracking=True
    )
    recipient_name = fields.Char(
        string='Recipient Name',
        required=True
    )
    recipient_phone = fields.Char(
        string='Recipient Phone',
        required=True
    )
    recipient_mobile = fields.Char(
        string='Recipient Mobile'
    )
    recipient_email = fields.Char(
        string='Recipient Email'
    )
    recipient_address = fields.Text(
        string='Delivery Address',
        required=True,
        help='Full address for delivery location'
    )
    recipient_city = fields.Char(string='Recipient City', required=True)
    recipient_state_id = fields.Many2one('res.country.state', string='Recipient State')
    recipient_country_id = fields.Many2one('res.country', string='Recipient Country', required=True)
    recipient_zip = fields.Char(string='Recipient ZIP')

    # تفاصيل الشحن
    pickup_date = fields.Datetime(
        string='Pickup Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    expected_delivery = fields.Datetime(
        string='Expected Delivery',
        tracking=True
    )
    actual_delivery = fields.Datetime(
        string='Actual Delivery',
        tracking=True
    )

    # المنتجات (عدة منتجات)
    shipment_line_ids = fields.One2many(
        'shipment.order.line',
        'shipment_id',
        string='Products',
        required=True
    )

    # الأوزان والأبعاد الإجمالية
    total_weight = fields.Float(
        string='Total Weight (KG)',
        compute='_compute_totals',
        store=True,
        tracking=True
    )
    total_volume = fields.Float(
        string='Total Volume (m³)',
        compute='_compute_totals',
        store=True
    )
    total_value = fields.Float(
        string='Total Products Value',
        compute='_compute_totals',
        store=True
    )
    package_count = fields.Integer(
        string='Number of Packages',
        default=1,
        required=True
    )

    # شركة الشحن والأسعار
    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        tracking=True,
        help='Select the shipping company'
    )

    shipping_service_id = fields.Many2one(
        'shipping.company.service',
        string='Shipping Service',
        domain="[('company_id', '=', shipping_company_id), ('active', '=', True)]",
        tracking=True,
        help='Select the specific service from the shipping company'
    )

    base_shipping_cost = fields.Float(
        string='Base Cost',
        store=True,
        readonly=False,
        help='Base shipping cost from the service'
    )

    weight_shipping_cost = fields.Float(
        string='Weight Cost',
        store=True,
        readonly=False,
        help='Cost based on weight'
    )

    cod_fee_amount = fields.Float(
        string='COD Fee',
        store=True,
        readonly=False,
        help='Cash on delivery fee'
    )

    insurance_fee_amount = fields.Float(
        string='Insurance Fee',
        store=True,
        readonly=False,
        help='Insurance fee amount'
    )

    # التكلفة الإجمالية
    shipping_cost = fields.Float(
        string='Total Shipping Cost',
        compute='_compute_shipping_cost',
        store=True,
        readonly=False,
        help='Total cost from shipping company',
        tracking=True
    )

    insurance_value = fields.Float(
        string='Insurance Value',
        help='Value to be insured (if different from total value)'
    )

    customer_price = fields.Float(
        string='Customer Price',
        help='Price charged to customer',
        tracking=True
    )

    profit_margin = fields.Float(
        string='Profit',
        compute='_compute_profit',
        store=True
    )

    # الحالة
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('picked', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # معلومات إضافية
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')

    tracking_number = fields.Char(
        string='Tracking Number',
        tracking=True,
        copy=False,
        readonly=True,
        index=True,
        help='Unique tracking number for this shipment'
    )

    tracking_url = fields.Char(
        string='Tracking URL',
        compute='_compute_tracking_url',
        help='URL to track this shipment'
    )

    # نوع الشحنة
    shipment_type = fields.Selection([
        ('document', 'Documents'),
        ('package', 'Package'),
        ('pallet', 'Pallet'),
        ('container', 'Container'),
        ('other', 'Other')
    ], string='Shipment Type', default='package')

    # التأمين
    insurance_required = fields.Boolean(string='Insurance Required')

    # الدفع
    payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('credit', 'Credit Account'),
        ('recipient', 'Recipient Pays')
    ], string='Payment Method', default='prepaid')

    cod_amount = fields.Float(string='COD Amount')

    # حقول للـ Smart Buttons
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count'
    )

    sender_whatsapp = fields.Char(
        string='Sender WhatsApp',
        help='WhatsApp number for quick communication'
    )

    sender_preferred_pickup_time = fields.Selection([
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 3 PM)'),
        ('late_afternoon', 'Late Afternoon (3 PM - 6 PM)'),
        ('evening', 'Evening (6 PM - 9 PM)'),
        ('anytime', 'Any Time'),
    ], string='Preferred Pickup Time', default='anytime')

    sender_pickup_notes = fields.Text(
        string='Pickup Instructions',
        help='Special instructions for pickup (floor, building, gate, etc.)'
    )

    recipient_whatsapp = fields.Char(
        string='Recipient WhatsApp',
        help='WhatsApp number for delivery coordination'
    )

    recipient_preferred_delivery_time = fields.Selection([
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 3 PM)'),
        ('late_afternoon', 'Late Afternoon (3 PM - 6 PM)'),
        ('evening', 'Evening (6 PM - 9 PM)'),
        ('anytime', 'Any Time'),
    ], string='Preferred Delivery Time', default='anytime')

    recipient_delivery_notes = fields.Text(
        string='Delivery Instructions',
        help='Special instructions for delivery (floor, building, gate, doorman name, etc.)'
    )

    recipient_alternative_phone = fields.Char(
        string='Alternative Phone',
        help='Alternative phone number if primary is not available'
    )

    # ===== حقول الرسوم الإضافية المبسطة =====
    broker_fee_ids = fields.Many2many(
        'broker.additional.fee',
        string='Additional Services',
        help='Select additional services to apply'
    )

    total_broker_fees = fields.Float(
        string='Total Additional Fees',
        compute='_compute_broker_fees',
        store=True,
        default = 0.0,
    )

    final_customer_price = fields.Float(
        string='Final Price',
        compute='_compute_final_price',
        store=True
    )

    # ===== Compute Methods =====

    @api.depends('broker_fee_ids')
    def _compute_broker_fees(self):
        """حساب مجموع الرسوم الإضافية - تأكد من الحساب الصحيح"""
        for record in self:
            if record.broker_fee_ids:
                record.total_broker_fees = sum(record.broker_fee_ids.mapped('fee_amount'))
            else:
                record.total_broker_fees = 0.0

    @api.depends('shipping_cost', 'total_broker_fees')
    def _compute_final_price(self):
        """حساب السعر النهائي"""
        for record in self:
            record.final_customer_price = record.shipping_cost + record.total_broker_fees

    @api.depends('tracking_number')
    def _compute_tracking_url(self):
        """Generate tracking URL based on tracking number"""
        for record in self:
            if record.tracking_number:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                record.tracking_url = f"{base_url}/track/{record.tracking_number}"
            else:
                record.tracking_url = False

    @api.depends('shipment_line_ids.weight', 'shipment_line_ids.quantity', 'shipment_line_ids.product_value')
    def _compute_totals(self):
        for record in self:
            record.total_weight = sum(line.total_weight for line in record.shipment_line_ids)
            record.total_volume = sum(line.volume * line.quantity for line in record.shipment_line_ids)
            record.total_value = sum(line.total_value for line in record.shipment_line_ids)

    @api.depends('base_shipping_cost', 'weight_shipping_cost', 'cod_fee_amount', 'insurance_fee_amount')
    def _compute_shipping_cost(self):
        """حساب إجمالي تكلفة الشحن"""
        for record in self:
            total = (
                    (record.base_shipping_cost or 0) +
                    (record.weight_shipping_cost or 0) +
                    (record.cod_fee_amount or 0) +
                    (record.insurance_fee_amount or 0)
            )
            record.shipping_cost = total

    @api.depends('shipping_cost', 'customer_price')
    def _compute_profit(self):
        """حساب هامش الربح"""
        for record in self:
            record.profit_margin = (record.customer_price or 0) - (record.shipping_cost or 0)

    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = 0

    # ===== Onchange Methods =====

    @api.onchange('shipping_company_id')
    def _onchange_shipping_company(self):
        """عند تغيير شركة الشحن"""
        if self.shipping_company_id:
            self.shipping_service_id = False
            default_service = self.env['shipping.company.service'].search([
                ('company_id', '=', self.shipping_company_id.id),
                ('active', '=', True),
                ('service_type', '=', 'normal')
            ], limit=1)

            if not default_service:
                default_service = self.env['shipping.company.service'].search([
                    ('company_id', '=', self.shipping_company_id.id),
                    ('active', '=', True)
                ], limit=1)

            if default_service:
                self.shipping_service_id = default_service
                self._calculate_all_fees()
        else:
            self.shipping_service_id = False
            self.base_shipping_cost = 0
            self.weight_shipping_cost = 0
            self.cod_fee_amount = 0
            self.insurance_fee_amount = 0

    @api.onchange('shipping_service_id')
    def _onchange_shipping_service(self):
        """عند تغيير الخدمة - بدون تطبيق رسوم افتراضية"""
        if self.shipping_service_id:
            self._calculate_all_fees()


            if self._context.get('auto_apply_fees', False):
                auto_fees = self.env['broker.additional.fee'].search([
                    ('active', '=', True),
                    ('auto_apply', '=', True)
                ])
                self.broker_fee_ids = [(6, 0, auto_fees.ids)]

    @api.onchange('total_weight', 'total_value', 'payment_method', 'insurance_required', 'insurance_value',
                  'cod_amount')
    def _onchange_shipping_factors(self):
        """عند تغيير أي عامل مؤثر على السعر"""
        if self.shipping_service_id:
            self._calculate_all_fees()

    @api.onchange('sender_id')
    def _onchange_sender_id(self):
        if self.sender_id:
            if self.sender_id.street:
                address_parts = []
                if self.sender_id.street:
                    address_parts.append(self.sender_id.street)
                if self.sender_id.street2:
                    address_parts.append(self.sender_id.street2)
                self.sender_address = ', '.join(address_parts)
            self.sender_city = self.sender_id.city
            self.sender_state_id = self.sender_id.state_id
            self.sender_country_id = self.sender_id.country_id
            self.sender_zip = self.sender_id.zip

            if hasattr(self.sender_id, 'whatsapp'):
                self.sender_whatsapp = self.sender_id.whatsapp
            elif self.sender_id.mobile:
                self.sender_whatsapp = self.sender_id.mobile

    @api.onchange('recipient_id')
    def _onchange_recipient_id(self):
        if self.recipient_id:
            self.recipient_name = self.recipient_id.name
            self.recipient_phone = self.recipient_id.phone
            self.recipient_mobile = self.recipient_id.mobile
            self.recipient_email = self.recipient_id.email
            if self.recipient_id.street:
                address_parts = []
                if self.recipient_id.street:
                    address_parts.append(self.recipient_id.street)
                if self.recipient_id.street2:
                    address_parts.append(self.recipient_id.street2)
                self.recipient_address = ', '.join(address_parts)
            self.recipient_city = self.recipient_id.city
            self.recipient_state_id = self.recipient_id.state_id
            self.recipient_country_id = self.recipient_id.country_id
            self.recipient_zip = self.recipient_id.zip

            if hasattr(self.recipient_id, 'whatsapp'):
                self.recipient_whatsapp = self.recipient_id.whatsapp
            elif self.recipient_id.mobile:
                self.recipient_whatsapp = self.recipient_id.mobile

    # ===== Helper Methods =====

    def _generate_tracking_number(self):
        """Generate unique tracking number for shipment"""
        for record in self:
            if not record.tracking_number:
                record.tracking_number = self.env['ir.sequence'].next_by_code('shipping.tracking')
                if not record.tracking_number:
                    import random
                    import datetime
                    today = datetime.datetime.now().strftime('%Y%m%d')
                    random_num = str(random.randint(100000, 999999))
                    record.tracking_number = f"TRK{today}{random_num}"
        return True

    def _calculate_all_fees(self):
        """دالة مركزية لحساب جميع الرسوم"""
        if not self.shipping_service_id:
            return

        service = self.shipping_service_id

        # 1. التكلفة الأساسية
        self.base_shipping_cost = service.base_price or 0

        # 2. تكلفة الوزن
        if self.total_weight > 0 and service.price_per_kg:
            self.weight_shipping_cost = service.price_per_kg * self.total_weight
        else:
            self.weight_shipping_cost = 0

        # 3. رسوم COD
        if self.payment_method == 'cod':
            cod_fee = service.cod_fee or 0

            if self.shipping_company_id and self.cod_amount > 0:
                if self.shipping_company_id.cod_commission_rate > 0:
                    cod_commission = (self.cod_amount * self.shipping_company_id.cod_commission_rate / 100)
                    cod_fee += cod_commission

                if self.shipping_company_id.cod_fixed_fee > 0:
                    cod_fee += self.shipping_company_id.cod_fixed_fee

            self.cod_fee_amount = cod_fee
        else:
            self.cod_fee_amount = 0

        # 4. رسوم التأمين
        if self.insurance_required:
            insured_amount = self.insurance_value if self.insurance_value > 0 else self.total_value

            if insured_amount > 0 and service.insurance_rate > 0:
                self.insurance_fee_amount = (insured_amount * service.insurance_rate / 100)
            else:
                self.insurance_fee_amount = 0
        else:
            self.insurance_fee_amount = 0

        self._compute_shipping_cost()

    def action_calculate_best_price(self):
        """البحث عن أفضل سعر من جميع الشركات"""
        self.ensure_one()

        if not self.total_weight:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Please add products with weights first'),
                    'type': 'warning',
                }
            }

        all_services = self.env['shipping.company.service'].search([
            ('active', '=', True),
            '|',
            ('max_weight', '>=', self.total_weight),
            ('max_weight', '=', 0)
        ])

        if not all_services:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Services Found'),
                    'message': _('No shipping services available for this weight'),
                    'type': 'warning',
                }
            }

        best_price = float('inf')
        best_service = None
        prices_list = []

        for service in all_services:
            price = service.calculate_price(
                weight=self.total_weight,
                value=self.total_value,
                cod=(self.payment_method == 'cod')
            )

            prices_list.append({
                'company': service.company_id.name,
                'service': service.name,
                'price': price
            })

            if price < best_price:
                best_price = price
                best_service = service

        if best_service:
            self.shipping_company_id = best_service.company_id
            self.shipping_service_id = best_service
            self._calculate_all_fees()

            price_details = '\n'.join([
                f"• {p['company']} - {p['service']}: {p['price']:.2f} EGP"
                for p in sorted(prices_list, key=lambda x: x['price'])[:5]
            ])

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Best Price Applied'),
                    'message': _(
                        'Best price: %.2f EGP\n'
                        'Company: %s\n'
                        'Service: %s\n\n'
                        'Top prices:\n%s'
                    ) % (best_price, best_service.company_id.name,
                         best_service.name, price_details),
                    'type': 'success',
                    'sticky': True,
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Error'),
                'message': _('Could not calculate prices'),
                'type': 'warning',
            }
        }

    def action_recalculate_fees(self):
        """زر لإعادة الحساب يدوياً"""
        self.ensure_one()
        if self.shipping_service_id:
            self._calculate_all_fees()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Shipping fees recalculated successfully'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Please select a shipping service first'),
                    'type': 'warning',
                }
            }

    # ===== CRUD Methods =====

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle sequences and fees calculation"""
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        for vals in vals_list:
            if vals.get('order_number', _('New')) == _('New'):
                vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or _('New')

        records = super(ShipmentOrder, self).create(vals_list)

        for record in records:
            if record.shipping_service_id:
                record.with_context(skip_onchange=True)._calculate_all_fees()
                record._compute_shipping_cost()

        return records if len(records) > 1 else records[0]

    def write(self, vals):
        """Override write to recalculate fees when needed"""
        shipping_trigger_fields = {
            'shipping_company_id', 'shipping_service_id',
            'total_weight', 'total_value', 'payment_method',
            'cod_amount', 'insurance_required', 'insurance_value'
        }

        needs_recalc = bool(shipping_trigger_fields & set(vals.keys()))

        result = super(ShipmentOrder, self).write(vals)

        if needs_recalc:
            for record in self:
                if record.shipping_service_id:
                    record.with_context(skip_onchange=True)._calculate_all_fees()
                    record._compute_shipping_cost()

        return result

    # ===== Action Methods =====

    def action_confirm(self):
        """Confirm the shipment and generate tracking number"""
        for record in self:
            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'confirmed'
            record.message_post(
                body=f"Shipment confirmed. Tracking Number: {record.tracking_number}",
                subject="Shipment Confirmed"
            )
        return True

    def action_pickup(self):
        """Mark shipment as picked up"""
        for record in self:
            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'picked'
            record.message_post(
                body=f"Shipment picked up. Tracking: {record.tracking_number}",
                subject="Pickup Completed"
            )
        return True

    def action_in_transit(self):
        """Mark shipment as in transit"""
        for record in self:
            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'in_transit'
            record.message_post(
                body=f"Shipment in transit. Track at: {record.tracking_url or record.tracking_number}",
                subject="In Transit"
            )
        return True

    def action_out_for_delivery(self):
        """Mark shipment as out for delivery"""
        for record in self:
            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'out_for_delivery'
            record.message_post(
                body="Shipment is out for delivery",
                subject="Out for Delivery"
            )
        return True

    def action_deliver(self):
        """Mark shipment as delivered"""
        for record in self:
            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'delivered'
            record.actual_delivery = fields.Datetime.now()
            record.message_post(
                body=f"Shipment delivered successfully at {record.actual_delivery}",
                subject="Delivered"
            )
        return True

    def action_return(self):
        """Mark shipment as returned"""
        for record in self:
            record.state = 'returned'
            record.message_post(
                body="Shipment has been returned",
                subject="Returned"
            )
        return True

    def action_cancel(self):
        """Cancel the shipment"""
        for record in self:
            record.state = 'cancelled'
            record.message_post(
                body="Shipment has been cancelled",
                subject="Cancelled"
            )
        return True

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invoices',
                'message': 'Invoice functionality will be added soon.',
                'type': 'info',
            }
        }


class ShipmentOrderLine(models.Model):
    _name = 'shipment.order.line'
    _description = 'Shipment Order Line'

    shipment_id = fields.Many2one(
        'shipment.order',
        string='Shipment',
        required=True,
        ondelete='cascade'
    )

    product_name = fields.Char(
        string='Product Description',
        required=True
    )

    category_id = fields.Many2one(
        'product.category',
        string='Category',
        required=True
    )

    subcategory_id = fields.Many2one(
        'product.subcategory',
        string='Sub Category'
    )

    brand_id = fields.Many2one(
        'product.brand',
        string='Brand'
    )

    quantity = fields.Integer(
        string='Quantity',
        default=1,
        required=True
    )

    weight = fields.Float(
        string='Weight per Unit (KG)',
        required=True
    )

    total_weight = fields.Float(
        string='Total Weight (KG)',
        compute='_compute_line_totals',
        store=True
    )

    length = fields.Float(string='Length (cm)')
    width = fields.Float(string='Width (cm)')
    height = fields.Float(string='Height (cm)')

    volume = fields.Float(
        string='Volume (m³)',
        compute='_compute_volume',
        store=True
    )

    product_value = fields.Float(
        string='Unit Value',
        required=True
    )

    total_value = fields.Float(
        string='Total Value',
        compute='_compute_line_totals',
        store=True
    )

    hs_code = fields.Char(string='HS Code')
    serial_number = fields.Char(string='Serial/Batch Number')
    fragile = fields.Boolean(string='Fragile')
    dangerous_goods = fields.Boolean(string='Dangerous Goods')
    notes = fields.Text(string='Notes')

    @api.depends('quantity', 'weight', 'product_value')
    def _compute_line_totals(self):
        for line in self:
            line.total_weight = line.quantity * line.weight
            line.total_value = line.quantity * line.product_value

    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        for line in self:
            line.volume = (line.length * line.width * line.height) / 1000000


class ProductCategory(models.Model):
    _inherit = 'product.category'

    shipment_line_ids = fields.One2many(
        'shipment.order.line',
        'category_id',
        string='Shipment Lines'
    )


class ProductSubcategory(models.Model):
    _name = 'product.subcategory'
    _description = 'Product Subcategory'

    name = fields.Char(string='Name', required=True)
    category_id = fields.Many2one('product.category', string='Main Category')
    active = fields.Boolean(string='Active', default=True)


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char(string='Brand Name', required=True)
    logo = fields.Binary(string='Logo')
    active = fields.Boolean(string='Active', default=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_shipping_company = fields.Boolean(
        string='Is Shipping Company',
        help='Check if this partner is a shipping company'
    )

    shipment_count = fields.Integer(
        string='Shipments',
        compute='_compute_shipment_count'
    )

    def _compute_shipment_count(self):
        for partner in self:
            partner.shipment_count = self.env['shipment.order'].search_count([
                '|', '|',
                ('sender_id', '=', partner.id),
                ('recipient_id', '=', partner.id),
                ('shipping_company_id', '=', partner.id)
            ])
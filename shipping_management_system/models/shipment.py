# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


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
        'res.partner',
        string='Shipping Company',
        domain=[('is_shipping_company', '=', True)],
        tracking=True
    )


    shipping_cost = fields.Float(
        string='Shipping Cost',
        help='Cost from shipping company',
        tracking=True
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
    insurance_value = fields.Float(string='Insurance Value')

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

    @api.depends('tracking_number')
    def _compute_tracking_url(self):
        """Generate tracking URL based on tracking number"""
        for record in self:
            if record.tracking_number:
                # يمكنك تخصيص هذا حسب نظام التتبع الخاص بك
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                record.tracking_url = f"{base_url}/track/{record.tracking_number}"
            else:
                record.tracking_url = False

    def _generate_tracking_number(self):
        """Generate unique tracking number for shipment"""
        for record in self:
            if not record.tracking_number:
                # Generate tracking number with format: TRK + YYYYMMDD + 6 digits
                record.tracking_number = self.env['ir.sequence'].next_by_code('shipping.tracking')
                if not record.tracking_number:
                    # Fallback if sequence not found
                    import random
                    import datetime
                    today = datetime.datetime.now().strftime('%Y%m%d')
                    random_num = str(random.randint(100000, 999999))
                    record.tracking_number = f"TRK{today}{random_num}"
        return True

    @api.depends('shipment_line_ids.weight', 'shipment_line_ids.quantity', 'shipment_line_ids.product_value')
    def _compute_totals(self):
        for record in self:
            record.total_weight = sum(line.total_weight for line in record.shipment_line_ids)
            record.total_volume = sum(line.volume * line.quantity for line in record.shipment_line_ids)
            record.total_value = sum(line.total_value for line in record.shipment_line_ids)

    @api.depends('shipping_cost', 'customer_price')
    def _compute_profit(self):
        for record in self:
            record.profit_margin = record.customer_price - record.shipping_cost

    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = 0

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

            # إضافة جديدة - جلب WhatsApp إذا كان محفوظ
            # يمكن حفظ رقم الواتساب في حقل مخصص في res.partner
            if hasattr(self.sender_id, 'whatsapp'):
                self.sender_whatsapp = self.sender_id.whatsapp
            elif self.sender_id.mobile:
                # أو استخدام رقم الموبايل كـ default
                self.sender_whatsapp = self.sender_id.mobile

            # جلب التفضيلات المحفوظة إن وجدت
            if hasattr(self.sender_id, 'preferred_pickup_time'):
                self.sender_preferred_pickup_time = self.sender_id.preferred_pickup_time

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

            # إضافة جديدة - جلب WhatsApp إذا كان محفوظ
            if hasattr(self.recipient_id, 'whatsapp'):
                self.recipient_whatsapp = self.recipient_id.whatsapp
            elif self.recipient_id.mobile:
                self.recipient_whatsapp = self.recipient_id.mobile

            # جلب التفضيلات المحفوظة إن وجدت
            if hasattr(self.recipient_id, 'preferred_delivery_time'):
                self.recipient_preferred_delivery_time = self.recipient_id.preferred_delivery_time

    @api.model
    def create(self, vals):
        if vals.get('order_number', _('New')) == _('New'):
            vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or _('New')
        return super(ShipmentOrder, self).create(vals)

    def action_confirm(self):
        """Confirm the shipment and generate tracking number"""
        for record in self:
            # Generate tracking number if not exists
            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'confirmed'
            # Log the confirmation with tracking number
            record.message_post(
                body=f"Shipment confirmed. Tracking Number: {record.tracking_number}",
                subject="Shipment Confirmed"
            )
        return True

    def action_pickup(self):
        """Mark shipment as picked up"""
        for record in self:
            # Ensure tracking number exists
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

    # معلومات المنتج
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

    # التفاصيل
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

    # الأبعاد
    length = fields.Float(string='Length (cm)')
    width = fields.Float(string='Width (cm)')
    height = fields.Float(string='Height (cm)')
    volume = fields.Float(
        string='Volume (m³)',
        compute='_compute_volume',
        store=True
    )

    # القيمة
    product_value = fields.Float(
        string='Unit Value',
        required=True
    )
    total_value = fields.Float(
        string='Total Value',
        compute='_compute_line_totals',
        store=True
    )

    # معلومات إضافية
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
            # تحويل من سم إلى متر
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
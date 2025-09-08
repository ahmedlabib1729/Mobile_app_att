from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ShipmentOrder(models.Model):
    _name = 'shipment.order'
    _description = 'Shipment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'order_number'

    # الحقول الأساسية كما هي...
    order_number = fields.Char(
        string='Order Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True
    )

    # معلومات المرسل
    sender_id = fields.Many2one('res.partner', string='Sender (Customer)', required=True, tracking=True)
    sender_name = fields.Char(related='sender_id.name', string='Sender Name', readonly=True)
    sender_phone = fields.Char(related='sender_id.phone', string='Sender Phone', readonly=True)
    sender_mobile = fields.Char(related='sender_id.mobile', string='Sender Mobile', readonly=True)
    sender_email = fields.Char(related='sender_id.email', string='Sender Email', readonly=True)
    sender_address = fields.Text(string='Pickup Address', required=True)
    sender_governorate_id = fields.Many2one(
        'res.country.state',
        string='Sender Governorate',
        required=True,
        domain=lambda self: [('country_id', '=', self.env.ref('base.eg').id)]
    )
    sender_city = fields.Char(string='City/Area')
    sender_country_id = fields.Many2one(
        'res.country',
        string='Sender Country',
        default=lambda self: self.env.ref('base.eg').id,
        readonly=True,
        required=True
    )
    sender_zip = fields.Char(string='Sender ZIP')
    sender_whatsapp = fields.Char(string='Sender WhatsApp')
    sender_preferred_pickup_time = fields.Selection([
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 3 PM)'),
        ('late_afternoon', 'Late Afternoon (3 PM - 6 PM)'),
        ('evening', 'Evening (6 PM - 9 PM)'),
        ('anytime', 'Any Time'),
    ], string='Preferred Pickup Time', default='anytime')
    sender_pickup_notes = fields.Text(string='Pickup Instructions')

    # معلومات المستلم
    recipient_id = fields.Many2one('res.partner', string='Recipient', required=True, tracking=True)
    recipient_name = fields.Char(string='Recipient Name', required=True)
    recipient_phone = fields.Char(string='Recipient Phone', required=True)
    recipient_mobile = fields.Char(string='Recipient Mobile')
    recipient_email = fields.Char(string='Recipient Email')
    recipient_address = fields.Text(string='Delivery Address', required=True)
    recipient_governorate_id = fields.Many2one(
        'res.country.state',
        string='Recipient Governorate',
        required=True,
        domain=lambda self: [('country_id', '=', self.env.ref('base.eg').id)]
    )
    recipient_city = fields.Char(string='City/Area', required=True)
    recipient_country_id = fields.Many2one(
        'res.country',
        string='Recipient Country',
        default=lambda self: self.env.ref('base.eg').id,
        readonly=True,
        required=True
    )
    recipient_zip = fields.Char(string='Recipient ZIP')
    recipient_whatsapp = fields.Char(string='Recipient WhatsApp')
    recipient_preferred_delivery_time = fields.Selection([
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 3 PM)'),
        ('late_afternoon', 'Late Afternoon (3 PM - 6 PM)'),
        ('evening', 'Evening (6 PM - 9 PM)'),
        ('anytime', 'Any Time'),
    ], string='Preferred Delivery Time', default='anytime')
    recipient_delivery_notes = fields.Text(string='Delivery Instructions')
    recipient_alternative_phone = fields.Char(string='Alternative Phone')

    # تفاصيل الشحن
    # في تعريف الحقل
    pickup_date = fields.Datetime(
        string='Pickup Date',
        required=True,
        tracking=True,
        default=lambda self: self._get_default_pickup_date() if hasattr(self,
                                                                        '_get_default_pickup_date') else fields.Datetime.now()
    )
    expected_delivery = fields.Datetime(string='Expected Delivery', tracking=True)
    actual_delivery = fields.Datetime(string='Actual Delivery', tracking=True)

    # المنتجات
    shipment_line_ids = fields.One2many('shipment.order.line', 'shipment_id', string='Products', required=True)

    # الأوزان والأبعاد
    total_weight = fields.Float(string='Total Weight (KG)', compute='_compute_totals', store=True, tracking=True)
    total_volume = fields.Float(string='Total Volume (m³)', compute='_compute_totals', store=True)
    total_value = fields.Float(string='Total Products Value', compute='_compute_totals', store=True)
    package_count = fields.Integer(string='Number of Packages', default=1, required=True)

    # شركة الشحن - بدون خدمة محددة
    shipping_company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        tracking=True,
        help='Select the shipping company'
    )

    # حقول التكلفة
    base_shipping_cost = fields.Float(
        string='Base Cost',
        store=True,
        readonly=False,
        help='Base shipping cost from governorate pricing'
    )

    weight_shipping_cost = fields.Float(
        string='Weight Cost',
        store=True,
        readonly=False,
        help='Cost based on weight'
    )

    cod_payment_type = fields.Selection([
        ('cash', 'Cash'),
        ('visa', 'Visa/Card'),
    ], string='COD Payment Type', default='cash',
        help='How the customer will pay to the delivery person')

    # هل COD يشمل قيمة الشحن؟
    cod_includes_shipping = fields.Boolean(
        string='COD Includes Shipping',
        default=False,
        help='If checked, the customer will pay shipping cost on delivery too'
    )

    # تفاصيل حساب COD
    cod_calculation_details = fields.Text(
        string='COD Calculation Details',
        compute='_compute_cod_details',
        store=True
    )

    # الحقول المحسوبة
    cod_base_amount = fields.Float(
        string='COD Base Amount',
        compute='_compute_cod_details',
        store=True,
        help='The base amount for COD calculation'
    )

    cod_percentage_used = fields.Float(
        string='COD Percentage Used %',
        compute='_compute_cod_details',
        store=True
    )

    cod_fixed_fee_used = fields.Float(
        string='COD Fixed Fee Used',
        compute='_compute_cod_details',
        store=True
    )

    # تعديل cod_fee_amount ليصبح محسوب
    cod_fee_amount = fields.Float(
        string='COD Fee',
        compute='_compute_cod_details',
        store=True,
        readonly=True,
        help='Cash on delivery fee calculated based on company settings'
    )

    insurance_fee_amount = fields.Float(
        string='Insurance Fee',
        store=True,
        readonly=False,
        help='Insurance fee amount'
    )

    shipping_cost = fields.Float(
        string='Total Shipping Cost',
        compute='_compute_shipping_cost',
        store=True,
        readonly=False,
        help='Total cost from shipping company',
        tracking=True
    )

    # معلومات إضافية
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

    shipment_type = fields.Selection([
        ('document', 'Documents'),
        ('package', 'Package'),
        ('pallet', 'Pallet'),
        ('container', 'Container'),
        ('other', 'Other')
    ], string='Shipment Type', default='package')

    payment_method = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('cod', 'Cash on Delivery'),
        ('credit', 'Credit Account'),
    ], string='Payment Method', default='prepaid')

    prepaid_payer = fields.Selection([
        ('sender', 'Sender'),
        ('recipient', 'Recipient'),
    ], string='Prepaid Payer',
        default='sender',
        help='Who will pay for prepaid shipment'
    )

    # حقل محسوب للحصول على الدافع الفعلي
    invoice_partner_id = fields.Many2one(
        'res.partner',
        string='Invoice Partner',
        compute='_compute_invoice_partner',
        store=True
    )

    cod_amount = fields.Float(string='COD Amount')
    insurance_required = fields.Boolean(string='Insurance Required')
    insurance_value = fields.Float(string='Insurance Value')

    tracking_number = fields.Char(string='Tracking Number', tracking=True, copy=False, readonly=True, index=True)
    tracking_url = fields.Char(string='Tracking URL', compute='_compute_tracking_url')

    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')

    # رسوم إضافية
    broker_fee_ids = fields.Many2many('broker.additional.fee', string='Additional Services')
    total_broker_fees = fields.Float(string='Total Additional Fees', compute='_compute_broker_fees', store=True,
                                     default=0.0)
    final_customer_price = fields.Float(string='Final Price', compute='_compute_final_price', store=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True,
                                 readonly=True)

    # للفواتير
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')

    weight_details = fields.Text(
        string='Weight Details',
        compute='_compute_weight_details'
    )

    insurance_calculation_details = fields.Text(
        string='Insurance Calculation Details',
        compute='_compute_insurance_details',
        store=True
    )

    insurance_type_used = fields.Char(
        string='Insurance Type Used',
        compute='_compute_insurance_details',
        store=True
    )

    pickup_type = fields.Selection([
        ('customer', 'Pickup from Customer'),
        ('sender', 'Customer Delivers to Us'),
    ], string='Pickup Type',
        default='customer',
        required=True,
        tracking=True,
        help='Choose whether we pickup from customer or customer delivers to us')

    pickup_fee = fields.Float(
        string='Pickup Fee',
        store=True,
        readonly=False,
        help='Additional fee for pickup service',
        default=0.0
    )
    color = fields.Integer(
        string='Color Index',
        default=0,
        help='Color index for kanban view'
    )

    # ===== Compute Methods =====

    @api.model
    def _get_default_pickup_date(self):
        """حساب pickup date الافتراضي عند فتح الفورم"""
        # استخدام دالة الحساب من pickup_configuration إذا موجودة
        if hasattr(self, '_calculate_pickup_date'):
            pickup_date, note = self._calculate_pickup_date()
            return pickup_date
        else:
            # إذا لم يكن pickup_configuration مثبت، استخدم الوقت الحالي
            return fields.Datetime.now()

    @api.onchange('shipping_company_id', 'recipient_governorate_id')
    def _onchange_shipping_company_governorate(self):
        """عند تغيير شركة الشحن أو المحافظة - محدث"""
        if self.shipping_company_id and self.recipient_governorate_id:
            # الحصول على كونفيج السعر للمحافظة
            price_config = self.shipping_company_id.get_governorate_price(
                self.recipient_governorate_id.id
            )

            if price_config:
                # حساب السعر
                cod_amount = self.cod_amount if self.payment_method == 'cod' else 0

                shipping_cost = price_config.calculate_shipping_price(
                    weight=self.total_weight,
                    cod_amount=cod_amount,
                    service_type='normal'
                )

                self.shipping_cost = shipping_cost

                # تحديث وقت التسليم المتوقع بناءً على pickup_date الصحيح
                if price_config.delivery_days_max and self.pickup_date:
                    # استخدم pickup_date المحسوب بدلاً من datetime.now()
                    self.expected_delivery = self.pickup_date + timedelta(days=price_config.delivery_days_max)
                elif price_config.delivery_days_max:
                    # إذا لم يكن هناك pickup_date، احسبه أولاً
                    if hasattr(self, '_calculate_pickup_date'):
                        pickup_date, note = self._calculate_pickup_date()
                        self.pickup_date = pickup_date
                        self.expected_delivery = pickup_date + timedelta(days=price_config.delivery_days_max)
                    else:
                        self.expected_delivery = fields.Datetime.now() + timedelta(days=price_config.delivery_days_max)

    @api.onchange('pickup_date')
    def _onchange_pickup_date(self):
        """إعادة حساب expected_delivery عند تغيير pickup_date"""
        if self.pickup_date and self.shipping_company_id and self.recipient_governorate_id:
            price_config = self.shipping_company_id.get_governorate_price(
                self.recipient_governorate_id.id
            )
            if price_config and price_config.delivery_days_max:
                self.expected_delivery = self.pickup_date + timedelta(days=price_config.delivery_days_max)

    @api.depends('payment_method', 'prepaid_payer', 'sender_id', 'recipient_id')
    def _compute_invoice_partner(self):
        """تحديد من سيتم إصدار الفاتورة له"""
        for record in self:
            if record.payment_method == 'prepaid':
                if record.prepaid_payer == 'recipient':
                    record.invoice_partner_id = record.recipient_id
                else:
                    record.invoice_partner_id = record.sender_id
            elif record.payment_method == 'cod':
                # في حالة COD، المستلم يدفع دائماً
                record.invoice_partner_id = record.sender_id
            else:
                # الافتراضي هو الراسل
                record.invoice_partner_id = record.sender_id

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        """عند تغيير طريقة الدفع"""
        if self.payment_method == 'prepaid':
            # يمكن اختيار من يدفع
            if not self.prepaid_payer:
                self.prepaid_payer = 'sender'
        elif self.payment_method == 'cod':
            # COD دائماً المستلم يدفع
            self.prepaid_payer = False


    def action_recalculate_dates(self):
        """زر لإعادة حساب التواريخ"""
        self.ensure_one()

        # إعادة حساب pickup date
        if hasattr(self, '_calculate_pickup_date'):
            pickup_date, note = self._calculate_pickup_date(self.create_date or fields.Datetime.now())
            self.pickup_date = pickup_date
            self.pickup_date_calculated = True
            self.pickup_calculation_note = note

        # إعادة حساب expected delivery
        if self.shipping_company_id and self.recipient_governorate_id:
            price_config = self.shipping_company_id.get_governorate_price(
                self.recipient_governorate_id.id
            )
            if price_config and price_config.delivery_days_max:
                self.expected_delivery = self.pickup_date + timedelta(days=price_config.delivery_days_max)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dates Updated'),
                'message': _('Pickup and delivery dates have been recalculated'),
                'type': 'success',
            }
        }

    @api.depends('insurance_required', 'total_value', 'shipping_company_id', 'insurance_fee_amount')
    def _compute_insurance_details(self):
        """حساب وعرض تفاصيل التأمين"""
        for record in self:
            if not record.insurance_required or not record.shipping_company_id:
                record.insurance_calculation_details = 'Insurance not required'
                record.insurance_type_used = ''
                continue

            company = record.shipping_company_id
            details = []

            # معلومات الإعدادات
            details.append(f"Company: {company.name}")
            details.append(f"Insurance Type: {company.insurance_type}")

            if company.insurance_type == 'percentage':
                details.append(f"Insurance Rate: {company.insurance_percentage}%")
                calculated_fee = record.total_value * company.insurance_percentage / 100
                details.append(
                    f"Calculation: {record.total_value:.2f} × {company.insurance_percentage}% = {calculated_fee:.2f} EGP")
            else:
                details.append(f"Fixed Insurance Fee: {company.insurance_fixed_amount:.2f} EGP")
                calculated_fee = company.insurance_fixed_amount

            details.append(f"Minimum Value Required: {company.insurance_minimum_value:.2f} EGP")
            details.append(f"Product Value: {record.total_value:.2f} EGP")

            # التحقق من التطابق
            if abs(record.insurance_fee_amount - calculated_fee) > 0.01:
                details.append("⚠️ WARNING: Mismatch in insurance calculation!")
                details.append(f"   Stored: {record.insurance_fee_amount:.2f} EGP")
                details.append(f"   Expected: {calculated_fee:.2f} EGP")
            else:
                details.append(f"✓ Final Insurance Fee: {record.insurance_fee_amount:.2f} EGP")

            record.insurance_calculation_details = '\n'.join(details)
            record.insurance_type_used = company.insurance_type

    @api.depends('shipment_line_ids', 'total_weight', 'weight_shipping_cost', 'shipping_company_id',
                 'recipient_governorate_id')
    def _compute_weight_details(self):
        for record in self:
            details = []
            if record.shipment_line_ids:
                for line in record.shipment_line_ids:
                    details.append(f"{line.product_name}: {line.quantity} × {line.weight} = {line.total_weight} KG")
                details.append(f"---")
                details.append(f"Total Weight: {record.total_weight} KG")

                if record.shipping_company_id and record.recipient_governorate_id:
                    price_config = record.shipping_company_id.get_governorate_price(record.recipient_governorate_id.id)
                    if price_config:
                        details.append(
                            f"Price/KG for {record.recipient_governorate_id.name}: {price_config.price_per_kg} EGP")
                        details.append(
                            f"Weight Cost: {record.total_weight} × {price_config.price_per_kg} = {record.weight_shipping_cost} EGP")

            record.weight_details = '\n'.join(details) if details else 'No products added'

    @api.depends('payment_method', 'cod_amount', 'cod_payment_type', 'cod_includes_shipping',
                 'shipping_cost', 'shipping_company_id')
    def _compute_cod_details(self):
        """حساب تفاصيل COD بناءً على إعدادات الشركة"""
        for record in self:
            if record.payment_method != 'cod' or not record.shipping_company_id:
                record.cod_fee_amount = 0
                record.cod_base_amount = 0
                record.cod_percentage_used = 0
                record.cod_fixed_fee_used = 0
                record.cod_calculation_details = ''
                continue

            # حساب رسوم COD باستخدام دالة الشركة
            result = record.shipping_company_id.calculate_cod_fee(
                cod_amount=record.cod_amount,
                payment_type=record.cod_payment_type,
                include_shipping_cost=record.cod_includes_shipping,
                shipping_cost=record.shipping_cost
            )

            record.cod_fee_amount = result['fee_amount']
            record.cod_base_amount = result['total_cod_amount']
            record.cod_percentage_used = result['percentage_used']
            record.cod_fixed_fee_used = result['fixed_fee_used']

            # إنشاء تفاصيل الحساب
            details = []
            details.append(f"COD Amount: {record.cod_amount:.2f} EGP")

            if record.cod_includes_shipping:
                details.append(f"Shipping Cost: {record.shipping_cost:.2f} EGP")
                details.append(f"Total COD Base: {result['total_cod_amount']:.2f} EGP")

            details.append(f"Payment Type: {record.cod_payment_type.upper()}")

            if result.get('reason'):
                details.append(f"Note: {result['reason']}")
            else:
                details.append(f"Percentage: {result['percentage_used']:.2f}%")
                if result.get('percentage_fee'):
                    details.append(f"Percentage Fee: {result['percentage_fee']:.2f} EGP")
                if result['fixed_fee_used']:
                    details.append(f"Fixed Fee: {result['fixed_fee_used']:.2f} EGP")
                details.append(f"Total COD Fee: {result['fee_amount']:.2f} EGP")

            record.cod_calculation_details = '\n'.join(details)

    @api.depends('shipment_line_ids.weight', 'shipment_line_ids.quantity', 'shipment_line_ids.product_value')
    def _compute_totals(self):
        for record in self:
            record.total_weight = sum(line.total_weight for line in record.shipment_line_ids)
            record.total_volume = sum(line.volume * line.quantity for line in record.shipment_line_ids)
            record.total_value = sum(line.total_value for line in record.shipment_line_ids)

            # استدعاء إعادة حساب الشحن عند تغيير الوزن
            if record.shipping_company_id and record.recipient_governorate_id:
                record._onchange_calculate_shipping()

    @api.depends('base_shipping_cost', 'weight_shipping_cost', 'cod_fee_amount', 'insurance_fee_amount', 'pickup_fee')
    def _compute_shipping_cost(self):
        """حساب إجمالي تكلفة الشحن مع COD والاستلام"""
        for record in self:
            total = (
                    (record.base_shipping_cost or 0) +
                    (record.weight_shipping_cost or 0) +
                    (record.cod_fee_amount or 0) +
                    (record.insurance_fee_amount or 0) +
                    (record.pickup_fee or 0)  # إضافة رسوم الاستلام
            )
            record.shipping_cost = total

    @api.onchange('pickup_type', 'shipping_company_id')
    def _onchange_pickup_type(self):
        """تحديد رسوم الاستلام حسب النوع"""
        if self.pickup_type == 'customer' and self.shipping_company_id:
            # يمكنك تحديد قيمة افتراضية أو من إعدادات الشركة
            # مثلاً 20 جنيه رسوم استلام
            self.pickup_fee = 20.0
        else:
            self.pickup_fee = 0.0

    @api.depends('broker_fee_ids')
    def _compute_broker_fees(self):
        for record in self:
            if record.broker_fee_ids:
                record.total_broker_fees = sum(record.broker_fee_ids.mapped('fee_amount'))
            else:
                record.total_broker_fees = 0.0

    @api.depends('shipping_cost', 'total_broker_fees')
    def _compute_final_price(self):
        for record in self:
            record.final_customer_price = record.shipping_cost + record.total_broker_fees

    @api.depends('tracking_number')
    def _compute_tracking_url(self):
        for record in self:
            if record.tracking_number:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                record.tracking_url = f"{base_url}/shipment/track?tracking={record.tracking_number}"
            else:
                record.tracking_url = False

    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = 0

    # ===== Onchange Methods =====

    @api.onchange('shipping_company_id', 'recipient_governorate_id', 'total_weight',
                  'payment_method', 'cod_amount', 'cod_payment_type', 'cod_includes_shipping',
                  'insurance_required', 'total_value')  # أضف الحقول المتعلقة بالتأمين
    def _onchange_calculate_shipping(self):
        """حساب السعر عند تغيير الشركة أو المحافظة أو الوزن أو إعدادات COD أو التأمين"""
        if self.shipping_company_id and self.recipient_governorate_id:
            # الحصول على كونفيج السعر للمحافظة
            price_config = self.shipping_company_id.get_governorate_price(
                self.recipient_governorate_id.id
            )

            if price_config:
                # حساب السعر الأساسي
                self.base_shipping_cost = price_config.base_price

                # حساب تكلفة الوزن
                if self.total_weight > 0 and price_config.price_per_kg > 0:
                    self.weight_shipping_cost = self.total_weight * price_config.price_per_kg
                else:
                    self.weight_shipping_cost = 0

                # حساب رسوم التأمين - التصحيح هنا
                if self.insurance_required and self.total_value > 0:
                    # التحقق من وجود دالة حساب التأمين
                    if hasattr(self.shipping_company_id, 'calculate_insurance_fee'):
                        insurance_result = self.shipping_company_id.calculate_insurance_fee(
                            product_value=self.total_value,
                            apply_insurance=True
                        )
                        self.insurance_fee_amount = insurance_result.get('fee_amount', 0)
                    else:
                        # إذا لم توجد الدالة، استخدم القيمة الافتراضية
                        self.insurance_fee_amount = 0
                        _logger.warning('Insurance calculation method not found in shipping company')
                else:
                    self.insurance_fee_amount = 0

                # تحديث وقت التسليم المتوقع
                if price_config.delivery_days_max:
                    from datetime import datetime, timedelta
                    self.expected_delivery = datetime.now() + timedelta(days=price_config.delivery_days_max)

        # حساب COD (سيتم تلقائياً عبر _compute_cod_details)
        if self.payment_method == 'cod' and self.shipping_company_id:
            self._compute_cod_details()

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

            if self.sender_id.state_id:
                self.sender_governorate_id = self.sender_id.state_id

            self.sender_city = self.sender_id.city
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

            if self.recipient_id.state_id:
                self.recipient_governorate_id = self.recipient_id.state_id

            self.recipient_city = self.recipient_id.city
            self.recipient_zip = self.recipient_id.zip

            if hasattr(self.recipient_id, 'whatsapp'):
                self.recipient_whatsapp = self.recipient_id.whatsapp
            elif self.recipient_id.mobile:
                self.recipient_whatsapp = self.recipient_id.mobile

    # ===== Helper Methods =====

    def action_recalculate_fees(self):
        """زر لإعادة حساب الرسوم يدوياً شاملة COD"""
        self.ensure_one()
        if self.shipping_company_id and self.recipient_governorate_id:
            self._onchange_calculate_shipping()
            # إعادة حساب COD
            if self.payment_method == 'cod':
                self._compute_cod_details()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('All fees including COD recalculated successfully'),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Please select a shipping company and recipient governorate first'),
                    'type': 'warning',
                }
            }

    def action_calculate_best_price(self):
        """البحث عن أفضل سعر من جميع الشركات"""
        self.ensure_one()

        if not self.recipient_governorate_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Please select recipient governorate first'),
                    'type': 'warning',
                }
            }

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

        all_companies = self.env['shipping.company'].search([('active', '=', True)])

        if not all_companies:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Companies Found'),
                    'message': _('No active shipping companies available'),
                    'type': 'warning',
                }
            }

        best_price = float('inf')
        best_company = None
        prices_list = []

        for company in all_companies:
            price_config = company.get_governorate_price(self.recipient_governorate_id.id)
            if price_config:
                # حساب السعر لهذه الشركة
                base_price = price_config.base_price
                weight_cost = self.total_weight * price_config.price_per_kg if price_config.price_per_kg else 0

                cod_fee = 0
                if self.payment_method == 'cod' and self.cod_amount > 0:
                    cod_fee = price_config.cod_fee or 0
                    if price_config.cod_percentage > 0:
                        cod_fee += (self.cod_amount * price_config.cod_percentage / 100)

                total_price = base_price + weight_cost + cod_fee

                prices_list.append({
                    'company': company.name,
                    'price': total_price
                })

                if total_price < best_price:
                    best_price = total_price
                    best_company = company

        if best_company:
            self.shipping_company_id = best_company
            self._onchange_calculate_shipping()

            price_details = '\n'.join([
                f"• {p['company']}: {p['price']:.2f} EGP"
                for p in sorted(prices_list, key=lambda x: x['price'])[:5]
            ])

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Best Price Applied'),
                    'message': _(
                        'Best price: %.2f EGP\n'
                        'Company: %s\n\n'
                        'Top prices:\n%s'
                    ) % (best_price, best_company.name, price_details),
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

    def _generate_tracking_number(self):
        """Generate unique tracking number for shipment"""
        for record in self:
            if not record.tracking_number:
                record.tracking_number = self.env['ir.sequence'].next_by_code('shipping.tracking')
                if not record.tracking_number:
                    import random
                    today = datetime.now().strftime('%Y%m%d')
                    random_num = str(random.randint(100000, 999999))
                    record.tracking_number = f"TRK{today}{random_num}"
        return True

    # ===== CRUD Methods =====

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-calculate pickup date"""
        import logging
        _logger = logging.getLogger(__name__)

        for vals in vals_list:
            # توليد رقم الطلب
            if vals.get('order_number', _('New')) == _('New'):
                vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or _('New')

            # حساب pickup_date إذا لم يكن موجود
            if 'pickup_date' not in vals or not vals.get('pickup_date'):
                try:
                    # التحقق من وجود دالة الحساب
                    if hasattr(self, '_calculate_pickup_date'):
                        pickup_date, note = self._calculate_pickup_date()
                        vals['pickup_date'] = pickup_date
                        vals['pickup_date_calculated'] = True
                        vals['pickup_calculation_note'] = note
                        _logger.info(f"Auto-calculated pickup date: {pickup_date}")
                    else:
                        # إذا لم توجد الدالة، استخدم الوقت الحالي
                        vals['pickup_date'] = fields.Datetime.now()
                        _logger.warning("_calculate_pickup_date not found, using current time")
                except Exception as e:
                    _logger.error(f"Error calculating pickup date: {str(e)}")
                    vals['pickup_date'] = fields.Datetime.now()

        return super(ShipmentOrder, self).create(vals_list)

    # ===== Action Methods =====

    def action_confirm(self):
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
        for record in self:
            record.state = 'returned'
            record.message_post(
                body="Shipment has been returned",
                subject="Returned"
            )
        return True

    def action_cancel(self):
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


# باقي الكلاسات كما هي
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
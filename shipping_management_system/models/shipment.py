from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError, AccessError
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
        ('torood_hub', 'Torood Hub'),  # حالة جديدة 1
        ('picked', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('shipping_company_hub', 'Shipping Company Hub'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True,
        group_expand='_read_group_state')

    shipment_type = fields.Selection([

        ('normal', 'Normal'),
        ('document', 'Doc'),
        ('pallet', 'Special'),
        ('BATTERY_YES', 'BATTERY_YES'),
        ('BATTERY_NO', 'BATTERY_NO'),
        ('ALL_BATTERY', 'ALL BATTERY'),
        ('Sensitive_cargo', 'Sensitive cargo'),

    ], string='Goods Type')

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

    cod_amount = fields.Float(
        string='COD Amount',
        compute='_compute_cod_amount',
        store=True,
        readonly=False,
        help='Auto-calculated: Product Value')

    cod_amount_sheet_excel = fields.Float(
        string='COD Atmount Export To shipping Company',
        compute='_compute_cod_amount',
        store=True,
        readonly=False,
        help='Auto-calculated: Product Value + Company Charges')


    insurance_required = fields.Boolean(string='Insurance Required')
    insurance_value = fields.Float(string='Insurance Value')

    tracking_number = fields.Char(string='Tracking Number', tracking=True, copy=False, readonly=True, index=True)
    tracking_url = fields.Char(string='Tracking URL', compute='_compute_tracking_url')
    tracking_number_shipping_company = fields.Char(string='shipping Company Tracking Number', tracking=True, copy=False,index=True)
    mark_as_packing = fields.Boolean(
        string='Mark as Packing',
        default=False,
        help='Enable if this shipment requires packing service'
    )

    allow_the_package_to_be_opened = fields.Boolean(
        string='Mark as Packing',
        default=False,
        help='Whether to allow the package to be opened'
    )

    delivery_type = fields.Selection([
        ('Deliver', 'Deliver'),
        ('Self_Pick-up', 'Self Pick-up'),

    ], string='Delivery Type')

    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')


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
    total_broker_fees = fields.Float(
        string='Total Broker Fees (Deprecated)',
        compute='_compute_broker_fees_compat',
        store=True,
        default=0.0
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

    cod_fee_ranges = fields.One2many(
        'cod.fee.range',
        'shipping_company_id',
        string='COD Fee Ranges'
    )

    # حقول المرتجعات
    is_return_processed = fields.Boolean(
        string='Return Processed',
        default=False,
        readonly=True
    )

    return_penalty_amount = fields.Float(
        string='Return Penalty',
        compute='_compute_return_penalty',
        store=True
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

    @api.depends('state', 'shipping_company_id', 'company_base_cost', 'company_weight_cost')
    def _compute_return_penalty(self):
        """حساب غرامة المرتجع بناءً على Company Base Cost + Company Weight Cost"""
        for record in self:
            if record.state == 'returned' and record.shipping_company_id:
                # حساب الغرامة على السعر الأساسي للشركة + رسوم الوزن فقط
                base_amount = (record.company_base_cost or 0) + (record.company_weight_cost or 0)
                # استخدام النسبة من إعدادات شركة الشحن
                if record.shipping_company_id.return_penalty_enabled:
                    penalty_rate = record.shipping_company_id.return_penalty_percentage / 100
                    record.return_penalty_amount = base_amount * penalty_rate
                else:
                    record.return_penalty_amount = 0
            else:
                record.return_penalty_amount = 0

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

    @api.depends('payment_method', 'cod_amount_sheet_excel', 'cod_payment_type', 'cod_includes_shipping',
                 'shipping_cost', 'shipping_company_id')
    def _compute_cod_details(self):
        """حساب تفاصيل COD بناءً على شرائح الشركة"""
        for record in self:
            if record.payment_method != 'cod' or not record.shipping_company_id:
                record.cod_fee_amount = 0
                record.cod_base_amount = 0
                record.cod_percentage_used = 0
                record.cod_fixed_fee_used = 0
                record.cod_calculation_details = ''
                continue

            # حساب رسوم COD باستخدام دالة الشركة المحدثة
            result = record.shipping_company_id.calculate_cod_fee(
                cod_amount=record.cod_amount_sheet_excel,  # استخدام cod_amount_sheet_excel
                payment_type=record.cod_payment_type,
                include_shipping_cost=record.cod_includes_shipping,
                shipping_cost=record.shipping_cost
            )

            record.cod_fee_amount = result['fee_amount']
            record.cod_base_amount = result['total_cod_amount']
            record.cod_percentage_used = result['percentage_used']
            record.cod_fixed_fee_used = result.get('fixed_fee_used', 0)

            # إنشاء تفاصيل الحساب
            details = []
            details.append(f"COD Amount (Sheet Excel): {record.cod_amount_sheet_excel:.2f} EGP")

            if record.cod_includes_shipping:
                details.append(f"Shipping Cost: {record.shipping_cost:.2f} EGP")
                details.append(f"Total COD Base: {result['total_cod_amount']:.2f} EGP")

            details.append(f"Payment Type: {record.cod_payment_type.upper()}")

            # إضافة معلومات الشريحة المستخدمة
            if result.get('range_used'):
                details.append(f"Range Used: {result['range_used']}")

            if result.get('reason'):
                details.append(f"Note: {result['reason']}")
            else:
                details.append(f"Percentage: {result['percentage_used']:.2f}%")
                if result.get('percentage_fee'):
                    details.append(f"Percentage Fee: {result['percentage_fee']:.2f} EGP")
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

    @api.depends('base_shipping_cost', 'weight_shipping_cost', 'cod_fee_amount', 'insurance_fee_amount')
    def _compute_shipping_cost(self):
        """حساب إجمالي تكلفة الشحن بدون pickup fee"""
        for record in self:
            # pickup_fee لا يُضاف هنا لأنه جزء من company cost
            total = (
                    (record.base_shipping_cost or 0) +
                    (record.weight_shipping_cost or 0) +
                    (record.cod_fee_amount or 0) +
                    (record.insurance_fee_amount or 0)
            )
            record.shipping_cost = total

    @api.onchange('pickup_type', 'shipping_company_id', 'sender_id')
    def _onchange_pickup_type(self):
        """تحديد رسوم الاستلام حسب النوع والفئة"""
        if self.pickup_type == 'customer':
            # التحقق من فئة العميل أولاً
            if self.sender_id and self.sender_id.price_category_id:
                category = self.sender_id.price_category_id
                if category.pickup_fee_enabled:
                    self.pickup_fee = category.pickup_fee_amount
                else:
                    self.pickup_fee = 0.0
            elif self.shipping_company_id:
                # إذا لم يكن هناك فئة، استخدم القيمة الافتراضية
                self.pickup_fee = 20.0
            else:
                self.pickup_fee = 20.0
        else:
            # إذا العميل سيوصل بنفسه، لا توجد رسوم
            self.pickup_fee = 0.0

    @api.onchange('sender_id')
    def _onchange_sender_pickup_fee(self):
        """تطبيق رسوم الاستلام عند تغيير العميل"""
        if self.pickup_type == 'customer' and self.sender_id and self.sender_id.price_category_id:
            category = self.sender_id.price_category_id
            if category.pickup_fee_enabled:
                self.pickup_fee = category.pickup_fee_amount



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
                  'payment_method', 'cod_payment_type', 'cod_includes_shipping',
                  'insurance_required', 'total_value', 'total_company_cost',
                  'total_additional_fees', 'discount_amount')
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

                # حساب تكلفة الوزن مع احتساب الوزن المجاني
                if self.total_weight > 0 and self.shipping_company_id:
                    # احسب الوزن الذي سيتم تحصيل رسوم عليه
                    free_limit = self.shipping_company_id.free_weight_limit or 0

                    if self.total_weight > free_limit:
                        # احسب فقط الوزن الزائد عن الحد المجاني
                        chargeable_weight = self.total_weight - free_limit
                        self.weight_shipping_cost = chargeable_weight * self.shipping_company_id.unified_price_per_kg
                    else:
                        # الوزن كله مجاني
                        self.weight_shipping_cost = 0
                else:
                    self.weight_shipping_cost = 0

                # حساب رسوم التأمين
                if self.insurance_required and self.total_value > 0:
                    if hasattr(self.shipping_company_id, 'calculate_insurance_fee'):
                        insurance_result = self.shipping_company_id.calculate_insurance_fee(
                            product_value=self.total_value,
                            apply_insurance=True
                        )
                        self.insurance_fee_amount = insurance_result.get('fee_amount', 0)
                    else:
                        self.insurance_fee_amount = 0
                else:
                    self.insurance_fee_amount = 0

                # تحديث وقت التسليم المتوقع
                if price_config.delivery_days_max:
                    from datetime import datetime, timedelta
                    if self.pickup_date:
                        self.expected_delivery = self.pickup_date + timedelta(days=price_config.delivery_days_max)
                    else:
                        if hasattr(self, '_calculate_pickup_date'):
                            pickup_date, note = self._calculate_pickup_date()
                            self.pickup_date = pickup_date
                            self.expected_delivery = pickup_date + timedelta(days=price_config.delivery_days_max)
                        else:
                            self.expected_delivery = datetime.now() + timedelta(days=price_config.delivery_days_max)
            else:
                self.base_shipping_cost = 0
                if self.total_weight > 0 and self.shipping_company_id:
                    free_limit = self.shipping_company_id.free_weight_limit or 0
                    if self.total_weight > free_limit:
                        chargeable_weight = self.total_weight - free_limit
                        self.weight_shipping_cost = chargeable_weight * self.shipping_company_id.unified_price_per_kg
                    else:
                        self.weight_shipping_cost = 0
                else:
                    self.weight_shipping_cost = 0

        # حساب COD
        if self.payment_method == 'cod' and self.shipping_company_id:
            self._compute_cod_details()

        if self.payment_method == 'cod':
            company_price = self.total_company_cost + self.total_additional_fees - self.discount_amount
            self.cod_amount = self.total_value
            self.cod_amount_sheet_excel = self.total_value + self.company_base_cost + self.company_weight_cost
            # إعادة حساب COD details
            self._compute_cod_details()

    # في class ShipmentOrder، أضف هذه الدالة المحسوبة:

    @api.depends('total_value', 'total_company_cost', 'total_additional_fees', 'discount_amount', 'payment_method' , 'company_base_cost' , 'company_weight_cost')
    def _compute_cod_amount(self):
        """حساب مبلغ COD تلقائياً = قيمة البضاعة + تكلفة الشركة"""
        for record in self:
            if record.payment_method == 'cod':
                # COD = قيمة البضاعة + (تكلفة الشركة + رسوم إضافية - خصم)
                company_price = record.total_company_cost + record.total_additional_fees - record.discount_amount
                record.cod_amount = record.total_value
                record.cod_amount_sheet_excel = record.total_value + record.company_base_cost + record.company_weight_cost
            else:
                record.cod_amount = 0




    # أضف أيضاً onchange للتحديث عند تغيير payment_method:
    @api.onchange('payment_method', 'total_value', 'total_company_cost', 'total_additional_fees', 'discount_amount')
    def _onchange_cod_calculation(self):
        """تحديث COD amount عند تغيير طريقة الدفع أو الأسعار"""
        if self.payment_method == 'cod':
            company_price = self.total_company_cost + self.total_additional_fees - self.discount_amount
            self.cod_amount = self.total_value
            self.cod_amount_sheet_excel = self.total_value + self.company_base_cost + self.company_weight_cost
            # إعادة حساب COD fee بناء على القيمة الجديدة
            self._compute_cod_details()
        else:
            self.cod_amount = 0
            self.cod_amount_sheet_excel = 0

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

    def action_to_torood_hub(self):
        """نقل الشحنة إلى Torood Hub مع التحقق من الحقول وتصدير الإكسيل تلقائياً"""
        for record in self:
            # التحقق من الحالة السابقة
            if record.state != 'confirmed':
                raise UserError(_('Shipment must be Confirmed first!'))

            # قائمة تفصيلية للحقول المفقودة
            errors = []



            # التحقق من delivery_type
            if not record.delivery_type:
                errors.append('❌ Delivery Type must be selected (Deliver/Self Pick-up)')

            # إذا كانت هناك أخطاء، اعرضها جميعاً
            if errors:
                error_message = (
                        f'Cannot move Order #{record.order_number} to Torood Hub!\n\n'
                        'Required fields:\n' + '\n'.join(errors) + '\n\n'
                                                                   'Please complete all fields before proceeding.'
                )
                raise UserError(_(error_message))

            # إذا كانت جميع الحقول موجودة، تابع العملية
            if not record.tracking_number:
                record._generate_tracking_number()

            record.state = 'torood_hub'
            record.message_post(
                body=f"✅ Shipment moved to Torood Hub successfully!\n"
                     f"📦 Order: {record.order_number}\n"
                     f"🔍 Tracking: {record.tracking_number}\n"
                     f"🚚 Shipping Company Tracking: {record.tracking_number_shipping_company}\n"
                     f"📋 Packing Required: {'Yes' if record.mark_as_packing else 'No'}\n"
                     f"🚛 Delivery Type: {record.delivery_type}",
                subject="Moved to Torood Hub - Ready for Export"
            )

        # بعد تحديث الحالة بنجاح، قم بتصدير الإكسيل
        return self.action_export_to_excel()

    def action_to_torood_hub_with_custom_export(self):
        """نقل الشحنة إلى Torood Hub مع التحقق والتصدير المخصص"""
        import base64
        import io
        from datetime import datetime

        # التحقق من تثبيت xlsxwriter
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter library: pip install xlsxwriter'))

        # التحقق من الحقول المطلوبة لكل سجل
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_(f'Order #{record.order_number} must be Confirmed first!'))

            # قائمة للحقول المفقودة
            missing_fields = []


            if not record.delivery_type:
                missing_fields.append('Delivery Type')

            if missing_fields:
                raise UserError(_(
                    'Order #%s is missing required fields:\n• %s\n\n'
                    'Please fill in all required fields before proceeding to Torood Hub.'
                ) % (record.order_number, '\n• '.join(missing_fields)))

            # تحديث الحالة
            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'torood_hub'
            record.message_post(
                body="Shipment arrived at Torood Hub - Excel exported",
                subject="At Torood Hub"
            )

        # إنشاء ملف Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Torood Hub Shipments')

        # تنسيقات Excel محسنة
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4CAF50',  # لون أخضر للـ Torood Hub
            'font_color': 'white',
            'border': 1
        })

        cell_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1
        })

        number_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'num_format': '#,##0.00'
        })

        highlight_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#E8F5E9'  # لون أخضر فاتح للحقول المهمة
        })

        # الـ 16 عمود المطلوبين + الحقول الإضافية المهمة
        headers = [
            'S.O.', 'Goods type', 'Goods name', 'Quantity', 'Weight', 'COD',
            'Insure price', 'Whether to allow the package to be opened', 'Remark',
            'Name', 'Telephone', 'City', 'Area', 'Receivers address',
            'Receiver Email', 'Delivery Type',
            # حقول إضافية مهمة
            'Shipping Tracking', 'Packing Required', 'Status'
        ]

        # كتابة الهيدر
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # تحديد عرض الأعمدة
        column_widths = [15, 15, 25, 10, 10, 12, 12, 30, 30, 20, 15, 15, 15, 35, 25, 15, 20, 15, 12]
        for col, width in enumerate(column_widths[:len(headers)]):
            worksheet.set_column(col, col, width)

        # كتابة البيانات
        row = 1
        total_cod = 0
        total_weight = 0

        for shipment in self:
            # S.O.
            worksheet.write(row, 0, shipment.order_number or '', cell_format)

            # Goods type
            goods_type_mapping = {
                'normal': 'Normal',
                'document': 'Doc',
                'pallet': 'Special',
                'package': 'Package',
                'BATTERY_YES': 'BATTERY_YES',
                'BATTERY_NO': 'BATTERY_NO',
                'ALL_BATTERY': 'ALL BATTERY',
                'Sensitive_cargo': 'Sensitive cargo'
            }
            goods_type = goods_type_mapping.get(shipment.shipment_type, shipment.shipment_type or 'Normal')
            worksheet.write(row, 1, goods_type, cell_format)

            # Goods name
            goods_names = ', '.join([line.product_name for line in shipment.shipment_line_ids])
            worksheet.write(row, 2, goods_names or '', cell_format)

            # Quantity
            total_qty = sum(line.quantity for line in shipment.shipment_line_ids) or 1
            worksheet.write(row, 3, total_qty, number_format)

            # Weight
            worksheet.write(row, 4, shipment.total_weight or 0, number_format)
            total_weight += shipment.total_weight or 0

            # COD
            cod_amount_sheet_excel = shipment.cod_amount_sheet_excel if shipment.payment_method == 'cod' else 0
            worksheet.write(row, 5, cod_amount_sheet_excel, number_format)
            total_cod += cod_amount_sheet_excel

            # Insure price
            insure_price = (shipment.insurance_value or shipment.total_value or 0) if shipment.insurance_required else 0
            worksheet.write(row, 6, insure_price, number_format)

            # Whether to allow the package to be opened
            allow_open = 'Yes' if shipment.allow_the_package_to_be_opened else 'No'
            worksheet.write(row, 7, allow_open, highlight_format if allow_open == 'Yes' else cell_format)

            # Remark
            worksheet.write(row, 8, shipment.notes or '', cell_format)

            # Name (المستلم)
            worksheet.write(row, 9, shipment.recipient_name or '', cell_format)

            # Telephone
            phone = shipment.recipient_mobile or shipment.recipient_phone or ''
            worksheet.write(row, 10, phone, cell_format)

            # City
            city = shipment.recipient_governorate_id.name if shipment.recipient_governorate_id else ''
            worksheet.write(row, 11, city, cell_format)

            # Area
            worksheet.write(row, 12, shipment.recipient_city or '', cell_format)

            # Receivers address
            worksheet.write(row, 13, shipment.recipient_address or '', cell_format)

            # Receiver Email
            worksheet.write(row, 14, shipment.recipient_email or '', cell_format)

            # Delivery Type
            delivery_type_mapping = {
                'Deliver': 'Deliver',
                'Self_Pick-up': 'Self Pick-up'
            }
            delivery_type = delivery_type_mapping.get(shipment.delivery_type, shipment.delivery_type or 'Deliver')
            worksheet.write(row, 15, delivery_type, highlight_format)

            # الحقول الإضافية المهمة
            # Shipping Company Tracking
            worksheet.write(row, 16, shipment.tracking_number_shipping_company or '', highlight_format)

            # Packing Required
            packing = 'Yes' if shipment.mark_as_packing else 'No'
            worksheet.write(row, 17, packing, highlight_format if packing == 'Yes' else cell_format)

            # Status
            worksheet.write(row, 18, 'Torood Hub', highlight_format)

            row += 1

        # إضافة صف الإجماليات
        summary_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#FFE082',
            'border': 1
        })

        row += 1  # سطر فارغ
        worksheet.write(row, 0, 'TOTAL', summary_format)
        worksheet.write(row, 1, f'{len(self)} Shipments', summary_format)
        worksheet.write(row, 2, '', summary_format)
        worksheet.write(row, 3, f'{sum(sum(line.quantity for line in s.shipment_line_ids) for s in self)}',
                        summary_format)
        worksheet.write(row, 4, f'{total_weight:.2f} KG', summary_format)
        worksheet.write(row, 5, f'{total_cod:.2f} EGP', summary_format)

        # إغلاق الملف
        workbook.close()
        output.seek(0)

        # إنشاء attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'torood_hub_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self[0].id if len(self) == 1 else False,
        })

        # إرجاع action لتحميل الملف
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_pickup(self):
        """استلام الشحنة من Torood Hub - مع التحقق من الحقول المطلوبة"""
        for record in self:
            # التحقق من الحالة السابقة
            if record.state != 'torood_hub':
                raise UserError(_('Shipment must be at Torood Hub first!'))

            # قائمة للحقول المفقودة
            missing_fields = []

            # التحقق من الحقول المطلوبة
            if not record.tracking_number_shipping_company:
                missing_fields.append('Shipping Company Tracking Number')

            # لـ mark_as_packing: إذا تريد أن يكون True فقط
            if not record.mark_as_packing:
                missing_fields.append('Mark as Packing must be checked')

            if not record.delivery_type:
                missing_fields.append('Delivery Type')

            # إذا كانت هناك حقول مفقودة
            if missing_fields:
                raise UserError(_(
                    'Cannot proceed to Picked Up status!\n\n'
                    'The following fields are required:\n• %s\n\n'
                    'Please fill in all required fields before proceeding.'
                ) % '\n• '.join(missing_fields))

            # تابع العملية
            record.state = 'picked'
            record.message_post(
                body=f"Shipment picked up - Tracking: {record.tracking_number_shipping_company}",
                subject="Pickup Completed"
            )

        return True

    def action_in_transit(self):
        """الشحنة في الطريق - تبقى كما هي بعد picked"""
        for record in self:
            if record.state != 'picked':
                raise UserError(_('Shipment must be Picked Up first!'))

            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'in_transit'
            record.message_post(
                body=f"Shipment in transit. Track at: {record.tracking_url or record.tracking_number}",
                subject="In Transit"
            )
        return True



    # Action للانتقال إلى Shipping Company Hub
    def action_to_shipping_company_hub(self):
        for record in self:
            if record.state != 'in_transit':
                raise UserError(_('Shipment must be In Transit first!'))
            record.state = 'shipping_company_hub'
            company_name = record.shipping_company_id.name if record.shipping_company_id else 'Shipping Company'
            record.message_post(
                body=f"Shipment arrived at {company_name} Hub",
                subject="At Shipping Company Hub"
            )
        return True

    # تعديل action_out_for_delivery (بعد Shipping Company Hub)
    def action_out_for_delivery(self):
        for record in self:
            if record.state != 'shipping_company_hub':
                raise UserError(_('Shipment must be at Shipping Company Hub first!'))
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
        """معالجة المرتجع مع إلغاء الفواتير القديمة وإنشاء جديدة"""
        for record in self:
            # تغيير الحالة
            record.state = 'returned'

            # معالجة الفواتير إذا لم تتم المعالجة بعد
            if not record.is_return_processed:
                record.process_return_invoices()

            record.message_post(
                body="Shipment has been returned - Penalties applied",
                subject="Returned with Penalties"
            )
        return True

    def process_return_invoices(self):
        """إلغاء الفواتير القديمة وإنشاء جديدة مع الغرامات"""
        self.ensure_one()

        # 1. إلغاء فواتير العميل القديمة
        customer_invoices = self.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
        for invoice in customer_invoices:
            if invoice.state == 'posted':
                # إنشاء إشعار دائن أولاً
                invoice.button_draft()
            invoice.button_cancel()

        # 2. إلغاء فواتير المورد القديمة
        vendor_bills = self.vendor_bill_ids.filtered(lambda bill: bill.state != 'cancel')
        for bill in vendor_bills:
            if bill.state == 'posted':
                bill.button_draft()
            bill.button_cancel()

        # 3. إنشاء فاتورة عميل جديدة مع الغرامة
        if self.sender_id:
            customer_invoice = self._create_return_customer_invoice()

        # 4. إنشاء فاتورة مورد جديدة مع الغرامة
        if self.shipping_company_id:
            vendor_bill = self._create_return_vendor_bill()

        # وضع علامة أن المرتجع تم معالجته
        self.is_return_processed = True

        return True

    def _create_return_customer_invoice(self):
        """إنشاء فاتورة عميل للمرتجع مع الغرامة المعدلة - بدون COD"""
        self.ensure_one()

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale')
        ], limit=1)

        if not journal:
            raise UserError(_('Please configure a sales journal first!'))

        # تحديد من يدفع
        invoice_partner = self.sender_id

        # حساب المبالغ المعدلة
        # الأساس للغرامة: Company Base Cost + Company Weight Cost فقط
        company_base_cost = self.company_base_cost or 0
        company_weight_cost = self.company_weight_cost or 0

        # الأساس الذي ستُحسب عليه الغرامة (شحن + وزن فقط)
        base_for_penalty = company_base_cost + company_weight_cost

        # حساب الغرامة على الأساس المحدد
        penalty_rate = self.shipping_company_id.return_penalty_percentage / 100
        penalty_amount = base_for_penalty * penalty_rate

        # الرسوم الإضافية التي لا تدخل في حساب الغرامة
        # لا نضيف رسوم COD في المرتجعات
        pickup_fee = self.pickup_fee or 0
        additional_fees = self.total_additional_fees or 0
        discount = self.discount_amount or 0

        # إنشاء سطور الفاتورة
        invoice_lines = []

        # السطر الأول: السعر الأساسي + الوزن (التي عليها الغرامة)
        invoice_lines.append((0, 0, {
            'name': f"Shipping Service (RETURNED) - Order #{self.order_number}\n"
                    f"From: {self.sender_city} To: {self.recipient_city}\n"
                    f"Company Base Cost ({company_base_cost:.2f}) + Weight Cost ({company_weight_cost:.2f})",
            'quantity': 1,
            'price_unit': base_for_penalty,
            'account_id': self._get_income_account().id,
        }))

        # السطر الثاني: غرامة الإرجاع
        invoice_lines.append((0, 0, {
            'name': f"Return Penalty ({self.shipping_company_id.return_penalty_percentage:.0f}%)\n"
                    "Penalty charges on base shipping and weight cost",
            'quantity': 1,
            'price_unit': penalty_amount,
            'account_id': self._get_income_account().id,
        }))

        # السطر الثالث: رسوم الاستلام (بدون غرامة)
        if pickup_fee > 0:
            invoice_lines.append((0, 0, {
                'name': f"Pickup Fee\n"
                        "Pickup service charges (no penalty)",
                'quantity': 1,
                'price_unit': pickup_fee,
                'account_id': self._get_income_account().id,
            }))

        # السطر الرابع: رسوم إضافية أخرى (بدون غرامة)
        if additional_fees > 0:
            invoice_lines.append((0, 0, {
                'name': f"Additional Services\n"
                        "Other additional service charges (no penalty)",
                'quantity': 1,
                'price_unit': additional_fees,
                'account_id': self._get_income_account().id,
            }))

        # السطر الخامس: الخصم إن وجد
        if discount > 0:
            invoice_lines.append((0, 0, {
                'name': f"Discount\n"
                        "Applied discount",
                'quantity': 1,
                'price_unit': -discount,  # سالب لأنه خصم
                'account_id': self._get_income_account().id,
            }))

        # حساب الإجمالي - بدون COD
        total_amount = base_for_penalty + penalty_amount + pickup_fee + additional_fees - discount

        # إنشاء الفاتورة
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': invoice_partner.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'currency_id': self.env.company.currency_id.id,
            'shipment_id': self.id,
            'ref': f"RETURN-{self.order_number}",
            'narration': f"Return Invoice for Shipment {self.order_number}\n"
                         f"⚠️ This shipment was returned\n\n"
                         f"=== WITH PENALTY ({self.shipping_company_id.return_penalty_percentage:.0f}%) ===\n"
                         f"Company Base Cost: {company_base_cost:.2f} EGP\n"
                         f"Company Weight Cost: {company_weight_cost:.2f} EGP\n"
                         f"Subtotal for penalty: {base_for_penalty:.2f} EGP\n"
                         f"Penalty Amount: {penalty_amount:.2f} EGP\n\n"
                         f"=== WITHOUT PENALTY ===\n"
                         f"Pickup Fee: {pickup_fee:.2f} EGP\n"
                         f"Additional Fees: {additional_fees:.2f} EGP\n"
                         f"Discount: -{discount:.2f} EGP\n\n"
                         f"=== TOTAL ===\n"
                         f"Total Amount: {total_amount:.2f} EGP\n"
                         f"Note: COD fees not included in return invoices",
            'invoice_line_ids': invoice_lines,
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        return invoice

    def _create_return_vendor_bill(self):
        """إنشاء فاتورة مورد للمرتجع مع الغرامة المعدلة"""
        self.ensure_one()

        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase')
        ], limit=1)

        if not journal:
            raise UserError(_('Please configure a purchase journal first!'))

        vendor_partner = self._get_shipping_vendor_partner()

        # حساب المبالغ المعدلة لفاتورة المورد
        # قيمة الشحن الأساسية + قيمة الوزن فقط (بدون COD fee أو insurance)
        base_vendor_amount = self.base_shipping_cost + self.weight_shipping_cost

        # حساب الغرامة حسب النسبة المحددة في إعدادات الشركة
        penalty_rate = self.shipping_company_id.return_penalty_percentage / 100
        penalty_amount = base_vendor_amount * penalty_rate

        # الإجمالي
        total_vendor_amount = base_vendor_amount + penalty_amount

        # إنشاء سطور الفاتورة
        invoice_lines = []

        # السطر الأول: التكلفة الأساسية (شحن + وزن)
        invoice_lines.append((0, 0, {
            'name': f"Shipping Service (RETURNED) - {self.order_number}\n"
                    f"From: {self.sender_city} To: {self.recipient_city}\n"
                    f"Base Shipping: {self.base_shipping_cost:.2f} EGP\n"
                    f"Weight Cost: {self.weight_shipping_cost:.2f} EGP",
            'quantity': 1,
            'price_unit': base_vendor_amount,
            'account_id': self._get_expense_account().id,
        }))

        # السطر الثاني: غرامة الإرجاع حسب نسبة الشركة
        invoice_lines.append((0, 0, {
            'name': f"Return Penalty ({self.shipping_company_id.return_penalty_percentage:.0f}%)\n"
                    "Penalty charges for returned shipment",
            'quantity': 1,
            'price_unit': penalty_amount,
            'account_id': self._get_expense_account().id,
        }))

        # إنشاء الفاتورة
        vendor_bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor_partner.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'currency_id': self.env.company.currency_id.id,
            'shipment_vendor_id': self.id,
            'ref': f"RETURN-{self.order_number}",
            'narration': f"Return Bill for Shipment {self.order_number}\n"
                         f"⚠️ This shipment was returned\n"
                         f"Base Cost (Shipping + Weight): {base_vendor_amount:.2f} EGP\n"
                         f"Return penalty ({self.shipping_company_id.return_penalty_percentage:.0f}%): {penalty_amount:.2f} EGP\n"
                         f"Total Amount: {total_vendor_amount:.2f} EGP\n"
                         f"Note: COD and Insurance fees excluded from penalty calculation",
            'invoice_line_ids': invoice_lines,
        }

        vendor_bill = self.env['account.move'].create(vendor_bill_vals)
        vendor_bill.action_post()
        return vendor_bill

    def _get_expense_account(self):
        """الحصول على حساب المصروفات"""
        account = self.env['account.account'].search([
            ('account_type', '=', 'expense')
        ], limit=1)

        if not account:
            raise UserError(_('No expense account found!'))

        return account

    def action_cancel(self):
        """إلغاء الشحنة مع معالجة الفواتير مثل المرتجعات"""
        for record in self:
            # تغيير الحالة
            record.state = 'cancelled'

            # معالجة الفواتير إذا لم تتم المعالجة بعد
            if not record.is_return_processed:
                record.process_cancel_invoices()

            record.message_post(
                body="Shipment has been cancelled - Penalties applied",
                subject="Cancelled with Penalties"
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


class ShipmentOrder(models.Model):
    _inherit = 'shipment.order'

    # ===== حقول المواقع الجديدة للمستلم =====
    recipient_governorate_new_id = fields.Many2one(
        'egypt.governorate',
        string='Governorate',
        tracking=True
    )

    recipient_area_id = fields.Many2one(
        'egypt.governorate.area',
        string='Area',
        domain="[('governorate_id', '=', recipient_governorate_new_id)]",
        tracking=True
    )

    recipient_city_district_id = fields.Many2one(
        'egypt.governorate.city',
        string='City/District',
        domain="[('area_id', '=', recipient_area_id)]",
        tracking=True
    )

    # ===== حقول المواقع الجديدة للمرسل =====
    sender_governorate_new_id = fields.Many2one(
        'egypt.governorate',
        string='Sender Governorate',
        tracking=True
    )

    sender_area_id = fields.Many2one(
        'egypt.governorate.area',
        string='Sender Area',
        domain="[('governorate_id', '=', sender_governorate_new_id)]",
        tracking=True
    )

    sender_city_district_id = fields.Many2one(
        'egypt.governorate.city',
        string='Sender City/District',
        domain="[('area_id', '=', sender_area_id)]",
        tracking=True
    )

    @api.onchange('recipient_governorate_new_id')
    def _onchange_recipient_governorate_new(self):
        """عند تغيير المحافظة، امسح المنطقة والمدينة"""
        if self.recipient_governorate_new_id:
            # ربط مع المحافظة القديمة
            if self.recipient_governorate_new_id.state_id:
                self.recipient_governorate_id = self.recipient_governorate_new_id.state_id

            # امسح الحقول التابعة
            self.recipient_area_id = False
            self.recipient_city_district_id = False

            # حدث حساب الشحن
            if hasattr(self, '_onchange_calculate_shipping'):
                self._onchange_calculate_shipping()
        else:
            self.recipient_area_id = False
            self.recipient_city_district_id = False

    @api.onchange('recipient_area_id')
    def _onchange_recipient_area(self):
        """عند تغيير المنطقة، امسح المدينة"""
        if self.recipient_area_id:
            self.recipient_city_district_id = False
            # يمكنك استخدام اسم المنطقة في الحقل القديم
            self.recipient_city = self.recipient_area_id.name
        else:
            self.recipient_city_district_id = False

    @api.onchange('recipient_city_district_id')
    def _onchange_recipient_city_district(self):
        """عند اختيار المدينة، حدث حقل المدينة القديم"""
        if self.recipient_city_district_id:
            # دمج اسم المنطقة والمدينة
            full_location = f"{self.recipient_area_id.name}, {self.recipient_city_district_id.name}"
            self.recipient_city = full_location

    @api.onchange('sender_governorate_new_id')
    def _onchange_sender_governorate_new(self):
        """عند تغيير محافظة المرسل"""
        if self.sender_governorate_new_id:
            # ربط مع المحافظة القديمة
            if self.sender_governorate_new_id.state_id:
                self.sender_governorate_id = self.sender_governorate_new_id.state_id

            # امسح الحقول التابعة
            self.sender_area_id = False
            self.sender_city_district_id = False
        else:
            self.sender_area_id = False
            self.sender_city_district_id = False

    @api.onchange('sender_area_id')
    def _onchange_sender_area(self):
        """عند تغيير منطقة المرسل"""
        if self.sender_area_id:
            self.sender_city_district_id = False
            self.sender_city = self.sender_area_id.name
        else:
            self.sender_city_district_id = False

    @api.onchange('sender_city_district_id')
    def _onchange_sender_city_district(self):
        """عند اختيار مدينة المرسل"""
        if self.sender_city_district_id:
            full_location = f"{self.sender_area_id.name}, {self.sender_city_district_id.name}"
            self.sender_city = full_location


class ShipmentOrder(models.Model):
    _inherit = 'shipment.order'

    # ===== تحديث الحقول الأساسية =====

    # استخدام المحافظة الجديدة كحقل أساسي
    recipient_governorate_new_id = fields.Many2one(
        'egypt.governorate',
        string='Recipient Governorate',
        required=True,  # جعله مطلوب
        tracking=True
    )

    # الحقل القديم يصبح محسوب للتوافق
    recipient_governorate_id = fields.Many2one(
        'res.country.state',
        string='Old Governorate',
        compute='_compute_old_governorate',
        store=True,
        readonly=True
    )

    sender_governorate_new_id = fields.Many2one(
        'egypt.governorate',
        string='Sender Governorate',
        required=True,  # جعله مطلوب
        tracking=True
    )

    # الحقل القديم يصبح محسوب للتوافق
    sender_governorate_id = fields.Many2one(
        'res.country.state',
        string='Old Sender Governorate',
        compute='_compute_old_governorate',
        store=True,
        readonly=True
    )

    @api.depends('recipient_governorate_new_id', 'sender_governorate_new_id')
    def _compute_old_governorate(self):
        """ربط مع المحافظات القديمة للتوافق"""
        for record in self:
            if record.recipient_governorate_new_id and record.recipient_governorate_new_id.state_id:
                record.recipient_governorate_id = record.recipient_governorate_new_id.state_id
            else:
                record.recipient_governorate_id = False

            if record.sender_governorate_new_id and record.sender_governorate_new_id.state_id:
                record.sender_governorate_id = record.sender_governorate_new_id.state_id
            else:
                record.sender_governorate_id = False

    # ===== تحديث دوال الحساب =====

    @api.onchange('shipping_company_id', 'recipient_governorate_new_id')
    def _onchange_shipping_company_governorate_new(self):
        """عند تغيير شركة الشحن أو المحافظة الجديدة"""
        if self.shipping_company_id and self.recipient_governorate_new_id:
            # استخدام الدالة الجديدة
            price_config = self.shipping_company_id.get_governorate_price_new(
                self.recipient_governorate_new_id.id
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

                # تحديث وقت التسليم المتوقع
                if price_config.delivery_days_max and self.pickup_date:
                    from datetime import timedelta
                    self.expected_delivery = self.pickup_date + timedelta(days=price_config.delivery_days_max)

    @api.depends('sender_id.price_category_id', 'recipient_governorate_new_id', 'total_weight',
                 'pickup_type', 'pickup_fee', 'payment_method', 'cod_amount', 'company_cod_fee_amount',
                 'total_additional_fees')
    def _compute_company_costs(self):
        """حساب تكاليف الشركة باستخدام المحافظة الجديدة"""
        for record in self:
            if record.customer_category_id and record.recipient_governorate_new_id:
                # استخدام الدالة الجديدة
                cost_config = record.customer_category_id.get_governorate_cost_new(
                    record.recipient_governorate_new_id.id
                )

                if cost_config:
                    # حساب التكلفة الأساسية
                    record.company_base_cost = cost_config.base_cost

                    # حساب تكلفة الوزن مع احتساب الوزن المجاني
                    if record.total_weight > 0 and record.customer_category_id:
                        free_limit = record.customer_category_id.free_weight_limit or 0
                        if record.total_weight > free_limit:
                            chargeable_weight = record.total_weight - free_limit
                            record.company_weight_cost = chargeable_weight * record.customer_category_id.unified_cost_per_kg
                        else:
                            record.company_weight_cost = 0
                    else:
                        record.company_weight_cost = 0

                    # رسوم المناولة
                    record.company_handling_fee = cost_config.handling_fee if hasattr(cost_config,
                                                                                      'handling_fee') else 0

                    # حساب الإجمالي
                    record.total_company_cost = (
                            record.company_base_cost +
                            record.company_weight_cost +
                            record.company_handling_fee +
                            (record.pickup_fee if record.pickup_type == 'customer' else 0) +
                            (record.company_cod_fee_amount if record.payment_method == 'cod' else 0) +
                            record.total_additional_fees
                    )
                else:
                    # قيم افتراضية
                    record.company_base_cost = 0
                    record.company_weight_cost = 0
                    record.company_handling_fee = 0
                    record.total_company_cost = 0
            else:
                record.company_base_cost = 0
                record.company_weight_cost = 0
                record.company_handling_fee = 0
                record.total_company_cost = 0

    @api.onchange('shipping_company_id', 'recipient_governorate_new_id', 'total_weight',
                  'payment_method', 'cod_payment_type', 'cod_includes_shipping',
                  'insurance_required', 'total_value', 'total_company_cost',
                  'total_additional_fees', 'discount_amount')
    def _onchange_calculate_shipping_new(self):
        """حساب السعر عند تغيير الشركة أو المحافظة الجديدة"""
        if self.shipping_company_id and self.recipient_governorate_new_id:
            # الحصول على كونفيج السعر للمحافظة
            price_config = self.shipping_company_id.get_governorate_price_new(
                self.recipient_governorate_new_id.id
            )

            if price_config:
                # حساب السعر الأساسي
                self.base_shipping_cost = price_config.base_price

                # حساب تكلفة الوزن
                if self.total_weight > 0 and self.shipping_company_id:
                    free_limit = self.shipping_company_id.free_weight_limit or 0
                    if self.total_weight > free_limit:
                        chargeable_weight = self.total_weight - free_limit
                        self.weight_shipping_cost = chargeable_weight * self.shipping_company_id.unified_price_per_kg
                    else:
                        self.weight_shipping_cost = 0
                else:
                    self.weight_shipping_cost = 0

                # حساب رسوم التأمين
                if self.insurance_required and self.total_value > 0:
                    if hasattr(self.shipping_company_id, 'calculate_insurance_fee'):
                        insurance_result = self.shipping_company_id.calculate_insurance_fee(
                            product_value=self.total_value,
                            apply_insurance=True
                        )
                        self.insurance_fee_amount = insurance_result.get('fee_amount', 0)
                    else:
                        self.insurance_fee_amount = 0
                else:
                    self.insurance_fee_amount = 0

                # تحديث وقت التسليم المتوقع
                if price_config.delivery_days_max:
                    from datetime import datetime, timedelta
                    if self.pickup_date:
                        self.expected_delivery = self.pickup_date + timedelta(days=price_config.delivery_days_max)
            else:
                self.base_shipping_cost = 0
                self.weight_shipping_cost = 0
                self.insurance_fee_amount = 0

        # حساب COD
        if self.payment_method == 'cod' and self.shipping_company_id:
            self._compute_cod_details()

    @api.onchange('recipient_governorate_new_id')
    def _onchange_governorate_pricing_new(self):
        """إعادة حساب التكاليف عند تغيير المحافظة الجديدة"""
        if self.recipient_governorate_new_id:
            # حساب تكاليف الشركة
            self._compute_company_costs()
            # حساب أسعار العميل
            self._compute_customer_pricing()
            # حساب تكاليف الشحن
            self._onchange_calculate_shipping_new()
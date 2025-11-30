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

    # =====================================================
    # الحقول الأساسية
    # =====================================================
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

    # المحافظة القديمة (محسوب للتوافق)
    sender_governorate_id = fields.Many2one(
        'res.country.state',
        string='Old Sender Governorate',
        compute='_compute_old_governorate',
        store=True,
        readonly=True
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

    # ===== حقول المواقع الجديدة للمرسل =====
    sender_governorate_new_id = fields.Many2one(
        'egypt.governorate',
        string='Sender Governorate',
        required=True,
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

    # معلومات المستلم
    recipient_id = fields.Many2one('res.partner', string='Recipient', required=True, tracking=True)
    recipient_name = fields.Char(string='Recipient Name', required=True)
    recipient_phone = fields.Char(string='Recipient Phone', required=True)
    recipient_mobile = fields.Char(string='Recipient Mobile')
    recipient_email = fields.Char(string='Recipient Email')
    recipient_address = fields.Text(string='Delivery Address', required=True)

    # المحافظة القديمة (محسوب للتوافق)
    recipient_governorate_id = fields.Many2one(
        'res.country.state',
        string='Old Governorate',
        compute='_compute_old_governorate',
        store=True,
        readonly=True
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

    # ===== حقول المواقع الجديدة للمستلم =====
    recipient_governorate_new_id = fields.Many2one(
        'egypt.governorate',
        string='Recipient Governorate',
        required=True,
        tracking=True
    )

    recipient_area_id = fields.Many2one(
        'egypt.governorate.area',
        string='City',
        domain="[('governorate_id', '=', recipient_governorate_new_id)]",
        tracking=True
    )

    recipient_city_district_id = fields.Many2one(
        'egypt.governorate.city',
        string='Area',
        domain="[('area_id', '=', recipient_area_id)]",
        tracking=True
    )

    # تفاصيل الشحن
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

    # شركة الشحن
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
    ], string='COD Payment Type',
        help='How the customer will pay to the delivery person')

    cod_includes_shipping = fields.Boolean(
        string='COD Includes Shipping',
        default=False,
        help='If checked, the customer will pay shipping cost on delivery too'
    )

    cod_calculation_details = fields.Text(
        string='COD Calculation Details',
        compute='_compute_cod_details',
        store=True
    )

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

    use_city_price_for_company = fields.Boolean(
        string='Use City Price for Company Cost',
        default=True,
        help='If checked, company_base_cost will be calculated from city/district pricing instead of governorate pricing'
    )

    use_city_price_for_shipping = fields.Boolean(
        string='Use City Price for Shipping Cost',
        default=True,
        help='If checked, base_shipping_cost will be calculated from city/district pricing instead of governorate pricing'
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
        ('torood_hub', 'Torood Hub'),
        ('in_transit', 'In Transit'),
        ('shipping_company_hub', 'Shipping Company Hub'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, group_expand='_read_group_state')

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
    ], string='Prepaid Payer', default='sender', help='Who will pay for prepaid shipment')

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

    cod_amount_sheet_excel = fields.Integer(
        string='COD Amount Export To shipping Company',
        compute='_compute_cod_amount',
        store=True,
        readonly=False,
        help='Auto-calculated: Product Value + Company Charges')

    include_services_in_cod = fields.Boolean(
        string='Include Services & Pickup in COD',
        default=False,
        help='If checked, Services Fees and Pickup Fee will be added to COD amount'
    )

    insurance_required = fields.Boolean(string='Insurance Required')
    insurance_value = fields.Float(string='Insurance Value')

    tracking_number = fields.Char(string='Tracking Number', tracking=True, copy=False, readonly=True, index=True)
    tracking_url = fields.Char(string='Tracking URL', compute='_compute_tracking_url')
    tracking_number_shipping_company = fields.Char(string='shipping Company Tracking Number', tracking=True, copy=False,
                                                   index=True)

    mark_as_packing = fields.Boolean(
        string='Mark as Packing',
        default=False,
        help='Enable if this shipment requires packing service'
    )

    allow_the_package_to_be_opened = fields.Boolean(
        string='Allow Package to be Opened',
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
    ], string='Pickup Type', default='customer', required=True, tracking=True,
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

    company_insurance_fee_amount = fields.Float(
        string='Company Insurance Fee',
        compute='_compute_company_insurance_fee',
        store=True,
        readonly=True,
        help='Insurance fee for the company (profit margin)'
    )

    company_insurance_calculation_details = fields.Text(
        string='Company Insurance Details',
        compute='_compute_company_insurance_fee',
        store=True
    )

    company_insurance_type = fields.Char(
        string='Company Insurance Type',
        compute='_compute_company_insurance_fee',
        store=True
    )

    customer_return_penalty = fields.Float(
        string='Customer Return Penalty',
        compute='_compute_customer_return_penalty',
        store=True,
        help='Penalty charged to customer based on their category'
    )

    hours_since_creation = fields.Float(
        string='Hours Since Creation',
        compute='_compute_hours_since_creation',
        store=False
    )

    is_no_action = fields.Boolean(
        string='No Action',
        compute='_compute_is_no_action',
        search='_search_no_action',
        store=False
    )

    is_overdue = fields.Boolean(
        string='Overdue Delivery',
        compute='_compute_is_overdue',
        search='_search_overdue',
        store=False,
        help='Order has passed expected delivery date without being delivered'
    )

    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_is_overdue',
        store=False
    )

    source = fields.Selection([
        ('manual', 'Manual'),
        ('website', 'Website'),
        ('api', 'API'),
        ('import', 'Import'),
    ], string='Order Source', default='manual', tracking=True)

    # =====================================================
    # Compute Methods
    # =====================================================

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

    @api.depends('expected_delivery', 'state')
    def _compute_is_overdue(self):
        """تحديد إذا كان الطلب تجاوز تاريخ التسليم المتوقع"""
        for record in self:
            if (record.expected_delivery and
                    fields.Datetime.now() > record.expected_delivery and
                    record.state not in ['delivered', 'cancelled', 'returned']):
                record.is_overdue = True
                time_diff = fields.Datetime.now() - record.expected_delivery
                record.days_overdue = time_diff.days
            else:
                record.is_overdue = False
                record.days_overdue = 0

    def _search_overdue(self, operator, value):
        """البحث عن الطلبات المتأخرة"""
        current_time = fields.Datetime.now()
        if operator in ['=', '!='] and isinstance(value, bool):
            if (operator == '=' and value) or (operator == '!=' and not value):
                return [
                    '&',
                    ('expected_delivery', '!=', False),
                    ('expected_delivery', '<', current_time),
                    ('state', 'not in', ['delivered', 'cancelled', 'returned'])
                ]
            else:
                return [
                    '|',
                    ('expected_delivery', '=', False),
                    '|',
                    ('expected_delivery', '>=', current_time),
                    ('state', 'in', ['delivered', 'cancelled', 'returned'])
                ]
        return []

    @api.model
    def action_view_overdue_orders(self):
        """عرض الطلبات المتأخرة عن تاريخ التسليم المتوقع"""
        current_time = fields.Datetime.now()
        return {
            'name': _('Overdue Deliveries'),
            'type': 'ir.actions.act_window',
            'res_model': 'shipment.order',
            'view_mode': 'tree,form,kanban,calendar',
            'domain': [
                ('expected_delivery', '!=', False),
                ('expected_delivery', '<', current_time),
                ('state', 'not in', ['delivered', 'cancelled', 'returned'])
            ],
            'context': {
                'search_default_group_by_state': 1,
                'overdue_filter': True,
                'search_default_sort_by_overdue': True
            },
            'help': _('''
                <p class="o_view_nocontent_smiling_face">
                    Great! No overdue deliveries
                </p>
                <p>
                    Orders shown here have passed their expected delivery date 
                    without being delivered, cancelled, or returned.
                </p>
            ''')
        }

    @api.depends('create_date')
    def _compute_hours_since_creation(self):
        """حساب عدد الساعات منذ إنشاء الطلب"""
        for record in self:
            if record.create_date:
                time_diff = fields.Datetime.now() - record.create_date
                record.hours_since_creation = time_diff.total_seconds() / 3600
            else:
                record.hours_since_creation = 0

    @api.depends('state', 'create_date')
    def _compute_is_no_action(self):
        """تحديد إذا كان الطلب بدون حركة لمدة 24 ساعة"""
        for record in self:
            if record.create_date and record.state == 'draft':
                time_diff = fields.Datetime.now() - record.create_date
                hours_passed = time_diff.total_seconds() / 3600
                record.is_no_action = hours_passed >= 24
            else:
                record.is_no_action = False

    def _search_no_action(self, operator, value):
        """البحث عن الطلبات بدون حركة"""
        if operator in ['=', '!='] and isinstance(value, bool):
            threshold_date = fields.Datetime.now() - timedelta(hours=24)
            if (operator == '=' and value) or (operator == '!=' and not value):
                return [
                    '&',
                    ('state', '=', 'draft'),
                    ('create_date', '<=', threshold_date)
                ]
            else:
                return [
                    '|',
                    ('state', '!=', 'draft'),
                    ('create_date', '>', threshold_date)
                ]
        return []

    @api.model
    def action_view_no_action_orders(self):
        """عرض الطلبات التي لم تتحرك لمدة 24 ساعة"""
        threshold_date = fields.Datetime.now() - timedelta(hours=24)
        return {
            'name': _('No Action Orders (24+ Hours)'),
            'type': 'ir.actions.act_window',
            'res_model': 'shipment.order',
            'view_mode': 'tree,form,kanban',
            'domain': [
                ('state', '=', 'draft'),
                ('create_date', '<=', threshold_date)
            ],
            'context': {
                'search_default_group_by_state': 1,
                'no_action_filter': True
            },
            'help': _('''
               <p class="o_view_nocontent_smiling_face">
                   No orders pending action for more than 24 hours
               </p>
               <p>
                   Orders shown here have been in Draft state for more than 24 hours without any action.
               </p>
           ''')
        }

    @api.depends('state', 'customer_category_id', 'company_base_cost', 'company_weight_cost',
                 'pickup_fee', 'total_additional_fees')
    def _compute_customer_return_penalty(self):
        """حساب غرامة العميل بناءً على المكونات المحددة في فئته"""
        for record in self:
            if record.state == 'returned' and record.customer_category_id:
                category = record.customer_category_id

                # 🆕 بناء المبلغ الأساسي بناءً على الـ boolean fields
                base_for_penalty = 0

                # Company base cost
                if category.include_base_in_customer_penalty:
                    base_for_penalty += (record.company_base_cost or 0)

                # Company weight cost
                if category.include_weight_in_customer_penalty:
                    base_for_penalty += (record.company_weight_cost or 0)

                # Pickup fee
                if category.include_pickup_in_customer_penalty:
                    base_for_penalty += (record.pickup_fee or 0)

                # Additional services
                if category.include_additional_in_customer_penalty:
                    base_for_penalty += (record.total_additional_fees or 0)

                # حساب الغرامة
                penalty_rate = category.customer_return_penalty_percentage / 100
                record.customer_return_penalty = base_for_penalty * penalty_rate
            else:
                record.customer_return_penalty = 0

    @api.model
    def _get_default_pickup_date(self):
        """حساب pickup date الافتراضي عند فتح الفورم"""
        if hasattr(self, '_calculate_pickup_date'):
            pickup_date, note = self._calculate_pickup_date()
            return pickup_date
        else:
            return fields.Datetime.now()

    @api.depends('state', 'shipping_company_id', 'company_base_cost', 'company_weight_cost')
    def _compute_return_penalty(self):
        """حساب غرامة المرتجع بناءً على المكونات المحددة في شركة الشحن"""
        for record in self:
            if record.state == 'returned' and record.shipping_company_id:
                if record.shipping_company_id.return_penalty_enabled:
                    # 🆕 بناء المبلغ الأساسي بناءً على الـ boolean fields
                    base_for_penalty = 0

                    # Base shipping cost
                    if record.shipping_company_id.include_base_in_penalty:
                        base_for_penalty += (record.base_shipping_cost or 0)

                    # Weight shipping cost
                    if record.shipping_company_id.include_weight_in_penalty:
                        base_for_penalty += (record.weight_shipping_cost or 0)

                    # حساب الغرامة
                    penalty_rate = record.shipping_company_id.return_penalty_percentage / 100
                    record.return_penalty_amount = base_for_penalty * penalty_rate
                else:
                    record.return_penalty_amount = 0
            else:
                record.return_penalty_amount = 0

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
                record.invoice_partner_id = record.sender_id
            else:
                record.invoice_partner_id = record.sender_id

    @api.depends('insurance_required', 'insurance_value', 'total_value', 'shipping_company_id',
                 'insurance_fee_amount', 'cod_amount_sheet_excel')
    def _compute_insurance_details(self):
        """حساب وعرض تفاصيل التأمين بشكل موحّد"""
        for record in self:
            if not record.insurance_required or not record.shipping_company_id:
                record.insurance_calculation_details = 'Insurance not required'
                record.insurance_type_used = ''
                continue

            company = record.shipping_company_id
            details = []
            base_for_insurance = record.insurance_value or record.total_value or record.cod_amount_sheet_excel or 0.0

            details.append(f"Company: {company.name}")
            details.append(f"Insurance Type: {company.insurance_type}")

            if company.insurance_type == 'percentage':
                rate = float(company.insurance_percentage or 0.0)
                calculated_fee = base_for_insurance * rate / 100.0
                details.append(f"Insurance Rate: {rate:.2f}%")
                details.append(f"Calculation: {base_for_insurance:.2f} × {rate:.2f}% = {calculated_fee:.2f} EGP")
            else:
                fixed_amt = float(company.insurance_fixed_amount or 0.0)
                calculated_fee = fixed_amt
                details.append(f"Fixed Insurance Fee: {fixed_amt:.2f} EGP")

            min_value = float(company.insurance_minimum_value or 0.0)
            details.append(f"Minimum Value/Fee Threshold: {min_value:.2f} EGP")
            details.append(f"Product Value (Base): {base_for_insurance:.2f} EGP")

            stored_fee = float(record.insurance_fee_amount or 0.0)
            if abs(stored_fee - calculated_fee) > 0.01:
                details.append("⚠️ WARNING: Mismatch in insurance calculation!")
                details.append(f"   Stored:   {stored_fee:.2f} EGP")
                details.append(f"   Expected: {calculated_fee:.2f} EGP")
            else:
                details.append(f"✓ Final Insurance Fee: {stored_fee:.2f} EGP")

            record.insurance_calculation_details = '\n'.join(details)
            record.insurance_type_used = company.insurance_type or ''

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

            payment_type = record.cod_payment_type if record.cod_payment_type else 'cash'

            result = record.shipping_company_id.calculate_cod_fee(
                cod_amount=record.cod_amount_sheet_excel,
                payment_type=payment_type,
                include_shipping_cost=record.cod_includes_shipping,
                shipping_cost=record.shipping_cost
            )

            record.cod_fee_amount = result['fee_amount']
            record.cod_base_amount = result['total_cod_amount']
            record.cod_percentage_used = result['percentage_used']
            record.cod_fixed_fee_used = result.get('fixed_fee_used', 0)

            details = []
            details.append(f"COD Amount (Sheet Excel): {record.cod_amount_sheet_excel:.2f} EGP")

            if record.cod_includes_shipping:
                details.append(f"Shipping Cost: {record.shipping_cost:.2f} EGP")
                details.append(f"Total COD Base: {result['total_cod_amount']:.2f} EGP")

            details.append(f"Payment Type: {payment_type.upper()}")

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
        """حساب الإجماليات بدون استدعاء دالة الشحن (الـ onchange يقوم بالمهمة)"""
        for record in self:
            record.total_weight = sum(line.total_weight for line in record.shipment_line_ids)
            record.total_volume = sum(line.volume * line.quantity for line in record.shipment_line_ids)
            record.total_value = sum(line.total_value for line in record.shipment_line_ids)

    @api.depends('base_shipping_cost', 'weight_shipping_cost', 'cod_fee_amount', 'insurance_fee_amount')
    def _compute_shipping_cost(self):
        """حساب إجمالي تكلفة الشحن بدون pickup fee"""
        for record in self:
            total = (
                    (record.base_shipping_cost or 0) +
                    (record.weight_shipping_cost or 0) +
                    (record.cod_fee_amount or 0) +
                    (record.insurance_fee_amount or 0)
            )
            record.shipping_cost = total

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

    @api.depends('total_value', 'total_company_cost', 'total_additional_fees', 'discount_amount',
                 'payment_method', 'company_base_cost', 'company_weight_cost', 'include_services_in_cod')
    def _compute_cod_amount(self):
        """حساب مبلغ COD تلقائياً = قيمة البضاعة + تكلفة الشركة"""
        for record in self:
            if record.payment_method == 'cod':
                record.cod_amount = record.total_value
                if record.include_services_in_cod:
                    record.cod_amount_sheet_excel = round(record.total_value + record.total_company_cost)
                else:
                    record.cod_amount_sheet_excel = round(record.total_value + record.company_base_cost)
            else:
                record.cod_amount = 0

    def _compute_company_costs(self):
        """حساب تكاليف الشركة بناءً على فئة العميل والمحافظة/المدينة - محدث مع effective_free_weight_limit"""
        for record in self:
            if record.customer_category_id and record.recipient_governorate_id:
                cost_config = None

                # ===== التحقق من استخدام أسعار المدن =====
                if record.use_city_price_for_company and record.recipient_city_district_id:
                    # استخدام أسعار المدينة/الحي
                    cost_config = record.customer_category_id.get_city_district_cost(
                        record.recipient_city_district_id.id
                    )

                # إذا لم يوجد سعر للمدينة أو لم يتم تفعيل الخيار، استخدم المحافظة
                if not cost_config:
                    # الحصول على كونفيج التكلفة للمحافظة
                    cost_config = record.customer_category_id.get_governorate_cost(
                        record.recipient_governorate_id.id
                    )

                if cost_config:
                    # حساب التكلفة الأساسية من المدينة أو المحافظة
                    record.company_base_cost = cost_config.base_cost

                    # ✅ التعديل: حساب تكلفة الوزن باستخدام effective من cost_config
                    if record.total_weight > 0:
                        # ✅ استخدم effective_free_weight_limit من cost_config
                        free_limit = cost_config.effective_free_weight_limit
                        chargeable_weight = max(0, record.total_weight - free_limit)

                        if chargeable_weight > 0:
                            # ✅ استخدم effective_cost_per_kg من cost_config
                            record.company_weight_cost = chargeable_weight * cost_config.effective_cost_per_kg
                        else:
                            record.company_weight_cost = 0
                    else:
                        record.company_weight_cost = 0

                    # رسوم المناولة
                    record.company_handling_fee = cost_config.handling_fee if hasattr(cost_config,
                                                                                      'handling_fee') else 0

                    # === إضافة Company Insurance Fee ===
                    record.total_company_cost = (
                            record.company_base_cost +
                            record.company_weight_cost +
                            record.company_handling_fee +
                            (record.pickup_fee if record.pickup_type == 'customer' else 0) +
                            (record.company_cod_fee_amount if record.payment_method == 'cod' else 0) +
                            (record.company_insurance_fee_amount if record.insurance_required else 0) +
                            record.total_additional_fees
                    )
                else:
                    # قيم افتراضية
                    record.company_base_cost = 0
                    record.company_weight_cost = 0
                    record.company_handling_fee = 0
                    record.total_company_cost = (
                            (record.pickup_fee if record.pickup_type == 'customer' else 0) +
                            (record.company_cod_fee_amount if record.payment_method == 'cod' else 0) +
                            (record.company_insurance_fee_amount if record.insurance_required else 0) +
                            record.total_additional_fees
                    )
            else:
                record.company_base_cost = 0
                record.company_weight_cost = 0
                record.company_handling_fee = 0
                record.total_company_cost = (
                        (record.pickup_fee if record.pickup_type == 'customer' else 0) +
                        (record.company_cod_fee_amount if record.payment_method == 'cod' else 0) +
                        (record.company_insurance_fee_amount if record.insurance_required else 0) +
                        record.total_additional_fees
                )

    # =====================================================
    # Onchange Methods
    # =====================================================

    @api.onchange('recipient_governorate_new_id')
    def _onchange_recipient_governorate_new(self):
        """عند تغيير المحافظة، امسح المنطقة والمدينة"""
        if self.recipient_governorate_new_id:
            if self.recipient_governorate_new_id.state_id:
                self.recipient_governorate_id = self.recipient_governorate_new_id.state_id
            self.recipient_area_id = False
            self.recipient_city_district_id = False
        else:
            self.recipient_area_id = False
            self.recipient_city_district_id = False

    @api.onchange('recipient_area_id')
    def _onchange_recipient_area(self):
        """عند تغيير المنطقة، امسح المدينة"""
        if self.recipient_area_id:
            self.recipient_city_district_id = False
            self.recipient_city = self.recipient_area_id.name
        else:
            self.recipient_city_district_id = False

    @api.onchange('recipient_city_district_id')
    def _onchange_recipient_city_district(self):
        """عند اختيار المدينة، حدث حقل المدينة القديم"""
        if self.recipient_city_district_id:
            full_location = f"{self.recipient_area_id.name}, {self.recipient_city_district_id.name}"
            self.recipient_city = full_location

    @api.onchange('sender_governorate_new_id')
    def _onchange_sender_governorate_new(self):
        """عند تغيير محافظة المرسل"""
        if self.sender_governorate_new_id:
            if self.sender_governorate_new_id.state_id:
                self.sender_governorate_id = self.sender_governorate_new_id.state_id
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

    @api.onchange('shipping_company_id', 'recipient_governorate_id')
    def _onchange_shipping_company_governorate(self):
        """عند تغيير شركة الشحن أو المحافظة - محدث"""
        if self.shipping_company_id and self.recipient_governorate_id:
            price_config = self.shipping_company_id.get_governorate_price(
                self.recipient_governorate_id.id
            )

            if price_config:
                cod_amount = self.cod_amount if self.payment_method == 'cod' else 0
                shipping_cost = price_config.calculate_shipping_price(
                    weight=self.total_weight,
                    cod_amount=cod_amount,
                    service_type='normal'
                )
                self.shipping_cost = shipping_cost

                if price_config.delivery_days_max and self.pickup_date:
                    self.expected_delivery = self.pickup_date + timedelta(days=price_config.delivery_days_max)
                elif price_config.delivery_days_max:
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

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        """عند تغيير طريقة الدفع"""
        if self.payment_method == 'prepaid':
            if not self.prepaid_payer:
                self.prepaid_payer = 'sender'
        elif self.payment_method == 'cod':
            self.prepaid_payer = False

    @api.onchange('pickup_type', 'shipping_company_id', 'sender_id')
    def _onchange_pickup_type(self):
        """تحديد رسوم الاستلام حسب النوع والفئة"""
        if self.pickup_type == 'customer':
            if self.sender_id and self.sender_id.price_category_id:
                category = self.sender_id.price_category_id
                if category.pickup_fee_enabled:
                    self.pickup_fee = category.pickup_fee_amount
                else:
                    self.pickup_fee = 0.0
            elif self.shipping_company_id:
                self.pickup_fee = 20.0
            else:
                self.pickup_fee = 20.0
        else:
            self.pickup_fee = 0.0

    @api.onchange('sender_id')
    def _onchange_sender_pickup_fee(self):
        """تطبيق رسوم الاستلام عند تغيير العميل"""
        if self.pickup_type == 'customer' and self.sender_id and self.sender_id.price_category_id:
            category = self.sender_id.price_category_id
            if category.pickup_fee_enabled:
                self.pickup_fee = category.pickup_fee_amount

    @api.onchange('insurance_required', 'insurance_value')
    def _onchange_insurance_required_direct(self):
        """تحديث فوري مباشر للتأمين"""
        if self.customer_category_id and self.recipient_governorate_id:
            cost_config = self.customer_category_id.get_governorate_cost(
                self.recipient_governorate_id.id
            )
            if cost_config:
                self.company_base_cost = cost_config.base_cost

                if self.total_weight > 0 and self.customer_category_id:
                    free_limit = self.customer_category_id.free_weight_limit or 0
                    if self.total_weight > free_limit:
                        chargeable_weight = self.total_weight - free_limit
                        self.company_weight_cost = chargeable_weight * self.customer_category_id.unified_cost_per_kg
                    else:
                        self.company_weight_cost = 0

        if self.payment_method == 'cod':
            if self.include_services_in_cod:
                self.cod_amount_sheet_excel = round(self.total_value + (self.total_company_cost or 0))
            else:
                self.cod_amount_sheet_excel = round(self.total_value + (self.company_base_cost or 0) + (
                        self.company_weight_cost or 0))

        if not self.insurance_required:
            self.insurance_fee_amount = 0
            self.company_insurance_fee_amount = 0
        else:
            base_for_insurance = self.insurance_value or self.total_value or self.cod_amount_sheet_excel or 0
            if self.shipping_company_id and base_for_insurance > 0:
                insurance_result = self.shipping_company_id.calculate_insurance_fee(
                    cod_amount_sheet_excel=base_for_insurance,
                    apply_insurance=True
                )
                self.insurance_fee_amount = insurance_result.get('fee_amount', 0)
            else:
                self.insurance_fee_amount = 0

            if self.customer_category_id and self.total_value > 0:
                category_result = self.customer_category_id.calculate_company_insurance_fee(
                    product_value=self.total_value,
                    apply_insurance=True
                )
                self.company_insurance_fee_amount = category_result.get('fee_amount', 0)

    @api.onchange('payment_method', 'total_value', 'total_company_cost', 'total_additional_fees',
                  'discount_amount', 'include_services_in_cod')
    def _onchange_cod_calculation(self):
        """تحديث COD amount عند تغيير طريقة الدفع أو الأسعار"""
        if self.payment_method == 'cod':
            self.cod_amount = self.total_value

            if self.include_services_in_cod:
                self.cod_amount_sheet_excel = round(self.total_value + self.total_company_cost)
            else:
                self.cod_amount_sheet_excel = round(
                    self.total_value + self.company_base_cost + self.company_weight_cost)

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

    @api.onchange('shipping_company_id', 'recipient_governorate_new_id', 'total_weight',
                  'payment_method', 'cod_payment_type', 'cod_includes_shipping',
                  'insurance_required', 'insurance_value',
                  'total_additional_fees', 'discount_amount', 'cod_amount_sheet_excel',
                  'use_city_price_for_shipping', 'recipient_city_district_id')
    def _onchange_calculate_shipping_new(self):
        """حساب السعر عند تغيير الشركة أو المحافظة/المدينة - محدث مع effective_free_weight_limit"""
        if self.shipping_company_id and self.recipient_governorate_new_id:
            price_config = None

            # ===== التحقق من استخدام أسعار المدن =====
            if self.use_city_price_for_shipping and self.recipient_city_district_id:
                # استخدام أسعار المدينة/الحي
                price_config = self.shipping_company_id.get_city_district_price(
                    self.recipient_city_district_id.id
                )

            # إذا لم يوجد سعر للمدينة أو لم يتم تفعيل الخيار، استخدم المحافظة
            if not price_config:
                # الحصول على كونفيج السعر للمحافظة
                price_config = self.shipping_company_id.get_governorate_price_new(
                    self.recipient_governorate_new_id.id
                )

            if price_config:
                # حساب السعر الأساسي من المدينة أو المحافظة
                self.base_shipping_cost = price_config.base_price

                # ✅ التعديل: حساب تكلفة الوزن باستخدام effective من price_config
                if self.total_weight > 0:
                    # ✅ استخدم effective_free_weight_limit من price_config
                    free_limit = price_config.effective_free_weight_limit
                    chargeable_weight = max(0, self.total_weight - free_limit)

                    if chargeable_weight > 0:
                        # ✅ استخدم effective_price_per_kg من price_config
                        price_per_kg = price_config.effective_price_per_kg
                        self.weight_shipping_cost = chargeable_weight * price_per_kg
                    else:
                        self.weight_shipping_cost = 0
                else:
                    self.weight_shipping_cost = 0

                # حساب رسوم التأمين
                base_for_insurance = self.insurance_value or self.total_value or self.cod_amount_sheet_excel or 0
                if self.insurance_required and base_for_insurance > 0 and self.shipping_company_id:
                    if hasattr(self.shipping_company_id, 'calculate_insurance_fee'):
                        insurance_result = self.shipping_company_id.calculate_insurance_fee(
                            cod_amount_sheet_excel=base_for_insurance,
                            apply_insurance=True
                        )
                        self.insurance_fee_amount = insurance_result.get('fee_amount', 0)
                    else:
                        self.insurance_fee_amount = 0
                else:
                    self.insurance_fee_amount = 0

                # تحديث وقت التسليم المتوقع
                if price_config.delivery_days_max:
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
            self._compute_company_costs()
            self._compute_customer_pricing()

    @api.onchange('use_city_price_for_shipping', 'recipient_city_district_id')
    def _onchange_city_pricing_shipping(self):
        """إعادة حساب تكاليف الشحن عند تغيير خيار المدينة"""
        pass

    # =====================================================
    # Helper Methods
    # =====================================================

    def action_recalculate_dates(self):
        """زر لإعادة حساب التواريخ"""
        self.ensure_one()

        if hasattr(self, '_calculate_pickup_date'):
            pickup_date, note = self._calculate_pickup_date(self.create_date or fields.Datetime.now())
            self.pickup_date = pickup_date
            self.pickup_date_calculated = True
            self.pickup_calculation_note = note

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

    def action_recalculate_fees(self):
        """زر لإعادة حساب الرسوم يدوياً شاملة COD"""
        self.ensure_one()
        if self.shipping_company_id and self.recipient_governorate_id:
            self._onchange_calculate_shipping_new()
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
                    'title': _('Missing Information'),
                    'message': _('Please select recipient governorate first'),
                    'type': 'warning',
                }
            }

        all_companies = self.env['shipping.company'].search([('active', '=', True)])

        if not all_companies:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Companies'),
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
                base_price = price_config.base_price
                free_limit = company.free_weight_limit or 0
                chargeable_weight = max(0, self.total_weight - free_limit)
                weight_cost = chargeable_weight * price_config.price_per_kg if price_config.price_per_kg else 0

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
            self._onchange_calculate_shipping_new()

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
                    'sticky': False,
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

    # =====================================================
    # CRUD Methods
    # =====================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-calculate pickup date"""

        for vals in vals_list:
            if vals.get('order_number', _('New')) == _('New'):
                vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or _('New')

            if 'pickup_date' not in vals or not vals.get('pickup_date'):
                try:
                    if hasattr(self, '_calculate_pickup_date'):
                        pickup_date, note = self._calculate_pickup_date()
                        vals['pickup_date'] = pickup_date
                        vals['pickup_date_calculated'] = True
                        vals['pickup_calculation_note'] = note
                        _logger.info(f"Auto-calculated pickup date: {pickup_date}")
                    else:
                        vals['pickup_date'] = fields.Datetime.now()
                        _logger.warning("_calculate_pickup_date not found, using current time")
                except Exception as e:
                    _logger.error(f"Error calculating pickup date: {str(e)}")
                    vals['pickup_date'] = fields.Datetime.now()

        return super().create(vals_list)

    # =====================================================
    # Action Methods
    # =====================================================

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
            if record.state != 'picked':
                raise UserError(_('Shipment must be Confirmed first!'))

            missing_fields = []

            if not record.tracking_number_shipping_company:
                missing_fields.append('Shipping Company Tracking Number')

            if not record.mark_as_packing:
                missing_fields.append('Mark as Packing must be checked')

            if not record.delivery_type:
                missing_fields.append('Delivery Type')

            if missing_fields:
                raise UserError(_(
                    'Cannot proceed to Picked Up status!\n\n'
                    'The following fields are required:\n• %s\n\n'
                    'Please fill in all required fields before proceeding.'
                ) % '\n• '.join(missing_fields))

            record.state = 'torood_hub'
            record.message_post(
                body=f"Shipment picked up - Tracking: {record.tracking_number_shipping_company}",
                subject="Pickup Completed"
            )

        return True

    def action_to_torood_hub_with_custom_export(self):
        """نقل الشحنة إلى Torood Hub مع التحقق والتصدير المخصص"""
        import base64
        import io

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter library: pip install xlsxwriter'))

        for record in self:
            missing_fields = []

            if not record.delivery_type:
                missing_fields.append('Delivery Type')

            if missing_fields:
                raise UserError(_(
                    'Order #%s is missing required fields:\n• %s\n\n'
                    'Please fill in all required fields before proceeding to Torood Hub.'
                ) % (record.order_number, '\n• '.join(missing_fields)))

            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'picked'
            record.message_post(
                body="Shipment arrived at Torood Hub - Excel exported",
                subject="At Torood Hub"
            )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Torood Hub Shipments')

        info_header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#FF9800',
            'font_color': 'white',
            'border': 1,
            'font_size': 12
        })

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#4CAF50',
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
            'bg_color': '#E8F5E9'
        })

        worksheet.merge_range(0, 0, 0, 8, 'Basic Information', info_header_format)
        worksheet.merge_range(0, 9, 0, 14, 'Receiver Information', info_header_format)
        worksheet.write(0, 15, 'Autres Informations', info_header_format)

        headers = [
            'S.O.', 'Goods type', 'Goods name', 'Quantity', 'Weight', 'COD',
            'Insure price', 'Whether to allow the package to be opened', 'Remark',
            'Name', 'Telephone', 'City', 'Area', 'Receivers address',
            'Receiver Email', 'Delivery Type'
        ]

        for col, header in enumerate(headers):
            worksheet.write(1, col, header, header_format)

        column_widths = [15, 15, 25, 10, 10, 12, 12, 30, 30, 20, 15, 15, 15, 35, 25, 15]
        for col, width in enumerate(column_widths[:len(headers)]):
            worksheet.set_column(col, col, width)

        row = 2

        for shipment in self:
            worksheet.write(row, 0, shipment.order_number or '', cell_format)

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

            goods_names = ', '.join([line.product_name for line in shipment.shipment_line_ids])
            worksheet.write(row, 2, goods_names or '', cell_format)

            total_qty = sum(line.quantity for line in shipment.shipment_line_ids) or 1
            worksheet.write(row, 3, total_qty, number_format)

            worksheet.write(row, 4, shipment.total_weight or 0, number_format)

            # COD = صفر في حالة prepaid أو credit (فقط cod يكون له قيمة)
            if shipment.payment_method == 'cod':
                cod_value = shipment.cod_amount_sheet_excel or 0
            else:
                # prepaid أو credit = صفر دائماً
                cod_value = 0
            worksheet.write(row, 5, cod_value, number_format)

            insure_price = (shipment.insurance_value or shipment.total_value or 0) if shipment.insurance_required else 0
            worksheet.write(row, 6, insure_price, number_format)

            allow_open = 'Yes' if shipment.allow_the_package_to_be_opened else 'No'
            worksheet.write(row, 7, allow_open, highlight_format if allow_open == 'Yes' else cell_format)

            worksheet.write(row, 8, shipment.notes or '', cell_format)

            worksheet.write(row, 9, shipment.recipient_name or '', cell_format)

            phone = shipment.recipient_mobile or shipment.recipient_phone or ''
            worksheet.write(row, 10, phone, cell_format)

            area = shipment.recipient_area_id.name if shipment.recipient_area_id else ''
            worksheet.write(row, 11, area, cell_format)

            city = shipment.recipient_city_district_id.name if shipment.recipient_city_district_id else ''
            worksheet.write(row, 12, city, cell_format)

            worksheet.write(row, 13, shipment.recipient_address or '', cell_format)

            worksheet.write(row, 14, shipment.recipient_email or '', cell_format)

            delivery_type_mapping = {
                'Deliver': 'Deliver',
                'Self_Pick-up': 'Self Pick-up'
            }
            delivery_type = delivery_type_mapping.get(shipment.delivery_type, shipment.delivery_type or 'Deliver')
            worksheet.write(row, 15, delivery_type, highlight_format)

            row += 1

        workbook.close()
        output.seek(0)

        attachment = self.env['ir.attachment'].create({
            'name': f'torood_hub_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self[0].id if len(self) == 1 else False,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_pickup(self):
        """استلام الشحنة من Torood Hub - مع التحقق من الحقول المطلوبة"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_('Shipment must be at Torood Hub first!'))

            errors = []

            if not record.delivery_type:
                errors.append('❌ Delivery Type must be selected (Deliver/Self Pick-up)')

            if errors:
                error_message = (
                        f'Cannot move Order #{record.order_number} to Torood Hub!\n\n'
                        'Required fields:\n' + '\n'.join(errors) + '\n\n'
                                                                   'Please complete all fields before proceeding.'
                )
                raise UserError(_(error_message))

            if not record.tracking_number:
                record._generate_tracking_number()

            record.state = 'picked'
            record.message_post(
                body=f"✅ Shipment moved to Torood Hub successfully!\n"
                     f"📦 Order: {record.order_number}\n"
                     f"🔍 Tracking: {record.tracking_number}\n"
                     f"🚚 Shipping Company Tracking: {record.tracking_number_shipping_company}\n"
                     f"📋 Packing Required: {'Yes' if record.mark_as_packing else 'No'}\n"
                     f"🚛 Delivery Type: {record.delivery_type}",
                subject="Moved to Torood Hub - Ready for Export"
            )

        return self.action_to_torood_hub_with_custom_export()

    def action_in_transit(self):
        """الشحنة في الطريق - تبقى كما هي بعد picked"""
        for record in self:
            if record.state != 'torood_hub':
                raise UserError(_('Shipment must be Picked Up first!'))

            if not record.tracking_number:
                record._generate_tracking_number()
            record.state = 'in_transit'
            record.message_post(
                body=f"Shipment in transit. Track at: {record.tracking_url or record.tracking_number}",
                subject="In Transit"
            )
        return True

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
            record.state = 'returned'

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

        customer_invoices = self.invoice_ids.filtered(lambda inv: inv.state != 'cancel')
        for invoice in customer_invoices:
            if invoice.state == 'posted':
                invoice.button_draft()
            invoice.button_cancel()

        vendor_bills = self.vendor_bill_ids.filtered(lambda bill: bill.state != 'cancel')
        for bill in vendor_bills:
            if bill.state == 'posted':
                bill.button_draft()
            bill.button_cancel()

        if self.sender_id:
            customer_invoice = self._create_return_customer_invoice()

        if self.shipping_company_id:
            vendor_bill = self._create_return_vendor_bill()

        self.is_return_processed = True

        return True

    # -*- coding: utf-8 -*-
    # استبدل دالة _create_return_customer_invoice في shipment.py

    def _create_return_customer_invoice(self):
        """إنشاء فاتورة عميل للمرتجع مع الغرامة المحسوبة"""
        self.ensure_one()

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale')
        ], limit=1)

        if not journal:
            raise UserError(_('Please configure a sales journal first!'))

        invoice_partner = self.sender_id
        category = self.customer_category_id

        if not category:
            raise UserError(_('Customer category is required for return invoice!'))

        # 🆕 بناء المبلغ الأساسي بناءً على الـ boolean fields
        base_components = []
        base_for_penalty = 0

        if category.include_base_in_customer_penalty:
            base_for_penalty += (self.company_base_cost or 0)
            base_components.append(f"Base Cost: {self.company_base_cost:.2f} EGP")

        if category.include_weight_in_customer_penalty:
            base_for_penalty += (self.company_weight_cost or 0)
            base_components.append(f"Weight Cost: {self.company_weight_cost:.2f} EGP")

        if category.include_pickup_in_customer_penalty:
            base_for_penalty += (self.pickup_fee or 0)
            base_components.append(f"Pickup Fee: {self.pickup_fee:.2f} EGP")

        if category.include_additional_in_customer_penalty:
            base_for_penalty += (self.total_additional_fees or 0)
            base_components.append(f"Additional Services: {self.total_additional_fees:.2f} EGP")

        # حساب الغرامة
        penalty_rate = category.customer_return_penalty_percentage / 100
        penalty_amount = base_for_penalty * penalty_rate

        invoice_lines = []

        # 🆕 بناء الوصف بناءً على المكونات المختارة
        components_text = "\n".join(base_components) if base_components else "No components selected"

        invoice_lines.append((0, 0, {
            'name': f"Return Penalty ({category.customer_return_penalty_percentage:.0f}%) - Order #{self.order_number}\n"
                    f"From: {self.sender_city or 'N/A'} To: {self.recipient_city}\n"
                    f"──────────────────────────\n"
                    f"Penalty Base Components:\n{components_text}\n"
                    f"Base Amount: {base_for_penalty:.2f} EGP\n"
                    f"Penalty Rate: {category.customer_return_penalty_percentage:.0f}%\n"
                    f"Penalty Amount: {penalty_amount:.2f} EGP",
            'quantity': 1,
            'price_unit': penalty_amount,  # 🆕 الغرامة فقط بدون الجمع!
            'account_id': self._get_income_account().id,
        }))

        # 🆕 ملاحظة: لو عايز تضيف discount بشكل منفصل (اختياري)
        discount = self.discount_amount or 0
        if discount > 0:
            invoice_lines.append((0, 0, {
                'name': "Discount",
                'quantity': 1,
                'price_unit': -discount,
                'account_id': self._get_income_account().id,
            }))

        total_amount = penalty_amount - discount

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
                         f"=== CUSTOMER PENALTY ({category.customer_return_penalty_percentage:.0f}%) ===\n"
                         f"Base Amount: {base_for_penalty:.2f} EGP\n"
                         f"Penalty Rate: {category.customer_return_penalty_percentage:.0f}%\n"
                         f"Penalty Amount: {penalty_amount:.2f} EGP\n"
                         f"Total: {total_amount:.2f} EGP\n\n"
                         f"Components included:\n{components_text}",
            'invoice_line_ids': invoice_lines,
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        return invoice

    def _create_return_vendor_bill(self):
        """إنشاء فاتورة مورد للمرتجع مع الغرامة المحسوبة"""
        self.ensure_one()

        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase')
        ], limit=1)

        if not journal:
            raise UserError(_('Please configure a purchase journal first!'))

        vendor_partner = self._get_shipping_vendor_partner()

        # 🆕 حساب المبلغ الأساسي بناءً على الـ boolean fields
        base_components = []
        base_vendor_amount = 0

        if self.shipping_company_id.include_base_in_penalty:
            base_vendor_amount += self.base_shipping_cost
            base_components.append(f"Base Shipping: {self.base_shipping_cost:.2f} EGP")

        if self.shipping_company_id.include_weight_in_penalty:
            base_vendor_amount += self.weight_shipping_cost
            base_components.append(f"Weight Cost: {self.weight_shipping_cost:.2f} EGP")

        # حساب الغرامة
        penalty_rate = self.shipping_company_id.return_penalty_percentage / 100
        penalty_amount = base_vendor_amount * penalty_rate

        invoice_lines = []

        # 🆕 بناء الوصف بناءً على المكونات المختارة
        components_text = "\n".join(base_components) if base_components else "No components selected"

        invoice_lines.append((0, 0, {
            'name': f"Return Penalty ({self.shipping_company_id.return_penalty_percentage:.0f}%) - {self.order_number}\n"
                    f"From: {self.sender_city} To: {self.recipient_city}\n"
                    f"──────────────────────────\n"
                    f"Penalty Base Components:\n{components_text}\n"
                    f"Base Amount: {base_vendor_amount:.2f} EGP\n"
                    f"Penalty Rate: {self.shipping_company_id.return_penalty_percentage:.0f}%\n"
                    f"Penalty Amount: {penalty_amount:.2f} EGP",
            'quantity': 1,
            'price_unit': penalty_amount,  # 🆕 الغرامة فقط بدون الجمع!
            'account_id': self._get_expense_account().id,
        }))

        vendor_bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': vendor_partner.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'currency_id': self.env.company.currency_id.id,
            'shipment_vendor_id': self.id,
            'ref': f"RETURN-{self.order_number}",
            'narration': f"Return Bill for Shipment {self.order_number}\n"
                         f"⚠️ This shipment was returned\n\n"
                         f"=== PENALTY CALCULATION ===\n"
                         f"Base Amount: {base_vendor_amount:.2f} EGP\n"
                         f"Penalty Rate: {self.shipping_company_id.return_penalty_percentage:.0f}%\n"
                         f"Penalty Amount: {penalty_amount:.2f} EGP\n\n"
                         f"Components included:\n{components_text}",
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
            record.state = 'cancelled'

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


# =====================================================
# باقي الكلاسات
# =====================================================

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
        string='Total Weight (KG)',
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
        string='Total Value',
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
            line.total_weight = line.weight
            line.total_value = line.product_value

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

    # Egyptian Location Fields
    governorate_new_id = fields.Many2one(
        'egypt.governorate',
        string='Governorate',
        tracking=True,
        help='Egyptian Governorate'
    )

    area_id = fields.Many2one(
        'egypt.governorate.area',
        string='City',
        domain="[('governorate_id', '=', governorate_new_id)]",
        tracking=True,
        help='City within the governorate'
    )

    city_district_id = fields.Many2one(
        'egypt.governorate.city',
        string='City/District',
        domain="[('area_id', '=', area_id)]",
        tracking=True,
        help='City or District within the area'
    )

    # Additional fields
    preferred_pickup_time = fields.Selection([
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 3 PM)'),
        ('late_afternoon', 'Late Afternoon (3 PM - 6 PM)'),
        ('evening', 'Evening (6 PM - 9 PM)'),
        ('anytime', 'Any Time'),
    ], string='Preferred Pickup Time', default='anytime')

    preferred_delivery_time = fields.Selection([
        ('morning', 'Morning (9 AM - 12 PM)'),
        ('afternoon', 'Afternoon (12 PM - 3 PM)'),
        ('late_afternoon', 'Late Afternoon (3 PM - 6 PM)'),
        ('evening', 'Evening (6 PM - 9 PM)'),
        ('anytime', 'Any Time'),
    ], string='Preferred Delivery Time', default='anytime')

    pickup_notes = fields.Text(string='Default Pickup Instructions')
    delivery_notes = fields.Text(string='Default Delivery Instructions')
    whatsapp = fields.Char(string='WhatsApp')
    alternative_phone = fields.Char(string='Alternative Phone')

    def _compute_shipment_count(self):
        for partner in self:
            partner.shipment_count = self.env['shipment.order'].search_count([
                '|', '|',
                ('sender_id', '=', partner.id),
                ('recipient_id', '=', partner.id),
                ('shipping_company_id', '=', partner.id)
            ])
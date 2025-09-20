# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CustomerPriceCategory(models.Model):
    """فئات تسعير العملاء"""
    _name = 'customer.price.category'
    _description = 'Customer Price Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='e.g., Standard, Silver, Gold'
    )

    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the category'
    )

    discount_percentage = fields.Float(
        string='Discount %',
        default=0.0,
        help='Discount percentage for this category (0-100)'
    )

    min_monthly_shipments = fields.Integer(
        string='Min. Monthly Shipments',
        default=0,
        help='Minimum shipments per month to qualify'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    color = fields.Integer(
        string='Color',
        default=0
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    description = fields.Text(
        string='Description',
        help='Description of this category benefits'
    )

    # ===== أسعار المحافظات الجديدة =====
    governorate_price_ids = fields.One2many(
        'customer.category.governorate.price',
        'category_id',
        string='Governorate Prices'
    )

    # أسعار افتراضية للمناطق
    use_zone_pricing = fields.Boolean(
        string='Use Zone Pricing',
        default=True,
        help='Use zone-based pricing instead of individual governorate prices'
    )

    # أسعار افتراضية للمناطق (تكلفة الشركة)
    cairo_zone_cost = fields.Float(string='Cairo & Giza Cost', default=30)
    alex_zone_cost = fields.Float(string='Alexandria Cost', default=35)
    delta_zone_cost = fields.Float(string='Delta Cost', default=40)
    upper_zone_cost = fields.Float(string='Upper Egypt Cost', default=50)
    canal_zone_cost = fields.Float(string='Suez Canal Cost', default=45)
    red_sea_zone_cost = fields.Float(string='Red Sea & Sinai Cost', default=60)
    remote_zone_cost = fields.Float(string='Remote Areas Cost', default=70)

    # سعر افتراضي لكل كيلو إضافي
    default_cost_per_kg = fields.Float(
        string='Default Cost per KG',
        default=3,
        help='Default additional cost per kilogram for company'
    )

    pickup_fee_enabled = fields.Boolean(
        string='Enable Pickup Fee',
        default=True,
        help='If enabled, pickup fee will be applied for this category'
    )

    pickup_fee_amount = fields.Float(
        string='Pickup Fee Amount (EGP)',
        default=20.0,
        help='Fixed pickup fee amount for this customer category'
    )

    # ===== COD Configuration for Company Profit =====
    cod_fee_enabled = fields.Boolean(
        string='Enable COD Fee',
        default=True,
        help='If enabled, company COD fee will be applied for this category'
    )

    # الحد الأدنى لتطبيق نسبة COD
    company_cod_minimum_amount = fields.Float(
        string='Company COD Minimum Amount',
        default=0,
        help='Minimum COD amount to apply company commission. If COD amount is less than this, no company commission will be applied'
    )

    # نسبة COD للدفع النقدي - ربح الشركة
    company_cod_cash_percentage = fields.Float(
        string='Company COD Cash Percentage (%)',
        default=1.0,
        help='Company COD commission percentage for cash payments (your profit margin)'
    )

    # رسوم ثابتة للدفع النقدي - ربح الشركة
    company_cod_cash_fixed_fee = fields.Float(
        string='Company COD Cash Fixed Fee',
        default=5,
        help='Fixed company fee for cash COD (in addition to percentage)'
    )

    # نسبة COD للدفع بالفيزا - ربح الشركة
    company_cod_visa_percentage = fields.Float(
        string='Company COD Visa/Card Percentage (%)',
        default=1.5,
        help='Company COD commission percentage for visa/card payments (your profit margin)'
    )

    # رسوم ثابتة للدفع بالفيزا - ربح الشركة
    company_cod_visa_fixed_fee = fields.Float(
        string='Company COD Visa/Card Fixed Fee',
        default=10,
        help='Fixed company fee for visa/card COD (in addition to percentage)'
    )
    service_price_ids = fields.One2many(
        'additional.service.category.price',
        'category_id',
        string='Service Prices'
    )

    # هل نطبق COD على قيمة الشحن أيضاً؟
    company_cod_include_shipping = fields.Boolean(
        string='Include Shipping in Company COD',
        default=False,
        help='If checked, company COD commission will be calculated on (Product Value + Shipping Cost)'
    )


    # إحصائيات
    customer_count = fields.Integer(
        string='Customers',
        compute='_compute_customer_count'
    )

    unified_cost_per_kg = fields.Float(
        string='Cost per KG (Unified)',
        default=3.0,
        help='Unified cost per kilogram for company (all governorates)'
    )
    free_weight_limit = fields.Float(
        string='Free Weight Limit (KG)',
        default=0.0,
        help='Weight up to this limit is free. Cost applies only for weight exceeding this limit.'
    )

    company_cod_fee_ranges = fields.One2many('cod.fee.range', 'customer_category_id', string='Company COD Fee Ranges')


    @api.constrains('discount_percentage')
    def _check_discount(self):
        for record in self:
            if record.discount_percentage < 0 or record.discount_percentage > 100:
                raise ValidationError(_('Discount must be between 0% and 100%'))

    def _compute_customer_count(self):
        for record in self:
            record.customer_count = self.env['res.partner'].search_count([
                ('price_category_id', '=', record.id)
            ])

    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            if record.discount_percentage > 0:
                name += f" (-{record.discount_percentage:.0f}%)"
            result.append((record.id, name))
        return result

    def get_governorate_cost(self, governorate_id):
        """الحصول على تكلفة المحافظة لهذه الفئة"""
        self.ensure_one()

        # البحث عن سعر مخصص للمحافظة
        price_config = self.governorate_price_ids.filtered(
            lambda p: p.governorate_id.id == governorate_id and p.active
        )

        if price_config:
            return price_config[0]

        # إذا لم يوجد سعر مخصص، استخدم السعر الافتراضي حسب المنطقة
        if self.use_zone_pricing:
            governorate = self.env['res.country.state'].browse(governorate_id)
            zone = self._get_governorate_zone(governorate.name)
            return self._create_temp_cost_config(governorate_id, zone)

        return False

    def _get_governorate_zone(self, governorate_name):
        """تحديد المنطقة حسب اسم المحافظة"""
        zones = {
            'cairo': ['القاهرة', 'Cairo', 'الجيزة', 'Giza'],
            'alex': ['الإسكندرية', 'Alexandria'],
            'delta': ['الدقهلية', 'الغربية', 'المنوفية', 'القليوبية', 'كفر الشيخ', 'دمياط', 'الشرقية', 'البحيرة'],
            'upper': ['أسيوط', 'أسوان', 'الأقصر', 'قنا', 'سوهاج', 'المنيا', 'بني سويف', 'الفيوم'],
            'canal': ['بورسعيد', 'الإسماعيلية', 'السويس'],
            'red_sea': ['البحر الأحمر', 'جنوب سيناء', 'شمال سيناء'],
            'remote': ['الوادي الجديد', 'مطروح']
        }

        for zone, governorates in zones.items():
            if any(gov in governorate_name for gov in governorates):
                return zone

        return 'delta'  # افتراضي

    def _create_temp_cost_config(self, governorate_id, zone):
        """إنشاء كونفيج تكلفة مؤقت بناءً على المنطقة"""
        zone_costs = {
            'cairo': self.cairo_zone_cost,
            'alex': self.alex_zone_cost,
            'delta': self.delta_zone_cost,
            'upper': self.upper_zone_cost,
            'canal': self.canal_zone_cost,
            'red_sea': self.red_sea_zone_cost,
            'remote': self.remote_zone_cost
        }

        # إنشاء كائن مؤقت
        return self.env['customer.category.governorate.price'].new({
            'category_id': self.id,
            'governorate_id': governorate_id,
            'zone': zone,
            'base_cost': zone_costs.get(zone, 40),
            'cost_per_kg': self.unified_cost_per_kg,  # استخدام السعر الموحد
        })

    def action_setup_all_services(self):
        """إنشاء أسعار لجميع الخدمات"""
        self.ensure_one()

        services = self.env['additional.service'].search([('active', '=', True)])

        for service in services:
            # التحقق من عدم وجود سعر مسبق
            existing = self.env['additional.service.category.price'].search([
                ('service_id', '=', service.id),
                ('category_id', '=', self.id)
            ])

            if not existing:
                self.env['additional.service.category.price'].create({
                    'service_id': service.id,
                    'category_id': self.id,
                    'fee_amount': 0.0,  # سعر افتراضي
                    'active': True
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Service prices created successfully'),
                'type': 'success',
            }
        }

class CustomerCategoryGovernoratePrice(models.Model):
    """أسعار المحافظات لكل فئة عملاء (تكلفة الشركة)"""
    _name = 'customer.category.governorate.price'
    _description = 'Customer Category Governorate Pricing'
    _rec_name = 'governorate_id'
    _order = 'category_id, zone, governorate_id'

    category_id = fields.Many2one(
        'customer.price.category',
        string='Customer Category',
        required=True,
        ondelete='cascade'
    )

    governorate_id = fields.Many2one(
        'res.country.state',
        string='Governorate',
        required=True,
        domain=[('country_id.code', '=', 'EG')]
    )

    zone = fields.Selection([
        ('cairo', 'Cairo & Giza'),
        ('alex', 'Alexandria'),
        ('delta', 'Delta'),
        ('upper', 'Upper Egypt'),
        ('canal', 'Suez Canal'),
        ('red_sea', 'Red Sea & Sinai'),
        ('remote', 'Remote Areas')
    ], string='Zone', help='Shipping zone classification')

    # تكلفة الشركة الأساسية
    base_cost = fields.Float(
        string='Base Cost (EGP)',
        required=True,
        default=0.0,
        help='Base company cost for this governorate'
    )

    # تكلفة إضافية حسب الوزن
    cost_per_kg = fields.Float(
        string='Cost per KG',
        default=0.0,
        help='Additional cost per kilogram'
    )

    # رسوم إضافية للشركة
    handling_fee = fields.Float(
        string='Handling Fee',
        default=0.0,
        help='Additional handling fee for company'
    )

    # الحالة
    active = fields.Boolean(
        string='Active',
        default=True
    )

    notes = fields.Text(
        string='Notes'
    )

    # Unique constraint
    _sql_constraints = [
        ('unique_category_governorate',
         'UNIQUE(category_id, governorate_id)',
         'Each governorate can have only one price configuration per customer category!')
    ]

    @api.constrains('base_cost', 'cost_per_kg')
    def _check_costs(self):
        for record in self:
            if record.base_cost < 0:
                raise ValidationError(_('Base cost cannot be negative!'))
            if record.cost_per_kg < 0:
                raise ValidationError(_('Cost per KG cannot be negative!'))

    def calculate_company_cost(self, weight=0):
        """حساب تكلفة الشركة للمحافظة"""
        self.ensure_one()

        # التكلفة الأساسية
        total_cost = self.base_cost

        # إضافة تكلفة الوزن
        if weight > 0 and self.cost_per_kg > 0:
            total_cost += weight * self.cost_per_kg

        # إضافة رسوم المناولة
        total_cost += self.handling_fee

        return total_cost


class ResPartner(models.Model):
    """إضافة فئة التسعير للعميل"""
    _inherit = 'res.partner'

    price_category_id = fields.Many2one(
        'customer.price.category',
        string='Price Category',
        help='Customer pricing category'
    )

    # إحصائيات للمساعدة في التصنيف
    monthly_shipment_count = fields.Integer(
        string='Monthly Shipments',
        compute='_compute_monthly_shipments'
    )

    total_shipment_value = fields.Float(
        string='Total Shipment Value',
        compute='_compute_shipment_stats'
    )

    def _compute_monthly_shipments(self):
        """حساب عدد الشحنات في آخر 30 يوم"""
        from datetime import datetime, timedelta

        for partner in self:
            date_from = datetime.now() - timedelta(days=30)
            partner.monthly_shipment_count = self.env['shipment.order'].search_count([
                ('sender_id', '=', partner.id),
                ('create_date', '>=', date_from)
            ])

    def _compute_shipment_stats(self):
        """حساب إجمالي قيمة الشحنات"""
        for partner in self:
            shipments = self.env['shipment.order'].search([
                ('sender_id', '=', partner.id),
                ('state', 'not in', ['cancelled'])
            ])
            partner.total_shipment_value = sum(shipments.mapped('final_customer_price'))

    def action_update_price_category(self):
        """تحديث فئة السعر بناءً على عدد الشحنات"""
        for partner in self:
            # البحث عن الفئة المناسبة
            categories = self.env['customer.price.category'].search([
                ('active', '=', True)
            ], order='min_monthly_shipments desc')

            for category in categories:
                if partner.monthly_shipment_count >= category.min_monthly_shipments:
                    partner.price_category_id = category
                    break

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Price categories updated successfully'),
                'type': 'success',
            }
        }


class ShipmentOrder(models.Model):
    _inherit = 'shipment.order'

    # الحقول الأساسية
    customer_category_id = fields.Many2one(
        related='sender_id.price_category_id',
        string='Customer Category',
        readonly=True
    )

    discount_percentage = fields.Float(
        related='sender_id.price_category_id.discount_percentage',
        string='Discount %',
        readonly=True
    )

    # ===== حقول التكلفة الجديدة للشركة =====
    company_base_cost = fields.Float(
        string='Company Base Cost',
        compute='_compute_company_costs',
        store=True,
        help='Base cost for the company based on customer category'
    )

    company_weight_cost = fields.Float(
        string='Company Weight Cost',
        compute='_compute_company_costs',
        store=True,
        help='Weight cost for the company'
    )

    company_handling_fee = fields.Float(
        string='Company Handling Fee',
        compute='_compute_company_costs',
        store=True,
        help='Handling fee for the company'
    )

    total_company_cost = fields.Float(
        string='Total Company Cost',
        compute='_compute_company_costs',
        store=True,
        help='Total cost for the company (before adding shipping company cost)'
    )

    # السعر قبل الخصم (مجموع كل شيء)
    subtotal_before_discount = fields.Float(
        string='Subtotal Before Discount',
        compute='_compute_customer_pricing',
        store=True
    )

    # المبلغ القابل للخصم (تكلفة الشركة + الرسوم الإضافية فقط)
    discountable_amount = fields.Float(
        string='Discountable Amount',
        compute='_compute_customer_pricing',
        store=True,
        help='Amount eligible for discount (Company costs + Additional fees)'
    )

    discount_amount = fields.Float(
        string='Discount Amount',
        compute='_compute_customer_pricing',
        store=True
    )

    # السعر النهائي المحسوب تلقائياً بعد الخصم
    calculated_customer_price = fields.Float(
        string='Calculated Price',
        compute='_compute_customer_pricing',
        store=True
    )

    # السعر النهائي الشامل (تكلفة الشركة + تكلفة شركة الشحن)
    total_final_cost = fields.Float(
        string='Total Final Cost (Company + Shipping)',
        compute='_compute_total_final_cost',
        store=True,
        help='Total cost including company cost and shipping company cost'
    )

    company_cod_fee_amount = fields.Float(
        string='Company COD Fee',
        compute='_compute_company_cod_fee',
        store=True,
        readonly=True,
        help='COD fee for the company (profit margin)'
    )

    company_cod_calculation_details = fields.Text(
        string='Company COD Calculation Details',
        compute='_compute_company_cod_fee',
        store=True
    )

    additional_service_ids = fields.One2many(
        'shipment.additional.service',
        'shipment_id',
        string='Additional Services'
    )

    total_additional_fees = fields.Float(
        string='Total Additional Fees',
        compute='_compute_additional_fees',
        store=True,
        default=0.0
    )

    @api.depends('sender_id.price_category_id', 'recipient_governorate_id', 'total_weight',
                 'pickup_type', 'pickup_fee', 'payment_method', 'cod_amount', 'company_cod_fee_amount')
    def _compute_company_costs(self):
        """حساب تكاليف الشركة بناءً على فئة العميل والمحافظة"""
        for record in self:
            if record.customer_category_id and record.recipient_governorate_id:
                # الحصول على كونفيج التكلفة للمحافظة
                cost_config = record.customer_category_id.get_governorate_cost(
                    record.recipient_governorate_id.id
                )

                if cost_config:
                    # حساب التكلفة الأساسية
                    record.company_base_cost = cost_config.base_cost

                    # حساب تكلفة الوزن مع احتساب الوزن المجاني
                    if record.total_weight > 0 and record.customer_category_id:
                        # احسب الوزن الذي سيتم حساب تكلفته
                        free_limit = record.customer_category_id.free_weight_limit or 0

                        if record.total_weight > free_limit:
                            # احسب فقط الوزن الزائد عن الحد المجاني
                            chargeable_weight = record.total_weight - free_limit
                            record.company_weight_cost = chargeable_weight * record.customer_category_id.unified_cost_per_kg
                        else:
                            # الوزن كله مجاني
                            record.company_weight_cost = 0
                    else:
                        record.company_weight_cost = 0

                    # رسوم المناولة
                    record.company_handling_fee = cost_config.handling_fee if hasattr(cost_config,
                                                                                      'handling_fee') else 0

                    # إجمالي تكلفة الشركة
                    record.total_company_cost = (
                            record.company_base_cost +
                            record.company_weight_cost +
                            record.company_handling_fee +
                            (record.pickup_fee if record.pickup_type == 'customer' else 0) +
                            (record.company_cod_fee_amount if record.payment_method == 'cod' else 0)
                    )
                else:
                    record.company_base_cost = 0

                    if record.total_weight > 0 and record.customer_category_id:
                        free_limit = record.customer_category_id.free_weight_limit or 0
                        if record.total_weight > free_limit:
                            chargeable_weight = record.total_weight - free_limit
                            record.company_weight_cost = chargeable_weight * record.customer_category_id.unified_cost_per_kg
                        else:
                            record.company_weight_cost = 0
                    else:
                        record.company_weight_cost = 0

                    record.company_handling_fee = 0

                    record.total_company_cost = (
                            record.company_weight_cost +
                            (record.pickup_fee if record.pickup_type == 'customer' else 0) +
                            (record.company_cod_fee_amount if record.payment_method == 'cod' else 0)
                    )
            else:
                record.company_base_cost = 0

                if record.total_weight > 0 and record.customer_category_id:
                    free_limit = record.customer_category_id.free_weight_limit or 0
                    if record.total_weight > free_limit:
                        chargeable_weight = record.total_weight - free_limit
                        record.company_weight_cost = chargeable_weight * record.customer_category_id.unified_cost_per_kg
                    else:
                        record.company_weight_cost = 0
                else:
                    record.company_weight_cost = 0

                record.company_handling_fee = 0

                record.total_company_cost = (
                        record.company_weight_cost +
                        (record.pickup_fee if record.pickup_type == 'customer' else 0) +
                        (record.company_cod_fee_amount if record.payment_method == 'cod' else 0)
                )

    @api.depends('payment_method', 'cod_amount', 'cod_payment_type', 'customer_category_id', 'shipping_cost')
    def _compute_company_cod_fee(self):
        """حساب رسوم COD للشركة (الربح) بناءً على شرائح فئة العميل"""
        for record in self:
            if record.payment_method != 'cod' or not record.customer_category_id:
                record.company_cod_fee_amount = 0
                record.company_cod_calculation_details = ''
                continue

            category = record.customer_category_id

            # التحقق من تفعيل COD fee
            if not category.cod_fee_enabled:
                record.company_cod_fee_amount = 0
                record.company_cod_calculation_details = 'COD fee disabled for this category'
                continue

            # حساب المبلغ الأساسي
            base_amount = record.cod_amount
            if category.company_cod_include_shipping:
                base_amount += record.shipping_cost

            # البحث عن الشريحة المناسبة من شرائح COD للفئة
            cod_range = category.company_cod_fee_ranges.filtered(
                lambda r: r.amount_from <= base_amount and (r.amount_to == 0 or r.amount_to >= base_amount)
            )

            if not cod_range:
                # إذا لم نجد شريحة مناسبة
                record.company_cod_fee_amount = 0
                record.company_cod_calculation_details = (
                    f'No COD range found for amount {base_amount:.2f} EGP in category {category.name}'
                )
                continue

            # استخدم أول شريحة مطابقة
            cod_range = cod_range[0]

            # حساب الرسوم حسب نوع الدفع
            if record.cod_payment_type == 'visa':
                percentage = cod_range.visa_percentage
            else:  # cash
                percentage = cod_range.cash_percentage

            # حساب الرسوم
            percentage_fee = (base_amount * percentage / 100) if percentage else 0
            total_fee = percentage_fee  # لم نعد نستخدم fixed fee

            record.company_cod_fee_amount = total_fee

            # تفاصيل الحساب
            details = []
            details.append(f"Category: {category.name}")
            details.append(f"COD Amount: {record.cod_amount:.2f} EGP")
            if category.company_cod_include_shipping:
                details.append(f"Shipping Cost: {record.shipping_cost:.2f} EGP")
                details.append(f"Total Base: {base_amount:.2f} EGP")

            # معلومات الشريحة المستخدمة
            if cod_range.amount_to > 0:
                range_display = f"{cod_range.amount_from:.0f}-{cod_range.amount_to:.0f} EGP"
            else:
                range_display = f"{cod_range.amount_from:.0f}+ EGP"
            details.append(f"Range Used: {range_display}")
            details.append(f"Payment Type: {record.cod_payment_type.upper()}")
            details.append(f"Company Percentage: {percentage:.2f}%")

            if percentage_fee:
                details.append(f"Percentage Fee: {percentage_fee:.2f} EGP")

            details.append(f"Total Company COD Fee: {total_fee:.2f} EGP")

            record.company_cod_calculation_details = '\n'.join(details)

    @api.depends('shipping_cost', 'total_additional_fees', 'discount_percentage', 'total_company_cost')  # تعديل هنا
    def _compute_customer_pricing(self):
        """حساب السعر النهائي مع الخصم (الخصم فقط على تكلفة الشركة)"""
        for record in self:
            # 1. حساب المجموع قبل الخصم
            # المجموع = تكلفة الشركة + تكلفة الشحن + الرسوم الإضافية
            record.subtotal_before_discount = (
                    record.total_company_cost +
                    record.shipping_cost +
                    record.total_additional_fees  # تم التعديل هنا
            )

            # 2. حساب المبلغ القابل للخصم (تكلفة الشركة + الرسوم الإضافية فقط)
            record.discountable_amount = record.total_company_cost + record.total_additional_fees  # تم التعديل هنا

            # 3. حساب الخصم على المبلغ القابل للخصم فقط
            if record.discount_percentage > 0 and record.discountable_amount > 0:
                record.discount_amount = record.discountable_amount * (record.discount_percentage / 100)
            else:
                record.discount_amount = 0

            # 4. السعر النهائي = (المبلغ القابل للخصم - الخصم) + تكلفة شركة الشحن
            record.calculated_customer_price = record.subtotal_before_discount - record.discount_amount

    @api.depends('total_company_cost', 'shipping_cost')
    def _compute_total_final_cost(self):
        """حساب التكلفة النهائية الشاملة"""
        for record in self:
            record.total_final_cost = record.total_company_cost + record.shipping_cost

    @api.depends('additional_service_ids.fee_amount')
    def _compute_additional_fees(self):
        for record in self:
            record.total_additional_fees = sum(record.additional_service_ids.mapped('fee_amount'))

    # تعديل دالة _compute_final_price
    @api.depends('shipping_cost', 'total_additional_fees')
    def _compute_final_price(self):
        for record in self:
            record.final_customer_price = record.shipping_cost + record.total_additional_fees

    @api.onchange('sender_id')
    def _onchange_sender_pricing(self):
        """تطبيق فئة السعر عند اختيار العميل"""
        if self.sender_id:
            self._compute_customer_pricing()
            self._compute_company_costs()

    @api.onchange('recipient_governorate_id')
    def _onchange_governorate_pricing(self):
        """إعادة حساب التكاليف عند تغيير المحافظة"""
        if self.recipient_governorate_id:
            self._compute_company_costs()
            self._compute_customer_pricing()

    def get_cost_breakdown(self):
        """الحصول على تفاصيل التكاليف للعرض في الفاتورة"""
        self.ensure_one()
        return {
            'company_costs': {
                'base_cost': self.company_base_cost,
                'weight_cost': self.company_weight_cost,
                'handling_fee': self.company_handling_fee,
                'pickup_fee': self.pickup_fee if self.pickup_type == 'customer' else 0,
                'company_cod_fee': self.company_cod_fee_amount if self.payment_method == 'cod' else 0,
                'total': self.total_company_cost
            },
            'shipping_costs': {
                'base_cost': self.base_shipping_cost,
                'weight_cost': self.weight_shipping_cost,
                'cod_fee': self.cod_fee_amount,  # هذا COD fee لشركة الشحن
                'insurance_fee': self.insurance_fee_amount,
                'total': self.shipping_cost
            },
            'additional_fees': self.total_additional_fees,  # تم التعديل هنا
            'discountable_amount': self.total_company_cost + self.total_additional_fees,  # وهنا
            'non_discountable_amount': self.shipping_cost,
            'subtotal': self.subtotal_before_discount,
            'discount': {
                'percentage': self.discount_percentage,
                'amount': self.discount_amount,
                'applied_on': 'Company costs (including pickup & COD) and additional fees only'
            },
            'final_price': self.calculated_customer_price
        }
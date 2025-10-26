# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShippingCompany(models.Model):
    _name = 'shipping.company'
    _description = 'Shipping Company'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # ===== الحقول الأساسية =====
    name = fields.Char(
        string='Company Name',
        required=True,
        tracking=True
    )

    code = fields.Char(
        string='Company Code',
        required=True,
        tracking=True,
        help='Short code for the company (e.g., ARAMEX, FEDEX, DHL)'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    # ===== معلومات الاتصال =====
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    website = fields.Char(string='Website')
    address = fields.Text(string='Address')

    # ===== إعدادات COD الجديدة =====

    # الحد الأدنى لتطبيق نسبة COD
    cod_minimum_amount = fields.Float(
        string='COD Minimum Amount',
        default=0,
        tracking=True,
        help='Minimum COD amount to apply commission. If COD amount is less than this, no commission will be applied'
    )

    # نسبة COD للدفع النقدي
    cod_cash_percentage = fields.Float(
        string='COD Cash Percentage (%)',
        default=2.0,
        tracking=True,
        help='COD commission percentage for cash payments'
    )

    # رسوم ثابتة للدفع النقدي
    cod_cash_fixed_fee = fields.Float(
        string='COD Cash Fixed Fee',
        default=0,
        help='Fixed fee for cash COD (in addition to percentage)'
    )

    # نسبة COD للدفع بالفيزا
    cod_visa_percentage = fields.Float(
        string='COD Visa/Card Percentage (%)',
        default=3.0,
        tracking=True,
        help='COD commission percentage for visa/card payments'
    )

    # رسوم ثابتة للدفع بالفيزا
    cod_visa_fixed_fee = fields.Float(
        string='COD Visa/Card Fixed Fee',
        default=0,
        help='Fixed fee for visa/card COD (in addition to percentage)'
    )

    # هل نطبق COD على قيمة الشحن أيضاً؟
    cod_include_shipping = fields.Boolean(
        string='Include Shipping in COD',
        default=False,
        help='If checked, COD commission will be calculated on (Product Value + Shipping Cost)'
    )

    # ===== إحصائيات =====
    total_orders = fields.Integer(
        string='Total Orders',
        compute='_compute_statistics'
    )

    delivered_orders = fields.Integer(
        string='Delivered Orders',
        compute='_compute_statistics'
    )

    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_statistics'
    )

    # ===== أسعار المحافظات =====
    governorate_price_ids = fields.One2many(
        'shipping.governorate.price',
        'company_id',
        string='Governorate Prices'
    )

    default_zone_prices = fields.Boolean(
        string='Use Zone Pricing',
        default=True,
        help='Use zone-based pricing instead of individual governorate prices'
    )

    # أسعار افتراضية للمناطق
    cairo_zone_price = fields.Float(string='Cairo & Giza Price', default=40)
    alex_zone_price = fields.Float(string='Alexandria Price', default=45)
    delta_zone_price = fields.Float(string='Delta Price', default=50)
    upper_zone_price = fields.Float(string='Upper Egypt Price', default=60)
    canal_zone_price = fields.Float(string='Suez Canal Price', default=55)
    red_sea_zone_price = fields.Float(string='Red Sea & Sinai Price', default=70)
    remote_zone_price = fields.Float(string='Remote Areas Price', default=80)

    # سعر افتراضي لكل كيلو إضافي
    default_price_per_kg = fields.Float(
        string='Default Price per KG',
        default=5,
        help='Default additional price per kilogram'
    )

    # ===== حقول محسوبة للأمثلة =====
    cod_example_5000_cash = fields.Char(
        string='5000 Cash Example',
        compute='_compute_cod_examples'
    )

    cod_example_10000_visa = fields.Char(
        string='10000 Visa Example',
        compute='_compute_cod_examples'
    )

    insurance_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Insurance Fee Type',
        default='percentage',
        tracking=True,
        help='Choose whether insurance fee is calculated as percentage or fixed amount')

    insurance_percentage = fields.Float(
        string='Insurance Percentage (%)',
        default=1.0,
        tracking=True,
        help='Insurance fee as percentage of product value'
    )

    insurance_fixed_amount = fields.Float(
        string='Insurance Fixed Amount',
        default=50.0,
        tracking=True,
        help='Fixed insurance fee amount in EGP'
    )

    insurance_minimum_value = fields.Float(
        string='Minimum Value for Insurance',
        default=500,
        help='Minimum product value to apply insurance'
    )

    unified_price_per_kg = fields.Float(
        string='Price per KG (Unified)',
        default=5.0,
        help='Unified price per kilogram for all governorates'
    )

    free_weight_limit = fields.Float(
        string='Free Weight Limit (KG)',
        default=0.0,
        help='Weight up to this limit is free. Charges apply only for weight exceeding this limit.'
    )

    cod_fee_ranges = fields.One2many('cod.fee.range', 'shipping_company_id', string='COD Fee Ranges')

    # إعدادات غرامة الإرجاع
    return_penalty_enabled = fields.Boolean(
        string='Enable Return Penalty',
        default=True,
        help='Apply penalty fees for returned shipments'
    )

    return_penalty_percentage = fields.Float(
        string='Return Penalty %',
        default=50.0,
        help='Percentage to add on shipping cost for returns'
    )

    def calculate_insurance_fee(self, cod_amount_sheet_excel, apply_insurance=True):
        """حساب رسوم التأمين بناءً على إعدادات الشركة - معادلة جديدة"""
        self.ensure_one()

        if not apply_insurance:
            return {
                'fee_amount': 0,
                'type_used': None,
                'rate_used': 0,
                'reason': 'Insurance not required'
            }

        # إذا كانت قيمة المنتج = 0، لا تأمين
        if cod_amount_sheet_excel == 0:
            return {
                'fee_amount': 0,
                'type_used': None,
                'rate_used': 0,
                'reason': 'Product value is zero'
            }

        # حساب الرسوم حسب النوع
        if self.insurance_type == 'percentage':
            # احسب النسبة المئوية
            calculated_fee = (cod_amount_sheet_excel * self.insurance_percentage / 100)

            # خد الأكبر بين النسبة والمنيمم
            final_fee = max(calculated_fee, self.insurance_minimum_value)

            return {
                'fee_amount': final_fee,
                'type_used': 'percentage',
                'rate_used': self.insurance_percentage,
                'cod_amount_sheet_excel': cod_amount_sheet_excel,
                'calculated_fee': calculated_fee,
                'minimum_applied': final_fee > calculated_fee,
                'reason': f'Applied max of percentage ({calculated_fee:.2f}) and minimum ({self.insurance_minimum_value:.2f})'
            }
        else:  # fixed
            # خد الأكبر بين القيمة الثابتة والمنيمم
            final_fee = max(self.insurance_fixed_amount, self.insurance_minimum_value)

            return {
                'fee_amount': final_fee,
                'type_used': 'fixed',
                'rate_used': self.insurance_fixed_amount,
                'cod_amount_sheet_excel': cod_amount_sheet_excel,
                'calculated_fee': self.insurance_fixed_amount,
                'minimum_applied': final_fee > self.insurance_fixed_amount,
                'reason': f'Applied max of fixed ({self.insurance_fixed_amount:.2f}) and minimum ({self.insurance_minimum_value:.2f})'
            }



    @api.depends('cod_minimum_amount', 'cod_cash_percentage', 'cod_cash_fixed_fee',
                 'cod_visa_percentage', 'cod_visa_fixed_fee')
    def _compute_cod_examples(self):
        """حساب أمثلة COD للعرض"""
        for record in self:
            # مثال 5000 نقدي
            if 5000 < record.cod_minimum_amount:
                record.cod_example_5000_cash = "0 EGP (Below minimum)"
            else:
                fee = (5000 * record.cod_cash_percentage / 100) + record.cod_cash_fixed_fee
                record.cod_example_5000_cash = f"{fee:.2f} EGP"

            # مثال 10000 فيزا
            if 10000 < record.cod_minimum_amount:
                record.cod_example_10000_visa = "0 EGP (Below minimum)"
            else:
                fee = (10000 * record.cod_visa_percentage / 100) + record.cod_visa_fixed_fee
                record.cod_example_10000_visa = f"{fee:.2f} EGP"

    # ===== الدوال =====

    def _compute_statistics(self):
        """حساب الإحصائيات"""
        for company in self:
            orders = self.env['shipment.order'].search([
                ('shipping_company_id', '=', company.id)
            ])

            company.total_orders = len(orders)
            company.delivered_orders = len(orders.filtered(lambda o: o.state == 'delivered'))

            if company.total_orders:
                company.success_rate = (company.delivered_orders / company.total_orders) * 100
            else:
                company.success_rate = 0

    @api.constrains('cod_minimum_amount', 'cod_cash_percentage', 'cod_visa_percentage')
    def _check_cod_values(self):
        """التحقق من صحة قيم COD"""
        for record in self:
            if record.cod_minimum_amount < 0:
                raise ValidationError(_('COD minimum amount cannot be negative!'))
            if record.cod_cash_percentage < 0:
                raise ValidationError(_('COD cash percentage cannot be negative!'))
            if record.cod_visa_percentage < 0:
                raise ValidationError(_('COD visa percentage cannot be negative!'))

    def calculate_cod_fee(self, cod_amount, payment_type='cash', include_shipping_cost=False, shipping_cost=0):
        """حساب رسوم COD بناءً على الشرائح"""
        self.ensure_one()

        # حساب المبلغ الأساسي
        base_amount = cod_amount
        if self.cod_include_shipping and include_shipping_cost:
            base_amount += shipping_cost

        # البحث عن الشريحة المناسبة
        cod_range = self.cod_fee_ranges.filtered(
            lambda r: r.amount_from <= base_amount and (r.amount_to == 0 or r.amount_to >= base_amount)
        )

        if not cod_range:
            # إذا لم نجد شريحة مناسبة
            return {
                'fee_amount': 0,
                'percentage_used': 0,
                'fixed_fee_used': 0,
                'total_cod_amount': base_amount,
                'reason': f'No COD range found for amount {base_amount:.2f}'
            }

        # استخدم أول شريحة مطابقة
        cod_range = cod_range[0]

        # حساب الرسوم حسب نوع الدفع
        if payment_type == 'visa':
            percentage = cod_range.visa_percentage
        else:  # cash
            percentage = cod_range.cash_percentage

        # حساب رسوم النسبة المئوية
        percentage_fee = (base_amount * percentage / 100) if percentage else 0

        # معلومات الشريحة للإرجاع
        if cod_range.amount_to > 0:
            range_used = f"{cod_range.amount_from:.0f}-{cod_range.amount_to:.0f}"
        else:
            range_used = f"{cod_range.amount_from:.0f}+"

        return {
            'fee_amount': percentage_fee,
            'percentage_used': percentage,
            'fixed_fee_used': 0,  # لم نعد نستخدم fixed fee
            'percentage_fee': percentage_fee,
            'total_cod_amount': base_amount,
            'payment_type': payment_type,
            'range_used': range_used
        }

    def get_governorate_price(self, governorate_id):
        """الحصول على سعر المحافظة"""
        self.ensure_one()

        # البحث عن سعر مخصص للمحافظة
        price_config = self.with_context(active_test=False).governorate_price_ids.filtered(
            lambda p: p.governorate_id.id == governorate_id
        )

        if price_config:
            return price_config[0]

        # إذا لم يوجد سعر مخصص، استخدم السعر الافتراضي حسب المنطقة
        if self.default_zone_prices:
            governorate = self.env['res.country.state'].browse(governorate_id)
            zone = self._get_governorate_zone(governorate.name)
            return self._create_temp_price_config(governorate_id, zone)

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

        # إذا لم نجد المحافظة، نعتبرها في الدلتا كافتراضي
        return 'delta'

    def _create_temp_price_config(self, governorate_id, zone):
        """إنشاء كونفيج سعر مؤقت بناءً على المنطقة"""
        zone_prices = {
            'cairo': self.cairo_zone_price,
            'alex': self.alex_zone_price,
            'delta': self.delta_zone_price,
            'upper': self.upper_zone_price,
            'canal': self.canal_zone_price,
            'red_sea': self.red_sea_zone_price,
            'remote': self.remote_zone_price
        }

        # إنشاء كائن مؤقت
        return self.env['shipping.governorate.price'].new({
            'company_id': self.id,
            'governorate_id': governorate_id,
            'zone': zone,
            'base_price': zone_prices.get(zone, 50),
            'price_per_kg': self.unified_price_per_kg,  # استخدام السعر الموحد
            'delivery_days_min': 2 if zone in ['cairo', 'alex'] else 3,
            'delivery_days_max': 3 if zone in ['cairo', 'alex'] else 5,
        })

    @api.model
    def initialize_default_prices(self):
        """إنشاء أسعار افتراضية لجميع المحافظات"""
        egypt = self.env.ref('base.eg')
        governorates = self.env['res.country.state'].search([
            ('country_id', '=', egypt.id)
        ])

        for company in self.search([]):
            for governorate in governorates:
                # تحقق من عدم وجود سعر مسبق
                existing = self.env['shipping.governorate.price'].search([
                    ('company_id', '=', company.id),
                    ('governorate_id', '=', governorate.id)
                ])

                if not existing:
                    zone = company._get_governorate_zone(governorate.name)
                    zone_prices = {
                        'cairo': company.cairo_zone_price,
                        'alex': company.alex_zone_price,
                        'delta': company.delta_zone_price,
                        'upper': company.upper_zone_price,
                        'canal': company.canal_zone_price,
                        'red_sea': company.red_sea_zone_price,
                        'remote': company.remote_zone_price
                    }

                    self.env['shipping.governorate.price'].create({
                        'company_id': company.id,
                        'governorate_id': governorate.id,
                        'zone': zone,
                        'base_price': zone_prices.get(zone, 50),
                        'price_per_kg': company.default_price_per_kg,
                        'delivery_days_min': 2 if zone in ['cairo', 'alex'] else 3,
                        'delivery_days_max': 3 if zone in ['cairo', 'alex'] else 5,
                    })

        return True

    def action_view_governorate_prices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Governorate Prices - {self.name}',
            'res_model': 'shipping.governorate.price',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {
                'default_company_id': self.id,
                'search_default_company_id': self.id,
                'active_test': False,
            },
        }
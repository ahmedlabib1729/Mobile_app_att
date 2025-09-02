# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShippingGovernoratePrice(models.Model):
    """أسعار الشحن حسب المحافظات لكل شركة شحن"""
    _name = 'shipping.governorate.price'
    _description = 'Shipping Governorate Pricing'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # إضافة الوراثة
    _rec_name = 'governorate_id'
    _order = 'company_id, zone, governorate_id'

    company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        ondelete='cascade',
        tracking=True  # إضافة tracking
    )

    governorate_id = fields.Many2one(
        'res.country.state',
        string='Governorate',
        required=True,
        domain=[('country_id.code', '=', 'EG')],
        tracking=True  # إضافة tracking
    )

    zone = fields.Selection([
        ('cairo', 'Cairo & Giza'),
        ('alex', 'Alexandria'),
        ('delta', 'Delta'),
        ('upper', 'Upper Egypt'),
        ('canal', 'Suez Canal'),
        ('red_sea', 'Red Sea & Sinai'),
        ('remote', 'Remote Areas')
    ], string='Zone', help='Shipping zone classification', tracking=True)

    # التسعير الأساسي
    base_price = fields.Float(
        string='Base Price (EGP)',
        required=True,
        default=0.0,
        help='Base shipping price for this governorate',
        tracking=True  # إضافة tracking
    )

    # تسعير إضافي حسب الوزن
    price_per_kg = fields.Float(
        string='Price per KG',
        default=0.0,
        help='Additional price per kilogram'
    )

    # رسوم إضافية
    cod_fee = fields.Float(
        string='COD Fee',
        default=0.0,
        help='Cash on delivery fee for this governorate'
    )

    cod_percentage = fields.Float(
        string='COD Percentage (%)',
        default=0.0,
        help='COD fee as percentage of amount'
    )

    # أوقات التسليم
    delivery_days_min = fields.Integer(
        string='Min Delivery Days',
        default=1
    )

    delivery_days_max = fields.Integer(
        string='Max Delivery Days',
        default=3
    )

    # رسوم خاصة
    return_fee = fields.Float(
        string='Return Fee',
        default=0.0,
        help='Fee for return shipments'
    )

    exchange_fee = fields.Float(
        string='Exchange Fee',
        default=0.0,
        help='Fee for exchange shipments'
    )

    # حدود الوزن
    max_weight = fields.Float(
        string='Max Weight (KG)',
        default=0.0,
        help='Maximum weight allowed (0 = unlimited)'
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
        ('unique_company_governorate',
         'UNIQUE(company_id, governorate_id)',
         'Each governorate can have only one price configuration per shipping company!')
    ]

    @api.constrains('base_price', 'price_per_kg')
    def _check_prices(self):
        for record in self:
            if record.base_price < 0:
                raise ValidationError(_('Base price cannot be negative!'))
            if record.price_per_kg < 0:
                raise ValidationError(_('Price per KG cannot be negative!'))

    @api.constrains('delivery_days_min', 'delivery_days_max')
    def _check_delivery_days(self):
        for record in self:
            if record.delivery_days_min < 0:
                raise ValidationError(_('Minimum delivery days cannot be negative!'))
            if record.delivery_days_max < record.delivery_days_min:
                raise ValidationError(_('Maximum delivery days must be greater than or equal to minimum!'))

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.company_id.name} - {record.governorate_id.name} ({record.base_price:.0f} EGP)"
            result.append((record.id, name))
        return result

    def calculate_shipping_price(self, weight=0, cod_amount=0, service_type='normal'):
        """حساب سعر الشحن للمحافظة"""
        self.ensure_one()

        # السعر الأساسي
        total_price = self.base_price

        # إضافة سعر الوزن
        if weight > 0 and self.price_per_kg > 0:
            total_price += weight * self.price_per_kg

        # رسوم COD
        if cod_amount > 0:
            if self.cod_fee > 0:
                total_price += self.cod_fee
            if self.cod_percentage > 0:
                total_price += (cod_amount * self.cod_percentage / 100)

        # رسوم إضافية حسب نوع الخدمة
        if service_type == 'express':
            total_price *= 1.5  # زيادة 50% للخدمة السريعة
        elif service_type == 'same_day':
            total_price *= 2  # ضعف السعر للتوصيل في نفس اليوم

        return total_price


class ShippingCompany(models.Model):
    """إضافة أسعار المحافظات لشركة الشحن"""
    _inherit = 'shipping.company'

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

    def get_governorate_price(self, governorate_id):
        """الحصول على سعر المحافظة"""
        self.ensure_one()

        # البحث عن سعر مخصص للمحافظة
        price_config = self.governorate_price_ids.filtered(
            lambda p: p.governorate_id.id == governorate_id and p.active
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
            'cairo': ['القاهرة', 'Cairo'],
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

        # إنشاء كائن مؤقت (لن يتم حفظه في قاعدة البيانات)
        return self.env['shipping.governorate.price'].new({
            'company_id': self.id,
            'governorate_id': governorate_id,
            'zone': zone,
            'base_price': zone_prices.get(zone, 50),
            'price_per_kg': 5,  # سعر افتراضي للكيلو
            'cod_fee': 10,  # رسوم COD افتراضية
            'cod_percentage': 1,  # نسبة COD افتراضية
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
                        'price_per_kg': 5,
                        'cod_fee': 10,
                        'cod_percentage': 1,
                        'delivery_days_min': 2 if zone in ['cairo', 'alex'] else 3,
                        'delivery_days_max': 3 if zone in ['cairo', 'alex'] else 5,
                    })

        return True


class ShipmentOrder(models.Model):
    """تعديل حساب الأسعار في الشحنة"""
    _inherit = 'shipment.order'

    @api.onchange('shipping_company_id', 'recipient_governorate_id')
    def _onchange_shipping_company_governorate(self):
        """عند تغيير شركة الشحن أو المحافظة"""
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
                    service_type='normal'  # يمكن تغييرها حسب نوع الخدمة
                )

                self.shipping_cost = shipping_cost

                # تحديث وقت التسليم المتوقع
                if price_config.delivery_days_min:
                    from datetime import datetime, timedelta
                    self.expected_delivery = datetime.now() + timedelta(days=price_config.delivery_days_max)
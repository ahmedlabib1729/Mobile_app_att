# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ShippingGovernoratePrice(models.Model):
    """أسعار الشحن حسب المحافظات لكل شركة شحن - محدث للمحافظات الجديدة"""
    _name = 'shipping.governorate.price'
    _description = 'Shipping Governorate Pricing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'egypt_governorate_id'
    _order = 'company_id, zone, egypt_governorate_id'

    company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    # استخدام المحافظة الجديدة
    egypt_governorate_id = fields.Many2one(
        'egypt.governorate',
        string='Governorate',
        required=True,
        tracking=True
    )

    # الحقل القديم للتوافق المؤقت
    governorate_id = fields.Many2one(
        'res.country.state',
        string='Governorate',
        compute='_compute_old_governorate',
        store=True
    )

    @api.depends('egypt_governorate_id')
    def _compute_old_governorate(self):
        """ربط مع المحافظة القديمة للتوافق"""
        for record in self:
            if record.egypt_governorate_id and record.egypt_governorate_id.state_id:
                record.governorate_id = record.egypt_governorate_id.state_id
            else:
                record.governorate_id = False

    zone = fields.Selection(
        related='egypt_governorate_id.zone',
        string='Zone',
        store=True,
        readonly=True
    )

    # التسعير الأساسي
    base_price = fields.Float(
        string='Base Price (EGP)',
        required=True,
        default=0.0,
        help='Base shipping price for this governorate',
        tracking=True
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

    # Unique constraint محدث
    _sql_constraints = [
        ('unique_company_governorate',
         'UNIQUE(company_id, egypt_governorate_id)',
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
            name = f"{record.company_id.name} - {record.egypt_governorate_id.name} ({record.base_price:.0f} EGP)"
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
    """تحديث شركة الشحن لاستخدام المحافظات الجديدة"""
    _inherit = 'shipping.company'

    # تحديث العلاقة مع أسعار المحافظات
    governorate_price_ids = fields.One2many(
        'shipping.governorate.price',
        'company_id',
        string='Governorate Prices'
    )

    def get_governorate_price_new(self, egypt_governorate_id):
        """الحصول على سعر المحافظة باستخدام المحافظة الجديدة"""
        self.ensure_one()

        # البحث عن سعر مخصص للمحافظة
        price_config = self.governorate_price_ids.filtered(
            lambda p: p.egypt_governorate_id.id == egypt_governorate_id and p.active
        )

        if price_config:
            return price_config[0]

        # إذا لم يوجد سعر مخصص، إنشاء سعر افتراضي
        if self.default_zone_prices:
            governorate = self.env['egypt.governorate'].browse(egypt_governorate_id)
            zone = governorate.zone
            return self._create_temp_price_config_new(egypt_governorate_id, zone)

        return False

    def _create_temp_price_config_new(self, egypt_governorate_id, zone):
        """إنشاء كونفيج سعر مؤقت للمحافظة الجديدة"""
        zone_prices = {
            'cairo_giza': self.cairo_zone_price,
            'alexandria': self.alex_zone_price,
            'delta': self.delta_zone_price,
            'upper_egypt': self.upper_zone_price,
            'canal': self.canal_zone_price,
            'red_sea_sinai': self.red_sea_zone_price,
            'remote': self.remote_zone_price
        }

        # إنشاء كائن مؤقت
        return self.env['shipping.governorate.price'].new({
            'company_id': self.id,
            'egypt_governorate_id': egypt_governorate_id,
            'zone': zone,
            'base_price': zone_prices.get(zone, 50),
            'price_per_kg': self.unified_price_per_kg,
            'delivery_days_min': 2 if zone in ['cairo_giza', 'alexandria'] else 3,
            'delivery_days_max': 3 if zone in ['cairo_giza', 'alexandria'] else 5,
        })

    @api.model
    def initialize_default_prices_egypt(self):
        """إنشاء أسعار افتراضية لجميع المحافظات الجديدة"""
        governorates = self.env['egypt.governorate'].search([])

        for company in self.search([]):
            for governorate in governorates:
                # تحقق من عدم وجود سعر مسبق
                existing = self.env['shipping.governorate.price'].search([
                    ('company_id', '=', company.id),
                    ('egypt_governorate_id', '=', governorate.id)
                ])

                if not existing:
                    zone_prices = {
                        'cairo_giza': company.cairo_zone_price,
                        'alexandria': company.alex_zone_price,
                        'delta': company.delta_zone_price,
                        'upper_egypt': company.upper_zone_price,
                        'canal': company.canal_zone_price,
                        'red_sea_sinai': company.red_sea_zone_price,
                        'remote': company.remote_zone_price
                    }

                    self.env['shipping.governorate.price'].create({
                        'company_id': company.id,
                        'egypt_governorate_id': governorate.id,
                        'base_price': zone_prices.get(governorate.zone, 50),
                        'price_per_kg': company.default_price_per_kg,
                        'delivery_days_min': 2 if governorate.zone in ['cairo_giza', 'alexandria'] else 3,
                        'delivery_days_max': 3 if governorate.zone in ['cairo_giza', 'alexandria'] else 5,
                    })

        return True


class ShippingCityDistrictPrice(models.Model):
    """أسعار الشحن حسب المدن/الأحياء لكل شركة شحن"""
    _name = 'shipping.city.district.price'
    _description = 'Shipping City/District Pricing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'city_district_id'
    _order = 'company_id, city_district_id'

    company_id = fields.Many2one(
        'shipping.company',
        string='Shipping Company',
        required=True,
        ondelete='cascade',
        tracking=True
    )

    city_district_id = fields.Many2one(
        'egypt.governorate.city',
        string='City/District',
        required=True,
        tracking=True
    )

    area_id = fields.Many2one(
        related='city_district_id.area_id',
        string='Area',
        store=True,
        readonly=True
    )

    governorate_id = fields.Many2one(
        related='city_district_id.area_id.governorate_id',
        string='Governorate',
        store=True,
        readonly=True
    )

    # التسعير الأساسي فقط - بدون سعر الوزن
    base_price = fields.Float(
        string='Base Price (EGP)',
        required=True,
        default=0.0,
        help='Base shipping price for this city/district',
        tracking=True
    )

    # رسوم إضافية
    cod_fee = fields.Float(
        string='COD Fee',
        default=0.0,
        help='Cash on delivery fee for this city/district'
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

    _sql_constraints = [
        ('unique_company_city_district',
         'UNIQUE(company_id, city_district_id)',
         'Each city/district can have only one price configuration per shipping company!')
    ]

    @api.constrains('base_price')
    def _check_prices(self):
        for record in self:
            if record.base_price < 0:
                raise ValidationError(_('Base price cannot be negative!'))

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
            name = f"{record.company_id.name} - {record.city_district_id.name} ({record.base_price:.0f} EGP)"
            result.append((record.id, name))
        return result
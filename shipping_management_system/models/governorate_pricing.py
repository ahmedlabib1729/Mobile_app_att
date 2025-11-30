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

    # ===== تسعير إضافي حسب الوزن - محدث ليصبح اختياري =====
    price_per_kg = fields.Float(
        string='Price per KG',
        default=0.0,
        tracking=True,
        help='Price per kilogram for this specific governorate. If 0 or empty, the unified company price will be used.'
    )

    # إضافة حقل محسوب لعرض السعر الفعلي
    effective_price_per_kg = fields.Float(
        string='Effective Price/KG',
        compute='_compute_effective_price_per_kg',
        store=True,
        help='The actual price per kg that will be used (governorate-specific or unified)'
    )

    @api.depends('price_per_kg', 'company_id.unified_price_per_kg')
    def _compute_effective_price_per_kg(self):
        """حساب السعر الفعلي للكيلو (أولوية المحافظة ثم الموحد)"""
        for record in self:
            if record.price_per_kg > 0:
                record.effective_price_per_kg = record.price_per_kg
            else:
                record.effective_price_per_kg = record.company_id.unified_price_per_kg if record.company_id else 0

    # ===== حد الوزن المجاني - جديد =====
    free_weight_limit = fields.Float(
        string='Free Weight Limit (KG) - Optional',
        default=0.0,
        tracking=True,
        help='Free weight limit for this specific governorate. If 0, the unified company limit will be used.'
    )

    # إضافة حقل محسوب لعرض حد الوزن المجاني الفعلي
    effective_free_weight_limit = fields.Float(
        string='Effective Free Weight (KG)',
        compute='_compute_effective_free_weight_limit',
        store=True,
        help='The actual free weight limit that will be used (governorate-specific or unified)'
    )

    @api.depends('free_weight_limit', 'company_id.free_weight_limit')
    def _compute_effective_free_weight_limit(self):
        """حساب حد الوزن المجاني الفعلي (أولوية المحافظة ثم الموحد)"""
        for record in self:
            if record.free_weight_limit > 0:
                record.effective_free_weight_limit = record.free_weight_limit
            else:
                record.effective_free_weight_limit = record.company_id.free_weight_limit if record.company_id else 0

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

    @api.constrains('base_price', 'price_per_kg', 'free_weight_limit')
    def _check_prices(self):
        for record in self:
            if record.base_price < 0:
                raise ValidationError(_('Base price cannot be negative!'))
            if record.price_per_kg < 0:
                raise ValidationError(_('Price per KG cannot be negative!'))
            if record.free_weight_limit < 0:
                raise ValidationError(_('Free weight limit cannot be negative!'))

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
            if record.price_per_kg > 0:
                name += f" + {record.price_per_kg:.2f}/kg"
            elif record.effective_price_per_kg > 0:
                name += f" + {record.effective_price_per_kg:.2f}/kg (unified)"
            if record.effective_free_weight_limit > 0:
                name += f" | Free: {record.effective_free_weight_limit:.1f}kg"
            result.append((record.id, name))
        return result

    def calculate_shipping_price(self, weight=0, cod_amount=0, service_type='normal'):
        """حساب سعر الشحن للمحافظة - محدث لاستخدام الأولوية"""
        self.ensure_one()

        # السعر الأساسي
        total_price = self.base_price

        # إضافة سعر الوزن بالأولوية الجديدة
        if weight > 0:
            # ✅ استخدام effective_free_weight_limit بدلاً من company free limit
            free_limit = self.effective_free_weight_limit
            chargeable_weight = max(0, weight - free_limit)

            if chargeable_weight > 0:
                # ✅ استخدام effective_price_per_kg مباشرة
                total_price += chargeable_weight * self.effective_price_per_kg

        # رسوم COD
        if cod_amount > 0:
            if self.cod_fee > 0:
                total_price += self.cod_fee
            if self.cod_percentage > 0:
                total_price += (cod_amount * self.cod_percentage / 100)

        # رسوم خاصة حسب نوع الخدمة
        if service_type == 'return' and self.return_fee > 0:
            total_price += self.return_fee
        elif service_type == 'exchange' and self.exchange_fee > 0:
            total_price += self.exchange_fee

        return total_price

    def get_delivery_estimate(self):
        """الحصول على تقدير مدة التسليم"""
        self.ensure_one()
        if self.delivery_days_min == self.delivery_days_max:
            return f"{self.delivery_days_min} days"
        return f"{self.delivery_days_min}-{self.delivery_days_max} days"

    @api.model
    def create_default_governorate_prices(self):
        """إنشاء أسعار افتراضية لجميع المحافظات المصرية"""
        # الحصول على جميع المحافظات
        governorates = self.env['egypt.governorate'].search([])
        companies = self.env['shipping.company'].search([])

        created_count = 0

        for company in companies:
            for governorate in governorates:
                # التحقق من عدم وجود سعر بالفعل
                existing = self.search([
                    ('company_id', '=', company.id),
                    ('egypt_governorate_id', '=', governorate.id)
                ])

                if not existing:
                    # تحديد السعر حسب المنطقة
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
                        'price_per_kg': 0,  # القيمة الافتراضية 0 = استخدام السعر الموحد
                        'free_weight_limit': 0,  # القيمة الافتراضية 0 = استخدام الحد الموحد
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

    # التسعير الأساسي
    base_price = fields.Float(
        string='Base Price (EGP)',
        required=True,
        default=0.0,
        help='Base shipping price for this city/district',
        tracking=True
    )

    # ===== إضافة حقل سعر الكيلو للمدينة - جديد =====
    price_per_kg = fields.Float(
        string='Price per KG (Optional)',
        default=0.0,
        tracking=True,
        help='Price per kilogram for this specific city/district. If 0 or empty, it will use governorate price or unified company price.'
    )

    # إضافة حقل محسوب لعرض سعر الكيلو الفعلي
    effective_price_per_kg = fields.Float(
        string='Effective Price/KG',
        compute='_compute_effective_price_per_kg',
        store=True,
        help='Price per kg: city-specific → governorate → unified company price'
    )

    free_weight_limit = fields.Float(
        string='Free Weight Limit (KG)',
        default=0.0,
        tracking=True,
        help='Free weight limit for this specific city/district. If 0 or empty, it will use governorate free weight or unified company free weight.'
    )

    @api.depends('price_per_kg', 'governorate_id', 'company_id.unified_price_per_kg')
    def _compute_effective_price_per_kg(self):
        """حساب السعر الفعلي للكيلو (أولوية المدينة ثم المحافظة ثم الموحد)"""
        for record in self:
            price_per_kg = 0

            # ✅ الأولوية الأولى: سعر الكيلو الخاص بالمدينة
            if record.price_per_kg > 0:
                price_per_kg = record.price_per_kg
            # ✅ الأولوية الثانية: محاولة الحصول على سعر الكيلو من المحافظة التابعة
            elif record.governorate_id and record.company_id:
                # البحث عن سعر المحافظة في نفس الشركة
                gov_price = self.env['shipping.governorate.price'].search([
                    ('company_id', '=', record.company_id.id),
                    ('egypt_governorate_id', '=', record.governorate_id.id),
                    ('active', '=', True)
                ], limit=1)

                if gov_price and gov_price.price_per_kg > 0:
                    price_per_kg = gov_price.price_per_kg
                else:
                    # ✅ الأولوية الثالثة: السعر الموحد من الشركة
                    price_per_kg = record.company_id.unified_price_per_kg if record.company_id else 0
            else:
                # ✅ الأولوية الثالثة: السعر الموحد من الشركة
                price_per_kg = record.company_id.unified_price_per_kg if record.company_id else 0

            record.effective_price_per_kg = price_per_kg

    # ===== حقل محسوب لعرض حد الوزن المجاني الفعلي =====
    effective_free_weight_limit = fields.Float(
        string='Effective Free Weight (KG)',
        compute='_compute_effective_free_weight_limit',
        store=True,
        help='Free weight limit: from parent governorate if set, otherwise unified company limit'
    )

    @api.depends('free_weight_limit', 'governorate_id', 'company_id.free_weight_limit')
    def _compute_effective_free_weight_limit(self):
        """حساب حد الوزن المجاني الفعلي (أولوية المدينة ثم المحافظة ثم الموحد)"""
        for record in self:
            free_limit = 0

            # ✅ الأولوية الأولى: حد الوزن المجاني الخاص بالمدينة
            if record.free_weight_limit > 0:
                free_limit = record.free_weight_limit
            # ✅ الأولوية الثانية: محاولة الحصول على حد الوزن المجاني من المحافظة التابعة
            elif record.governorate_id and record.company_id:
                gov_price = self.env['shipping.governorate.price'].search([
                    ('company_id', '=', record.company_id.id),
                    ('egypt_governorate_id', '=', record.governorate_id.id),
                    ('active', '=', True)
                ], limit=1)

                if gov_price and gov_price.free_weight_limit > 0:
                    free_limit = gov_price.free_weight_limit
                else:
                    # ✅ الأولوية الثالثة: الحد الموحد من الشركة
                    free_limit = record.company_id.free_weight_limit if record.company_id else 0
            else:
                # ✅ الأولوية الثالثة: الحد الموحد من الشركة
                free_limit = record.company_id.free_weight_limit if record.company_id else 0

            record.effective_free_weight_limit = free_limit

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
            name = f"{record.company_id.name} - {record.city_district_id.name} ({record.base_price:.0f} EGP)"

            # عرض سعر الكيلو مع توضيح المصدر
            if record.price_per_kg > 0:
                name += f" + {record.price_per_kg:.2f}/kg (city)"
            elif record.effective_price_per_kg > 0:
                # تحديد المصدر (محافظة أو موحد)
                gov_price = self.env['shipping.governorate.price'].search([
                    ('company_id', '=', record.company_id.id),
                    ('egypt_governorate_id', '=', record.governorate_id.id),
                    ('active', '=', True)
                ], limit=1)

                if gov_price and gov_price.price_per_kg > 0:
                    name += f" + {record.effective_price_per_kg:.2f}/kg (gov)"
                else:
                    name += f" + {record.effective_price_per_kg:.2f}/kg (unified)"

            if record.effective_free_weight_limit > 0:
                name += f" | Free: {record.effective_free_weight_limit:.1f}kg"
            result.append((record.id, name))
        return result

    def calculate_shipping_price(self, weight=0, cod_amount=0):
        """حساب سعر الشحن للمدينة - يستخدم سعر الكيلو وحد الوزن المجاني من المدينة أو المحافظة التابعة أو الموحد"""
        self.ensure_one()

        total_price = self.base_price

        # إضافة سعر الوزن مع الأولوية الجديدة
        if weight > 0:
            # ✅ استخدام effective_free_weight_limit بدلاً من company free limit
            free_limit = self.effective_free_weight_limit
            chargeable_weight = max(0, weight - free_limit)

            if chargeable_weight > 0:
                # ✅ استخدام effective_price_per_kg مباشرة (المدينة → المحافظة → الموحد)
                total_price += chargeable_weight * self.effective_price_per_kg

        # رسوم COD
        if cod_amount > 0:
            if self.cod_fee > 0:
                total_price += self.cod_fee
            if self.cod_percentage > 0:
                total_price += (cod_amount * self.cod_percentage / 100)

        return total_price
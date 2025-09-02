# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import ValidationError
import pytz


class ResConfigSettings(models.TransientModel):
    """إضافة إعدادات Pickup في الإعدادات العامة"""
    _inherit = 'res.config.settings'

    # إعدادات وقت القطع (Cutoff Time)
    pickup_cutoff_time = fields.Float(
        string='Daily Cutoff Time',
        default=15.0,  # 3:00 PM
        config_parameter='shipping_management_system.pickup_cutoff_time',
        help='Orders placed after this time will have pickup scheduled for next day (24-hour format, e.g., 15.0 for 3:00 PM)'
    )

    pickup_buffer_days = fields.Integer(
        string='Pickup Buffer Days',
        default=0,
        config_parameter='shipping_management_system.pickup_buffer_days',
        help='Additional days to add for pickup preparation'
    )

    pickup_skip_friday = fields.Boolean(
        string='Skip Friday',
        config_parameter='shipping_management_system.pickup_skip_friday',
        help='If checked, Friday will be skipped for pickup scheduling'
    )

    pickup_skip_saturday = fields.Boolean(
        string='Skip Saturday',
        config_parameter='shipping_management_system.pickup_skip_saturday',
        help='If checked, Saturday will be skipped for pickup scheduling'
    )

    pickup_skip_sunday = fields.Boolean(
        string='Skip Sunday',
        config_parameter='shipping_management_system.pickup_skip_sunday',
        help='If checked, Sunday will be skipped for pickup scheduling'
    )

    # إعدادات متقدمة لكل يوم
    pickup_use_advanced = fields.Boolean(
        string='Use Advanced Schedule',
        config_parameter='shipping_management_system.pickup_use_advanced',
        help='Enable different cutoff times for each day of the week'
    )

    pickup_monday_cutoff = fields.Float(
        string='Monday Cutoff',
        default=15.0,
        config_parameter='shipping_management_system.pickup_monday_cutoff'
    )

    pickup_tuesday_cutoff = fields.Float(
        string='Tuesday Cutoff',
        default=15.0,
        config_parameter='shipping_management_system.pickup_tuesday_cutoff'
    )

    pickup_wednesday_cutoff = fields.Float(
        string='Wednesday Cutoff',
        default=15.0,
        config_parameter='shipping_management_system.pickup_wednesday_cutoff'
    )

    pickup_thursday_cutoff = fields.Float(
        string='Thursday Cutoff',
        default=15.0,
        config_parameter='shipping_management_system.pickup_thursday_cutoff'
    )

    pickup_friday_cutoff = fields.Float(
        string='Friday Cutoff',
        default=12.0,  # وقت مبكر يوم الجمعة
        config_parameter='shipping_management_system.pickup_friday_cutoff'
    )

    pickup_saturday_cutoff = fields.Float(
        string='Saturday Cutoff',
        default=15.0,
        config_parameter='shipping_management_system.pickup_saturday_cutoff'
    )

    pickup_sunday_cutoff = fields.Float(
        string='Sunday Cutoff',
        default=15.0,
        config_parameter='shipping_management_system.pickup_sunday_cutoff'
    )


class ShipmentOrder(models.Model):
    _inherit = 'shipment.order'

    # حقل جديد لتوضيح كيف تم حساب التاريخ
    pickup_date_calculated = fields.Boolean(
        string='Auto Calculated',
        default=False,
        readonly=True,
        help='Indicates if pickup date was automatically calculated'
    )

    pickup_calculation_note = fields.Text(
        string='Pickup Calculation Note',
        readonly=True,
        help='Explanation of how pickup date was calculated'
    )

    @api.model
    def _get_pickup_cutoff_time(self, date_obj=None):
        """الحصول على وقت القطع لليوم المحدد"""
        if not date_obj:
            date_obj = datetime.now()

        # التحقق من استخدام الجدول المتقدم
        use_advanced = self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_use_advanced',
            default=False
        )

        if use_advanced:
            # الحصول على وقت القطع حسب اليوم
            weekday = date_obj.weekday()  # 0 = Monday, 6 = Sunday
            day_mapping = {
                0: 'monday',
                1: 'tuesday',
                2: 'wednesday',
                3: 'thursday',
                4: 'friday',
                5: 'saturday',
                6: 'sunday'
            }

            param_name = f'shipping_management_system.pickup_{day_mapping[weekday]}_cutoff'
            cutoff_time = float(self.env['ir.config_parameter'].sudo().get_param(
                param_name,
                default=15.0
            ))
        else:
            # استخدام الوقت الواحد لجميع الأيام
            cutoff_time = float(self.env['ir.config_parameter'].sudo().get_param(
                'shipping_management_system.pickup_cutoff_time',
                default=15.0
            ))

        return cutoff_time

    @api.model
    def _is_working_day(self, date_obj):
        """التحقق من أن اليوم يوم عمل"""
        weekday = date_obj.weekday()

        # التحقق من الأيام المستثناة
        skip_friday = self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_skip_friday',
            default=False
        )
        skip_saturday = self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_skip_saturday',
            default=False
        )
        skip_sunday = self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_skip_sunday',
            default=False
        )

        # Friday = 4, Saturday = 5, Sunday = 6
        if weekday == 4 and skip_friday:
            return False
        if weekday == 5 and skip_saturday:
            return False
        if weekday == 6 and skip_sunday:
            return False

        # يمكن إضافة التحقق من العطلات الرسمية هنا
        # holidays = self.env['hr.holidays.public'].search([...])

        return True

    @api.model
    def _calculate_pickup_date(self, order_datetime=None):
        """حساب تاريخ الاستلام بناءً على الإعدادات"""
        if not order_datetime:
            order_datetime = datetime.now()

        # الحصول على وقت القطع
        cutoff_time = self._get_pickup_cutoff_time(order_datetime)

        # الحصول على الـ buffer days
        buffer_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_buffer_days',
            default=0
        ))

        # تحويل وقت القطع إلى ساعات ودقائق
        cutoff_hour = int(cutoff_time)
        cutoff_minute = int((cutoff_time - cutoff_hour) * 60)

        # إنشاء datetime object لوقت القطع
        cutoff_datetime = order_datetime.replace(
            hour=cutoff_hour,
            minute=cutoff_minute,
            second=0,
            microsecond=0
        )

        # تحديد تاريخ البداية
        if order_datetime > cutoff_datetime:
            # الطلب بعد وقت القطع - نبدأ من اليوم التالي
            pickup_date = order_datetime + timedelta(days=1)
            calculation_note = f"Order placed after cutoff time ({cutoff_time:.1f}:00), pickup scheduled for next day"
        else:
            # الطلب قبل وقت القطع - نفس اليوم
            pickup_date = order_datetime
            calculation_note = f"Order placed before cutoff time ({cutoff_time:.1f}:00), pickup scheduled for same day"

        # إضافة buffer days
        if buffer_days > 0:
            pickup_date += timedelta(days=buffer_days)
            calculation_note += f" + {buffer_days} buffer day(s)"

        # التحقق من أيام العمل
        days_added = 0
        while not self._is_working_day(pickup_date):
            pickup_date += timedelta(days=1)
            days_added += 1

        if days_added > 0:
            calculation_note += f" + {days_added} day(s) to skip non-working days"

        return pickup_date, calculation_note

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-calculate pickup date"""
        for vals in vals_list:
            if 'pickup_date' not in vals or not vals.get('pickup_date'):
                # حساب تاريخ الاستلام تلقائياً
                pickup_date, note = self._calculate_pickup_date()
                vals['pickup_date'] = pickup_date
                vals['pickup_date_calculated'] = True
                vals['pickup_calculation_note'] = note

        return super(ShipmentOrder, self).create(vals_list)

    def action_recalculate_pickup_date(self):
        """زر لإعادة حساب تاريخ الاستلام"""
        self.ensure_one()

        pickup_date, note = self._calculate_pickup_date(self.create_date)

        self.write({
            'pickup_date': pickup_date,
            'pickup_date_calculated': True,
            'pickup_calculation_note': note
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pickup Date Updated'),
                'message': note,
                'type': 'success',
                'sticky': False,
            }
        }


class PickupScheduleRule(models.Model):
    """نموذج اختياري للقواعد المتقدمة"""
    _name = 'pickup.schedule.rule'
    _description = 'Pickup Schedule Rules'
    _order = 'sequence, id'

    name = fields.Char(
        string='Rule Name',
        required=True
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # شروط القاعدة
    governorate_ids = fields.Many2many(
        'res.country.state',
        string='Governorates',
        domain=[('country_id.code', '=', 'EG')],
        help='Apply this rule only for these governorates'
    )

    customer_category_ids = fields.Many2many(
        'customer.price.category',
        string='Customer Categories',
        help='Apply this rule only for these customer categories'
    )

    min_weight = fields.Float(
        string='Min Weight (KG)',
        default=0
    )

    max_weight = fields.Float(
        string='Max Weight (KG)',
        default=0,
        help='0 means no limit'
    )

    # الإجراء
    additional_days = fields.Integer(
        string='Additional Days',
        default=0,
        help='Days to add to pickup date when this rule applies'
    )

    cutoff_time_override = fields.Float(
        string='Override Cutoff Time',
        help='Override the default cutoff time for this rule'
    )

    note = fields.Text(
        string='Note',
        help='Note to display when this rule is applied'
    )
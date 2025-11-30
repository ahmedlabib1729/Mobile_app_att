# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta, time
from odoo.exceptions import ValidationError
import pytz
import logging

_logger = logging.getLogger(__name__)



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
            default='False'
        ) == 'True'

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
                default='15.0'
            ))
        else:
            # استخدام الوقت الواحد لجميع الأيام
            cutoff_time = float(self.env['ir.config_parameter'].sudo().get_param(
                'shipping_management_system.pickup_cutoff_time',
                default='15.0'
            ))

        return cutoff_time

    @api.model
    def _is_working_day(self, date_obj):
        """التحقق من أن اليوم يوم عمل"""
        weekday = date_obj.weekday()

        # التحقق من الأيام المستثناة
        skip_friday = self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_skip_friday',
            default='False'
        ) == 'True'

        skip_saturday = self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_skip_saturday',
            default='False'
        ) == 'True'

        skip_sunday = self.env['ir.config_parameter'].sudo().get_param(
            'shipping_management_system.pickup_skip_sunday',
            default='False'
        ) == 'True'

        # Friday = 4, Saturday = 5, Sunday = 6
        if weekday == 4 and skip_friday:
            _logger.info(f"Friday is skipped")
            return False
        if weekday == 5 and skip_saturday:
            _logger.info(f"Saturday is skipped")
            return False
        if weekday == 6 and skip_sunday:
            _logger.info(f"Sunday is skipped")
            return False

        return True

    # shipping_management_system/models/pickup_configuration.py

    @api.model
    def _calculate_pickup_date(self, order_datetime=None):
        """حساب تاريخ الاستلام بناءً على الإعدادات - مع التعامل مع Timezone"""
        try:
            # الحصول على timezone المستخدم
            user_tz = self.env.user.tz or 'UTC'
            _logger.info(f"User timezone: {user_tz}")

            # استخدام الوقت المحلي الصحيح
            if not order_datetime:
                # استخدام الوقت المحلي للمستخدم
                import pytz
                tz = pytz.timezone(user_tz)
                # الحصول على الوقت المحلي
                local_datetime = datetime.now(tz)
                # تحويل إلى naive datetime للحفظ في Odoo
                order_datetime = local_datetime.replace(tzinfo=None)
                _logger.info(f"Using local time: {local_datetime}")
            elif hasattr(order_datetime, 'tzinfo') and order_datetime.tzinfo:
                # إذا كان معه timezone، حوله للوقت المحلي ثم اجعله naive
                import pytz
                tz = pytz.timezone(user_tz)
                local_datetime = order_datetime.astimezone(tz)
                order_datetime = local_datetime.replace(tzinfo=None)

            _logger.info(f"=== PICKUP DATE CALCULATION START ===")
            _logger.info(f"Order created at (local): {order_datetime}")
            _logger.info(f"Server system time: {datetime.now()}")

            # الحصول على وقت القطع من الإعدادات
            cutoff_param = self.env['ir.config_parameter'].sudo().get_param(
                'shipping_management_system.pickup_cutoff_time',
                default='15.0'  # 3:00 PM default
            )
            cutoff_time = float(cutoff_param)
            _logger.info(f"Cutoff time setting: {cutoff_time}")

            # الحصول على buffer days
            buffer_days = int(self.env['ir.config_parameter'].sudo().get_param(
                'shipping_management_system.pickup_buffer_days',
                default='0'
            ))

            # تحويل وقت القطع إلى ساعات ودقائق
            cutoff_hour = int(cutoff_time)
            cutoff_minute = int((cutoff_time - cutoff_hour) * 60)

            # الوقت الحالي للطلب
            order_hour = order_datetime.hour
            order_minute = order_datetime.minute
            order_time_decimal = order_hour + (order_minute / 60.0)

            _logger.info(f"Order time (local): {order_hour:02d}:{order_minute:02d} ({order_time_decimal:.2f})")
            _logger.info(f"Cutoff: {cutoff_hour:02d}:{cutoff_minute:02d} ({cutoff_time:.2f})")

            # البدء من تاريخ الطلب
            pickup_date = order_datetime

            # المقارنة بين وقت الطلب ووقت القطع
            if order_time_decimal >= cutoff_time:
                # الطلب بعد وقت القطع - اليوم التالي
                pickup_date = pickup_date + timedelta(days=1)
                calculation_note = f"Order placed after cutoff time ({cutoff_hour:02d}:{cutoff_minute:02d}), pickup scheduled for next working day"
                _logger.info("AFTER cutoff - moving to next day")
            else:
                # الطلب قبل وقت القطع - نفس اليوم
                calculation_note = f"Order placed before cutoff time ({cutoff_hour:02d}:{cutoff_minute:02d}), pickup scheduled for same day"
                _logger.info("BEFORE cutoff - same day")

            # إضافة buffer days إذا موجود
            if buffer_days > 0:
                pickup_date = pickup_date + timedelta(days=buffer_days)
                calculation_note += f" + {buffer_days} buffer day(s)"
                _logger.info(f"Added {buffer_days} buffer days")

            # التحقق من أيام العمل
            skip_friday = self.env['ir.config_parameter'].sudo().get_param(
                'shipping_management_system.pickup_skip_friday',
                default='False'
            ) == 'True'
            skip_saturday = self.env['ir.config_parameter'].sudo().get_param(
                'shipping_management_system.pickup_skip_saturday',
                default='False'
            ) == 'True'
            skip_sunday = self.env['ir.config_parameter'].sudo().get_param(
                'shipping_management_system.pickup_skip_sunday',
                default='False'
            ) == 'True'

            _logger.info(f"Skip settings - Friday: {skip_friday}, Saturday: {skip_saturday}, Sunday: {skip_sunday}")

            # تخطي أيام العطلة
            days_skipped = 0
            max_days = 10

            while days_skipped < max_days:
                weekday = pickup_date.weekday()
                day_name = pickup_date.strftime('%A')

                _logger.info(f"Checking {day_name} (weekday {weekday})")

                # Friday = 4, Saturday = 5, Sunday = 6
                if (weekday == 4 and skip_friday) or \
                        (weekday == 5 and skip_saturday) or \
                        (weekday == 6 and skip_sunday):
                    pickup_date = pickup_date + timedelta(days=1)
                    days_skipped += 1
                    _logger.info(f"{day_name} is a holiday - skipping")
                else:
                    _logger.info(f"{day_name} is a working day - OK")
                    break

            if days_skipped > 0:
                calculation_note += f" + {days_skipped} day(s) skipped (holidays/weekends)"

            # تحديد وقت الاستلام (9:00 صباحاً افتراضياً)
            pickup_date = pickup_date.replace(hour=9, minute=0, second=0, microsecond=0)

            _logger.info(f"FINAL pickup date (local): {pickup_date}")
            _logger.info(f"Note: {calculation_note}")
            _logger.info(f"=== CALCULATION END ===")

            return pickup_date, calculation_note

        except Exception as e:
            _logger.error(f"ERROR in pickup calculation: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            # في حالة خطأ
            tomorrow = datetime.now() + timedelta(days=1)
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0), f"Error: {str(e)}"

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

    def action_recalculate_pickup_date(self):
        """زر لإعادة حساب تاريخ الاستلام"""
        self.ensure_one()

        try:
            # استخدام تاريخ الإنشاء أو التاريخ الحالي
            order_datetime = self.create_date if self.create_date else datetime.now()

            # تأكد من أنه naive datetime
            if hasattr(order_datetime, 'tzinfo') and order_datetime.tzinfo:
                order_datetime = order_datetime.replace(tzinfo=None)

            pickup_date, note = self._calculate_pickup_date(order_datetime)

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
        except Exception as e:
            _logger.error(f"Error in action_recalculate_pickup_date: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    @api.model
    def _get_default_pickup_date(self):
        """حساب pickup date الافتراضي عند فتح الفورم"""
        try:
            pickup_date, note = self._calculate_pickup_date()
            return pickup_date
        except Exception as e:
            _logger.error(f"Error in _get_default_pickup_date: {str(e)}")
            return fields.Datetime.now()


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
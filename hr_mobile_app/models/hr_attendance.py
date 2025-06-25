# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import math
import pytz
import re


_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # إضافة حقول جديدة إذا كنت بحاجة إليها
    mobile_created = fields.Boolean(
        string="تم الإنشاء من التطبيق",
        default=False,
        help="يشير إلى ما إذا كان سجل الحضور قد تم إنشاؤه من التطبيق المحمول"
    )

    # حقول الموقع الجغرافي الجديدة
    check_in_latitude = fields.Float(
        string="خط العرض عند الحضور",
        digits=(10, 6),
        help="خط العرض (Latitude) لموقع تسجيل الحضور"
    )

    check_in_longitude = fields.Float(
        string="خط الطول عند الحضور",
        digits=(10, 6),
        help="خط الطول (Longitude) لموقع تسجيل الحضور"
    )

    check_out_latitude = fields.Float(
        string="خط العرض عند الانصراف",
        digits=(10, 6),
        help="خط العرض (Latitude) لموقع تسجيل الانصراف"
    )

    check_out_longitude = fields.Float(
        string="خط الطول عند الانصراف",
        digits=(10, 6),
        help="خط الطول (Longitude) لموقع تسجيل الانصراف"
    )

    location_verified = fields.Boolean(
        string="تم التحقق من الموقع",
        default=False,
        help="يشير إلى ما إذا كان الموقع قد تم التحقق منه وهو ضمن النطاق المسموح"
    )

    check_in_distance = fields.Float(
        string="المسافة عند الحضور (متر)",
        help="المسافة بين موقع الموظف وموقع المكتب عند تسجيل الحضور"
    )

    check_out_distance = fields.Float(
        string="المسافة عند الانصراف (متر)",
        help="المسافة بين موقع الموظف وموقع المكتب عند تسجيل الانصراف"
    )

    @api.model
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        حساب المسافة بين نقطتين جغرافيتين باستخدام Haversine formula
        المسافة المرجعة بالأمتار
        """
        # نصف قطر الأرض بالكيلومتر
        R = 6371.0

        # تحويل من درجات إلى راديان
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # الفرق بين الإحداثيات
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # حساب Haversine
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # المسافة بالكيلومتر
        distance_km = R * c

        # تحويل إلى أمتار
        distance_m = distance_km * 1000

        return distance_m

    @api.model
    def _verify_location(self, employee_id, latitude, longitude):
        """
        التحقق من أن الموقع ضمن النطاق المسموح للموظف
        إرجاع tuple: (is_valid, distance, office_location)
        """
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return False, 0, {}

        # التحقق من السماح بالعمل عن بُعد
        if employee.allow_remote_attendance:
            return True, 0, {
                'latitude': latitude,
                'longitude': longitude,
                'radius': 0,
                'remote_allowed': True
            }

        # التحقق من المواقع المؤقتة
        today = fields.Date.today()
        temp_location = employee.temporary_location_ids.filtered(
            lambda l: l.date_from <= today <= l.date_to
        )

        if temp_location:
            # استخدام أول موقع مؤقت صالح
            temp_loc = temp_location[0]
            distance = self._calculate_distance(
                latitude, longitude,
                temp_loc.latitude, temp_loc.longitude
            )
            is_valid = distance <= temp_loc.allowed_radius

            return is_valid, distance, {
                'latitude': temp_loc.latitude,
                'longitude': temp_loc.longitude,
                'radius': temp_loc.allowed_radius,
                'temporary': True,
                'reason': temp_loc.reason
            }

        # استخدام موقع المكتب المخصص للموظف
        office_location = employee.office_location_id

        # إذا لم يكن للموظف موقع مخصص، استخدم موقع القسم
        if not office_location and employee.department_id:
            office_location = employee.department_id.office_location_id

        # إذا لم يكن هناك موقع محدد، استخدم موقع افتراضي
        if not office_location:
            # موقع افتراضي مؤقت - يجب تحديد موقع للموظف
            return False, 0, {
                'error': 'لم يتم تحديد موقع مكتب للموظف'
            }

        # حساب المسافة
        distance = self._calculate_distance(
            latitude, longitude,
            office_location.latitude, office_location.longitude
        )

        # التحقق من النطاق
        # استخدام النطاق المرن إذا كان مفعلاً وفي أوقات معينة
        allowed_radius = office_location.allowed_radius
        if office_location.allow_flexible_radius:
            # يمكن إضافة شروط إضافية هنا (مثل أوقات الذروة)
            current_hour = fields.Datetime.now().hour
            if 7 <= current_hour <= 10 or 16 <= current_hour <= 19:
                allowed_radius = office_location.flexible_radius

        is_valid = distance <= allowed_radius

        return is_valid, distance, {
            'latitude': office_location.latitude,
            'longitude': office_location.longitude,
            'radius': allowed_radius,
            'location_name': office_location.name,
            'location_id': office_location.id
        }

    @api.model
    def get_employee_attendance_status(self, employee_id):
        """الحصول على حالة الحضور الحالية للموظف"""
        # التحقق من صحة المعرف
        if not employee_id or not isinstance(employee_id, int):
            return {'is_checked_in': False, 'check_in': None, 'attendance_id': None}

        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'is_checked_in': False, 'check_in': None, 'attendance_id': None}

        # التحقق مما إذا كان الموظف قد سجل حضوره بالفعل ولم يسجل انصرافه
        attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False)
        ], limit=1)

        if attendance:
            # إرسال الوقت كما هو (Odoo يحفظه كـ UTC)
            return {
                'is_checked_in': True,
                'check_in': attendance.check_in.isoformat() + 'Z',  # إضافة Z للإشارة إلى UTC
                'attendance_id': attendance.id,
            }

        return {
            'is_checked_in': False,
            'check_in': None,
            'attendance_id': None,
        }
    @api.model
    def create_mobile_attendance(self, employee_id):
        """إنشاء سجل حضور جديد من التطبيق المحمول"""
        if not employee_id or not isinstance(employee_id, int):
            return {'success': False, 'error': 'معرف الموظف غير صالح'}

        # التحقق من أن الموظف موجود
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'success': False, 'error': 'الموظف غير موجود'}

        # التحقق من عدم وجود سجل حضور مفتوح
        open_attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False),
        ], limit=1)

        if open_attendance:
            return {
                'success': False,
                'error': 'يوجد بالفعل سجل حضور مفتوح لهذا الموظف'
            }

        try:
            # إنشاء سجل حضور جديد
            attendance = self.create({
                'employee_id': employee_id,
                'check_in': fields.Datetime.now(),
                'mobile_created': True,
            })

            _logger.info(f"تم إنشاء سجل حضور جديد بنجاح للموظف {employee.name} بواسطة التطبيق المحمول.")

            return {
                'success': True,
                'attendance_id': attendance.id,
            }
        except Exception as e:
            _logger.error(f"خطأ أثناء إنشاء سجل حضور للموظف {employee.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }

    @api.model
    def update_mobile_attendance_checkout(self, attendance_id):
        """تحديث سجل حضور بوقت الانصراف من التطبيق المحمول"""
        if not attendance_id or not isinstance(attendance_id, int):
            return {'success': False, 'error': 'معرف سجل الحضور غير صالح'}

        # التحقق من أن سجل الحضور موجود
        attendance = self.browse(attendance_id)
        if not attendance.exists():
            return {'success': False, 'error': 'سجل الحضور غير موجود'}

        # التحقق من أن سجل الحضور ليس له وقت انصراف بالفعل
        if attendance.check_out:
            return {
                'success': False,
                'error': 'تم تسجيل وقت الانصراف بالفعل لهذا السجل'
            }

        try:
            # تحديث سجل الحضور بوقت الانصراف
            attendance.write({
                'check_out': fields.Datetime.now(),
            })

            _logger.info(f"تم تحديث سجل الحضور {attendance.id} بوقت الانصراف بنجاح بواسطة التطبيق المحمول.")

            # حساب مدة العمل
            check_in = attendance.check_in.isoformat() + 'Z' if attendance.check_in else None
            check_out = attendance.check_out
            duration = (check_out - check_in).total_seconds() / 3600.0  # بالساعات

            hours = int(duration)
            minutes = int((duration - hours) * 60)
            duration_str = f"{hours}:{minutes:02d}"

            return {
                'success': True,
                'duration': duration_str,
            }
        except Exception as e:
            _logger.error(f"خطأ أثناء تحديث سجل الحضور {attendance_id} بوقت الانصراف: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }

    @api.model
    def get_employee_attendance_summary(self, employee_id):
        """الحصول على ملخص الحضور اليومي للموظف"""
        if not employee_id or not isinstance(employee_id, int):
            return {'work_hours': '0:00', 'request_count': 0}

        # التحقق من أن الموظف موجود
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'work_hours': '0:00', 'request_count': 0}

        # حساب وقت العمل اليوم
        today = fields.Date.today()
        today_start = fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))

        # البحث عن سجلات الحضور لهذا اليوم
        domain = [
            ('employee_id', '=', employee_id),
            ('check_in', '>=', today_start),
        ]

        # سجلات الحضور المكتملة (مع وقت انصراف)
        completed_attendances = self.search(domain + [('check_out', '!=', False)])

        # سجل الحضور المفتوح (بدون وقت انصراف)
        open_attendance = self.search(domain + [('check_out', '=', False)], limit=1)

        # حساب إجمالي وقت العمل
        total_worked_hours = 0.0

        # إضافة وقت العمل من السجلات المكتملة
        for attendance in completed_attendances:
            delta = (attendance.check_out - attendance.check_in).total_seconds() / 3600.0
            total_worked_hours += delta

        # إضافة وقت العمل من السجل المفتوح (إذا وجد)
        if open_attendance:
            now = fields.Datetime.now()
            delta = (now - open_attendance.check_in).total_seconds() / 3600.0
            total_worked_hours += delta

        # تنسيق وقت العمل
        hours = int(total_worked_hours)
        minutes = int((total_worked_hours - hours) * 60)
        work_hours = f"{hours}:{minutes:02d}"

        # حساب عدد الطلبات النشطة
        leave_count = self.env['hr.leave'].search_count([
            ('employee_id', '=', employee_id),
            ('state', 'in', ['draft', 'confirm', 'validate1']),
        ])

        # يمكنك إضافة أنواع طلبات أخرى هنا إذا كنت ترغب في ذلك
        # مثال: طلبات السلف أو المصروفات
        expense_count = 0
        if 'hr.expense' in self.env:
            expense_count = self.env['hr.expense'].search_count([
                ('employee_id', '=', employee_id),
                ('state', 'in', ['draft', 'reported', 'approved']),
            ])

        request_count = leave_count + expense_count

        return {
            'work_hours': work_hours,
            'request_count': request_count,
        }

    @api.model
    def get_employee_attendance_history(self, employee_id, limit=10):
        """الحصول على سجل الحضور السابق للموظف"""
        if not employee_id or not isinstance(employee_id, int):
            return []

        # التحقق من أن الموظف موجود
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return []

        # البحث عن سجلات الحضور السابقة
        attendances = self.search([
            ('employee_id', '=', employee_id),
        ], order='check_in desc', limit=limit)

        result = []
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        for attendance in attendances:
            # الحصول على التاريخ من attendance.check_in مباشرة
            check_in_datetime = attendance.check_in
            check_in_date = check_in_datetime.date()

            # تحديد اسم اليوم
            if check_in_date == today:
                date_str = 'اليوم'
            elif check_in_date == yesterday:
                date_str = 'الأمس'
            else:
                # تنسيق التاريخ بالعربية
                date_str = check_in_datetime.strftime('%d/%m/%Y')

            # تنسيق وقت الحضور
            check_in_str = check_in_datetime.strftime('%I:%M %p')

            # تنسيق وقت الانصراف (إذا كان موجودًا)
            check_out_str = None
            duration_str = '0:00'

            if attendance.check_out:
                check_out_datetime = attendance.check_out
                check_out_str = check_out_datetime.strftime('%I:%M %p')

                # حساب المدة
                duration = (check_out_datetime - check_in_datetime).total_seconds() / 3600.0
                hours = int(duration)
                minutes = int((duration - hours) * 60)
                duration_str = f"{hours}:{minutes:02d}"

            # إضافة معلومات الموقع إذا كانت متوفرة
            attendance_data = {
                'date': date_str,
                'checkIn': check_in_str,
                'checkOut': check_out_str,
                'duration': duration_str,
                'locationVerified': attendance.location_verified,
            }

            # إضافة معلومات الموقع للعرض في التطبيق
            if attendance.check_in_latitude and attendance.check_in_longitude:
                attendance_data[
                    'check_in_location'] = f"{attendance.check_in_latitude:.4f}, {attendance.check_in_longitude:.4f}"
                if attendance.check_in_distance:
                    attendance_data['check_in_distance'] = f"{attendance.check_in_distance:.0f}m"

            if attendance.check_out_latitude and attendance.check_out_longitude:
                attendance_data[
                    'check_out_location'] = f"{attendance.check_out_latitude:.4f}, {attendance.check_out_longitude:.4f}"
                if attendance.check_out_distance:
                    attendance_data['check_out_distance'] = f"{attendance.check_out_distance:.0f}m"

            result.append(attendance_data)

        return result
    @api.model
    def clean_datetime_str(self, datetime_str):
        """تنظيف سلسلة التاريخ والوقت للتأكد من أنها بالتنسيق المناسب لـ Odoo"""
        # إذا كانت القيمة بالفعل بتنسيق Odoo المناسب
        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', datetime_str):
            return datetime_str

        # إذا كانت بتنسيق ISO
        if 'T' in datetime_str:
            try:
                # تحويل من تنسيق ISO إلى تنسيق Odoo
                dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

        # محاولة تحويل التنسيق باستخدام الطرق العامة
        for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S']:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue

        # إذا فشلت كل المحاولات السابقة، ارجاع الوقت الحالي
        _logger.warning(f"تم استلام تنسيق تاريخ غير معروف: {datetime_str}. استخدام الوقت الحالي بدلاً منه.")
        return fields.Datetime.now()

    @api.model
    def mobile_check_in(self, employee_id, latitude=None, longitude=None):
        """تسجيل حضور من التطبيق المحمول مع التحقق من الموقع"""
        if not employee_id:
            return {'success': False, 'error': 'معرف الموظف غير صالح'}

        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'success': False, 'error': 'الموظف غير موجود'}

        # التحقق من عدم وجود سجل حضور مفتوح
        open_attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False),
        ], limit=1)

        if open_attendance:
            return {
                'success': False,
                'error': 'يوجد بالفعل سجل حضور مفتوح لهذا الموظف'
            }

        # التحقق من الموقع إذا تم إرسال الإحداثيات
        location_verified = False
        distance = 0

        if latitude is not None and longitude is not None:
            is_valid, distance, office_location = self._verify_location(
                employee_id, latitude, longitude
            )

            if not is_valid:
                return {
                    'success': False,
                    'error': f'موقعك الحالي بعيد عن مكان العمل. المسافة: {distance:.0f} متر',
                    'distance': distance,
                    'allowed_radius': office_location['radius'],
                    'office_location': office_location
                }

            location_verified = True

        try:
            # استخدام وقت الخادم الحالي مباشرة
            now = fields.Datetime.now()

            # إنشاء سجل حضور جديد
            attendance_vals = {
                'employee_id': employee_id,
                'check_in': now,
                'mobile_created': True,
            }

            # إضافة بيانات الموقع إذا كانت متوفرة
            if latitude is not None and longitude is not None:
                attendance_vals.update({
                    'check_in_latitude': latitude,
                    'check_in_longitude': longitude,
                    'location_verified': location_verified,
                    'check_in_distance': distance
                })

            attendance = self.create(attendance_vals)

            _logger.info(f"تم إنشاء سجل حضور جديد بنجاح للموظف {employee.name} في {now}.")

            return {
                'success': True,
                'attendance_id': attendance.id,
                'location_verified': location_verified,
                'distance': distance
            }
        except Exception as e:
            _logger.error(f"خطأ أثناء إنشاء سجل حضور للموظف {employee.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }

    @api.model
    def mobile_check_out(self, employee_id, latitude=None, longitude=None):
        """تسجيل انصراف من التطبيق المحمول مع التحقق من الموقع"""
        if not employee_id:
            return {'success': False, 'error': 'معرف الموظف غير صالح'}

        # البحث عن آخر سجل حضور مفتوح للموظف
        attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False),
        ], limit=1)

        if not attendance:
            return {
                'success': False,
                'error': 'لا يوجد سجل حضور مفتوح للموظف'
            }

        # التحقق من الموقع إذا تم إرسال الإحداثيات
        location_verified = False
        distance = 0

        if latitude is not None and longitude is not None:
            is_valid, distance, office_location = self._verify_location(
                employee_id, latitude, longitude
            )

            if not is_valid:
                return {
                    'success': False,
                    'error': f'موقعك الحالي بعيد عن مكان العمل. المسافة: {distance:.0f} متر',
                    'distance': distance,
                    'allowed_radius': office_location['radius'],
                    'office_location': office_location
                }

            location_verified = True

        try:
            # استخدام وقت الخادم الحالي مباشرة
            now = fields.Datetime.now()

            # تحديث سجل الحضور بوقت الانصراف
            update_vals = {
                'check_out': now,
            }

            # إضافة بيانات الموقع إذا كانت متوفرة
            if latitude is not None and longitude is not None:
                update_vals.update({
                    'check_out_latitude': latitude,
                    'check_out_longitude': longitude,
                    'check_out_distance': distance
                })

                # تحديث حالة التحقق من الموقع إذا كان الحضور والانصراف من موقع صحيح
                if attendance.location_verified:
                    update_vals['location_verified'] = location_verified

            attendance.write(update_vals)

            _logger.info(f"تم تسجيل الانصراف بنجاح للموظف {attendance.employee_id.name} في {now}.")

            # حساب مدة العمل
            duration = (attendance.check_out - attendance.check_in).total_seconds() / 3600.0
            hours = int(duration)
            minutes = int((duration - hours) * 60)
            duration_str = f"{hours}:{minutes:02d}"

            return {
                'success': True,
                'duration': duration_str,
                'location_verified': location_verified,
                'distance': distance
            }
        except Exception as e:
            _logger.error(f"خطأ أثناء تسجيل انصراف الموظف: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }

    @api.model
    def check_location_before_attendance(self, employee_id, latitude, longitude):
        """التحقق من الموقع قبل السماح بتسجيل الحضور/الانصراف"""
        if not employee_id:
            return {'success': False, 'error': 'معرف الموظف غير صالح'}

        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'success': False, 'error': 'الموظف غير موجود'}

        # التحقق من الموقع
        is_valid, distance, office_location = self._verify_location(
            employee_id, latitude, longitude
        )

        return {
            'success': True,
            'location_valid': is_valid,
            'distance': distance,
            'allowed_radius': office_location['radius'],
            'office_location': office_location,
            'message': 'موقعك ضمن النطاق المسموح' if is_valid else f'موقعك بعيد {distance:.0f} متر عن مكان العمل'
        }
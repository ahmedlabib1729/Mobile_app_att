# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # إضافة حقول جديدة إذا كنت بحاجة إليها
    mobile_created = fields.Boolean(
        string="تم الإنشاء من التطبيق",
        default=False,
        help="يشير إلى ما إذا كان سجل الحضور قد تم إنشاؤه من التطبيق المحمول"
    )

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
            ('check_out', '=', False),
        ], limit=1)

        if attendance:
            return {
                'is_checked_in': True,
                'check_in': fields.Datetime.to_string(attendance.check_in),
                'attendance_id': attendance.id,
            }
        else:
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
            check_in = attendance.check_in
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
            check_in = attendance.check_in
            check_in_date = check_in.date()

            # تحديد اسم اليوم
            if check_in_date == today:
                date_str = 'اليوم'
            elif check_in_date == yesterday:
                date_str = 'الأمس'
            else:
                # تنسيق التاريخ بالعربية
                date_str = check_in.strftime('%d/%m/%Y')

            # تنسيق وقت الحضور
            check_in_str = check_in.strftime('%I:%M %p')

            # تنسيق وقت الانصراف (إذا كان موجودًا)
            check_out_str = None
            duration_str = '0:00'

            if attendance.check_out:
                check_out = attendance.check_out
                check_out_str = check_out.strftime('%I:%M %p')

                # حساب المدة
                duration = (check_out - check_in).total_seconds() / 3600.0
                hours = int(duration)
                minutes = int((duration - hours) * 60)
                duration_str = f"{hours}:{minutes:02d}"

            result.append({
                'date': date_str,
                'checkIn': check_in_str,
                'checkOut': check_out_str,
                'duration': duration_str,
            })

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
    def mobile_check_in(self, employee_id):
        """تسجيل حضور من التطبيق المحمول"""
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

        try:
            # استخدام وقت الخادم الحالي مباشرة
            now = fields.Datetime.now()

            # إنشاء سجل حضور جديد
            attendance = self.create({
                'employee_id': employee_id,
                'check_in': now,
            })

            _logger.info(f"تم إنشاء سجل حضور جديد بنجاح للموظف {employee.name} في {now}.")

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
    def mobile_check_out(self, employee_id):
        """تسجيل انصراف من التطبيق المحمول"""
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

        try:
            # استخدام وقت الخادم الحالي مباشرة
            now = fields.Datetime.now()

            # تحديث سجل الحضور بوقت الانصراف
            attendance.write({
                'check_out': now,
            })

            _logger.info(f"تم تسجيل الانصراف بنجاح للموظف {attendance.employee_id.name} في {now}.")

            # حساب مدة العمل
            duration = (attendance.check_out - attendance.check_in).total_seconds() / 3600.0
            hours = int(duration)
            minutes = int((duration - hours) * 60)
            duration_str = f"{hours}:{minutes:02d}"

            return {
                'success': True,
                'duration': duration_str,
            }
        except Exception as e:
            _logger.error(f"خطأ أثناء تسجيل انصراف الموظف: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
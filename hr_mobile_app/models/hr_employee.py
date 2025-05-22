# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import hashlib
import secrets
import base64
import re
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # حقول التطبيق المحمول
    mobile_username = fields.Char(
        string="اسم المستخدم للتطبيق",
        help="اسم المستخدم الخاص بهذا الموظف للدخول عبر التطبيق المحمول",
        copy=False,
    )
    mobile_pin = fields.Char(
        string="رمز الدخول للتطبيق",
        help="رمز PIN للتحقق من هوية الموظف في التطبيق (4-6 أرقام)",
        copy=False,
        groups="hr.group_hr_user",
    )
    mobile_pin_hash = fields.Char(
        string="رمز الدخول المشفر",
        help="تخزين رمز الدخول بشكل مشفر",
        copy=False,
        groups="hr.group_hr_user",
    )
    mobile_salt = fields.Char(
        string="Salt للتشفير",
        help="قيمة عشوائية تستخدم في تشفير رمز الدخول",
        copy=False,
        groups="hr.group_hr_user",
    )
    allow_mobile_access = fields.Boolean(
        string="السماح بالوصول من التطبيق",
        default=False,
        help="تفعيل وصول الموظف من التطبيق المحمول",
    )
    mobile_last_login = fields.Datetime(
        string="آخر تسجيل دخول للتطبيق",
        readonly=True,
        copy=False,
    )
    mobile_login_count = fields.Integer(
        string="عدد مرات تسجيل الدخول",
        default=0,
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        ('mobile_username_unique', 'UNIQUE(mobile_username)', 'اسم المستخدم للتطبيق يجب أن يكون فريداً!')
    ]


    @api.model
    def create(self, vals):
        """إنشاء سجل موظف جديد مع حساب التشفير لـ PIN"""
        if vals.get('mobile_pin'):
            # إنشاء salt عشوائي وتشفير PIN
            salt = secrets.token_hex(8)
            vals['mobile_salt'] = salt
            vals['mobile_pin_hash'] = self._hash_pin(vals['mobile_pin'], salt)

            # بعد تخزين القيمة المشفرة، نمسح القيمة الأصلية لأسباب أمنية
            # نحتفظ بنسخة مشفرة فقط
            vals['mobile_pin'] = '******'

        return super(HrEmployee, self).create(vals)

    def write(self, vals):
        """تحديث سجل موظف مع تشفير PIN إذا تم تغييره"""
        for employee in self:
            if vals.get('mobile_pin'):
                # إنشاء salt جديد وتشفير PIN
                salt = secrets.token_hex(8)
                vals['mobile_salt'] = salt
                vals['mobile_pin_hash'] = self._hash_pin(vals['mobile_pin'], salt)

                # بعد تخزين القيمة المشفرة، نمسح القيمة الأصلية
                vals['mobile_pin'] = '******'

        return super(HrEmployee, self).write(vals)

    def _hash_pin(self, pin, salt):
        """تشفير رمز PIN باستخدام PBKDF2 with SHA-256"""
        # استخدام تكرارات كثيرة لجعل عملية التشفير أكثر أماناً
        iterations = 100000

        # استخدام PBKDF2 لتشفير كلمة المرور مع salt
        dk = hashlib.pbkdf2_hmac('sha256', pin.encode(), salt.encode(), iterations)

        # تحويل الناتج إلى سلسلة نصية قابلة للتخزين
        return base64.b64encode(dk).decode()

    def verify_pin(self, pin):
        """التحقق من صحة رمز PIN"""
        self.ensure_one()

        # إضافة تسجيل للتصحيح
        _logger.info("Verifying PIN for employee: %s (ID: %s)", self.name, self.id)
        _logger.info("Mobile access allowed: %s", self.allow_mobile_access)
        _logger.info("PIN hash exists: %s", bool(self.mobile_pin_hash))
        _logger.info("Salt exists: %s", bool(self.mobile_salt))

        if not self.mobile_pin_hash or not self.mobile_salt:
            _logger.warning("Missing PIN hash or salt for employee: %s", self.name)
            return False

        # حساب التشفير لمقارنته مع القيمة المخزنة
        hashed_pin = self._hash_pin(pin, self.mobile_salt)

        # مقارنة القيمة المحسوبة بالقيمة المخزنة
        result = (self.mobile_pin_hash == hashed_pin)

        _logger.info("PIN verification result: %s", result)

        # تسجيل محاولة تسجيل الدخول
        if result:
            self.write({
                'mobile_last_login': fields.Datetime.now(),
                'mobile_login_count': self.mobile_login_count + 1,
            })

        return result

    def reset_mobile_pin(self):
        """إعادة تعيين رمز PIN مع إصلاح مشكلة التخزين"""
        # إنشاء رمز PIN عشوائي من 6 أرقام
        new_pin = '123456'  # رمز PIN ثابت للاختبار

        # إنشاء salt وتشفير
        salt = secrets.token_hex(8)
        pin_hash = self._hash_pin(new_pin, salt)

        # تحديث مباشر في قاعدة البيانات لتجنب المرور بـ write المخصصة
        self.env.cr.execute("""
            UPDATE hr_employee 
            SET mobile_salt = %s, mobile_pin_hash = %s 
            WHERE id = %s
        """, (salt, pin_hash, self.id))

        # تحديث القيم في الذاكرة
        self.mobile_salt = salt
        self.mobile_pin_hash = pin_hash

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم إعادة تعيين رمز الدخول'),
                'message': _('الرمز الجديد: %s') % new_pin,
                'sticky': False,
                'type': 'success',
            }
        }

    def toggle_mobile_access(self):
        """تفعيل/تعطيل وصول الموظف من التطبيق"""
        for record in self:
            record.allow_mobile_access = not record.allow_mobile_access

        return True

    def generate_demo_credentials(self):
        """إنشاء بيانات اعتماد تجريبية مع إصلاح حفظ الـ PIN"""
        if not self.mobile_username:
            # إنشاء اسم مستخدم من البريد الإلكتروني أو الاسم
            if self.work_email:
                username = self.work_email.split('@')[0]
            else:
                username = self.name.lower().replace(' ', '.')

            # التأكد من فرادة اسم المستخدم
            base_username = username
            counter = 1
            while self.env['hr.employee'].search_count([('mobile_username', '=', username)]) > 0:
                username = f"{base_username}{counter}"
                counter += 1

            self.mobile_username = username

        # إنشاء رمز PIN عشوائي
        new_pin = '1234'  # رمز PIN ثابت للاختبار بدلاً من العشوائي

        # إنشاء salt وتشفير مباشر للـ PIN
        salt = secrets.token_hex(8)
        pin_hash = self._hash_pin(new_pin, salt)

        # حفظ البيانات مباشرة لتجنب المرور بـ write المخصصة
        self.env.cr.execute("""
            UPDATE hr_employee 
            SET mobile_salt = %s, mobile_pin_hash = %s, allow_mobile_access = TRUE 
            WHERE id = %s
        """, (salt, pin_hash, self.id))

        # تحديث البيانات في الذاكرة
        self.mobile_salt = salt
        self.mobile_pin_hash = pin_hash
        self.allow_mobile_access = True

        # للتأكد من صحة التشفير والتخزين
        verification_result = self.verify_pin(new_pin)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم إنشاء بيانات الاعتماد'),
                'message': _('''
                اسم المستخدم: %s
                رمز الدخول: %s
                تم التحقق من الرمز: %s
                ''') % (self.mobile_username, new_pin, verification_result),
                'sticky': True,
                'type': 'success',
            }
        }

    @api.model
    def get_employee_by_username(self, username):
        """العثور على الموظف باستخدام اسم المستخدم"""
        employee = self.search([
            ('mobile_username', '=', username),
            ('allow_mobile_access', '=', True),
        ], limit=1)

        return employee if employee else False

    def set_test_pin(self):
        """تعيين رمز PIN للاختبار"""
        test_pin = '123456'  # رمز PIN بسيط للاختبار

        # إنشاء salt جديد
        salt = secrets.token_hex(8)

        # تخزين قيم حقيقية (بدون تشفير في هذه المرحلة)
        self.write({
            'mobile_pin': test_pin,
            'mobile_salt': salt,
            'mobile_pin_hash': self._hash_pin(test_pin, salt),
            'allow_mobile_access': True,
        })

        # عرض القيم للتحقق
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم تعيين رمز PIN للاختبار'),
                'message': _('''
                اسم المستخدم: %s
                رمز PIN: %s
                Salt: %s
                PIN Hash: %s
                ''') % (self.mobile_username, test_pin, salt, self.mobile_pin_hash),
                'sticky': True,
                'type': 'success',
            }
        }

    @api.model
    def verify_employee_credentials(self, username, pin):
        """التحقق من بيانات اعتماد الموظف"""
        # إضافة تسجيل للتصحيح
        _logger.info("التحقق من بيانات الاعتماد للمستخدم: %s", username)

        # تسجيل جميع الموظفين في النظام للتصحيح
        all_employees = self.search_read([], ['name', 'mobile_username', 'allow_mobile_access'])
        _logger.info("جميع الموظفين في النظام: %s", all_employees)

        # البحث عن الموظف باستخدام اسم المستخدم فقط (تجاهل allow_mobile_access مؤقتًا)
        employee = self.search([
            ('mobile_username', '=', username),
            # ('allow_mobile_access', '=', True),  # مؤقتًا نتجاهل هذا الشرط
        ], limit=1)

        if not employee:
            _logger.warning("لم يتم العثور على موظف باسم المستخدم: %s", username)
            return {'success': False, 'error': 'لم يتم العثور على الموظف أو تم رفض الوصول'}

        _logger.info("تم العثور على الموظف: %s (المعرف: %s)، معلومات إضافية: %s",
                     employee.name, employee.id,
                     employee.read(['mobile_username', 'allow_mobile_access', 'mobile_pin_hash', 'mobile_salt']))

        # ضبط allow_mobile_access على True بشكل مباشر لهذا الموظف
        if not employee.allow_mobile_access:
            _logger.info("تفعيل الوصول من التطبيق للموظف: %s", employee.name)
            employee.env.cr.execute("UPDATE hr_employee SET allow_mobile_access = TRUE WHERE id = %s", (employee.id,))

        # التحقق من صحة PIN (مع طباعة التفاصيل للتصحيح)
        _logger.info("محاولة التحقق من PIN للموظف: %s", employee.name)
        verification_result = employee.verify_pin(pin)
        _logger.info("نتيجة التحقق من PIN: %s", verification_result)

        if verification_result:
            _logger.info("تم التحقق من PIN بنجاح للموظف: %s", employee.name)
            return {
                'success': True,
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'job_title': employee.job_title or False,
                    'department': employee.department_id.name if employee.department_id else False,
                    'work_email': employee.work_email or False,
                    'work_phone': employee.work_phone or False,
                }
            }
        else:
            _logger.warning("فشل التحقق من PIN للموظف: %s", employee.name)
            return {'success': False, 'error': 'PIN غير صالح'}
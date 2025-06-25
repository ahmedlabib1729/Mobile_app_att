# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HrMobileAppSettings(models.TransientModel):
    _name = 'hr.mobile.app.settings'
    _description = 'إعدادات التطبيق المحمول للموظفين'

    name = fields.Char(default='إعدادات التطبيق المحمول')
    allow_mobile_app_access = fields.Boolean(
        string="تفعيل الوصول من التطبيق",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.allow_mobile_app_access',
                                                                              'False').lower() == 'true',
        help="تمكين الموظفين من استخدام التطبيق المحمول"
    )
    mobile_service_username = fields.Char(
        string="اسم مستخدم الخدمة",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.service_username',
                                                                              'mobile_app_service'),
        help="اسم المستخدم المشترك للاتصال بالخادم"
    )
    mobile_service_password = fields.Char(
        string="كلمة مرور الخدمة",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.service_password', ''),
        help="كلمة مرور المستخدم المشترك (يجب تغييرها بانتظام)"
    )
    api_base_url = fields.Char(
        string="عنوان خادم API",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.api_base_url', ''),
        help="عنوان URL الأساسي لخادم Odoo (مثال: https://your-odoo-server.com)"
    )
    api_database = fields.Char(
        string="اسم قاعدة البيانات",
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param('hr_mobile_app.api_database',
                                                                              self.env.cr.dbname),
        help="اسم قاعدة بيانات Odoo للاتصال بها"
    )

    def execute(self):
        """حفظ الإعدادات"""
        # التحقق من صحة الإدخال
        if self.mobile_service_password and len(self.mobile_service_password) < 3:
            raise ValidationError(_('يجب أن تتكون كلمة المرور من 8 أحرف على الأقل'))

        # حفظ الإعدادات في معلمات النظام
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('hr_mobile_app.allow_mobile_app_access', str(self.allow_mobile_app_access))
        params.set_param('hr_mobile_app.service_username', self.mobile_service_username or 'mobile_app_service')

        if self.mobile_service_password:
            params.set_param('hr_mobile_app.service_password', self.mobile_service_password)

        params.set_param('hr_mobile_app.api_base_url', self.api_base_url or '')
        params.set_param('hr_mobile_app.api_database', self.api_database or self.env.cr.dbname)

        # تحديث المستخدم المشترك إذا تم تغيير البيانات
        if self.mobile_service_username or self.mobile_service_password:
            service_user = self.env['res.users'].sudo().search([('login', '=', 'mobile_app_service')], limit=1)

            if service_user:
                # تحديث بيانات المستخدم الموجود
                update_vals = {}

                if self.mobile_service_username:
                    update_vals['login'] = self.mobile_service_username
                    update_vals['name'] = f"Mobile App Service ({self.mobile_service_username})"

                if self.mobile_service_password:
                    update_vals['password'] = self.mobile_service_password

                if update_vals:
                    service_user.write(update_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم الحفظ'),
                'message': _('تم حفظ إعدادات التطبيق المحمول بنجاح.'),
                'sticky': False,
                'type': 'success',
            }
        }
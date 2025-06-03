# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrOfficeLocation(models.Model):
    _name = 'hr.office.location'
    _description = 'مواقع مكاتب الشركة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'sequence, name'

    # الحقول الأساسية
    name = fields.Char(
        string='اسم الموقع',
        required=True,
        tracking=True,
        help="اسم واضح للموقع (مثل: المقر الرئيسي، فرع المعادي)"
    )

    code = fields.Char(
        string='رمز الموقع',
        help="رمز مختصر للموقع (مثل: HQ, BR1)"
    )

    active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True,
        help="إلغاء التفعيل بدلاً من الحذف"
    )

    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help="ترتيب العرض"
    )

    # إحداثيات الموقع
    latitude = fields.Float(
        string='خط العرض',
        digits=(10, 6),
        required=True,
        tracking=True,
        help="خط العرض (Latitude) للموقع"
    )

    longitude = fields.Float(
        string='خط الطول',
        digits=(10, 6),
        required=True,
        tracking=True,
        help="خط الطول (Longitude) للموقع"
    )

    # إعدادات النطاق
    allowed_radius = fields.Integer(
        string='النطاق المسموح (متر)',
        default=100,
        required=True,
        tracking=True,
        help="المسافة المسموحة من الموقع لتسجيل الحضور بالأمتار"
    )

    # معلومات العنوان
    street = fields.Char(
        string='الشارع',
        help="عنوان الشارع"
    )

    street2 = fields.Char(
        string='الشارع 2',
        help="عنوان إضافي"
    )

    city = fields.Char(
        string='المدينة',
        help="المدينة"
    )

    state_id = fields.Many2one(
        'res.country.state',
        string='المحافظة',
        help="المحافظة أو الولاية"
    )

    country_id = fields.Many2one(
        'res.country',
        string='الدولة',
        default=lambda self: self.env.ref('base.eg'),  # مصر كافتراضي
        help="الدولة"
    )

    zip = fields.Char(
        string='الرمز البريدي',
        help="الرمز البريدي"
    )

    # معلومات إضافية
    description = fields.Text(
        string='وصف',
        help="وصف تفصيلي للموقع"
    )

    location_type = fields.Selection([
        ('main', 'مقر رئيسي'),
        ('branch', 'فرع'),
        ('warehouse', 'مستودع'),
        ('site', 'موقع عمل'),
        ('client', 'موقع عميل'),
        ('other', 'أخرى')
    ], string='نوع الموقع', default='branch', tracking=True)

    # العلاقات
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company,
        help="الشركة التابع لها هذا الموقع"
    )

    department_ids = fields.One2many(
        'hr.department',
        'office_location_id',
        string='الأقسام',
        help="الأقسام التي تعمل من هذا الموقع"
    )

    employee_ids = fields.One2many(
        'hr.employee',
        'office_location_id',
        string='الموظفون',
        help="الموظفون المرتبطون بهذا الموقع"
    )

    # حقول محسوبة
    employee_count = fields.Integer(
        string='عدد الموظفين',
        compute='_compute_employee_count',
        store=True
    )

    department_count = fields.Integer(
        string='عدد الأقسام',
        compute='_compute_department_count',
        store=True
    )

    # خريطة Google
    google_maps_url = fields.Char(
        string='رابط خرائط Google',
        compute='_compute_google_maps_url',
        help="رابط لعرض الموقع على خرائط Google"
    )

    # إعدادات إضافية
    allow_flexible_radius = fields.Boolean(
        string='السماح بنطاق مرن',
        default=False,
        help="السماح بتسجيل الحضور من نطاق أوسع في أوقات معينة"
    )

    flexible_radius = fields.Integer(
        string='النطاق المرن (متر)',
        default=200,
        help="النطاق الأوسع المسموح به في الحالات الخاصة"
    )

    require_wifi = fields.Boolean(
        string='يتطلب اتصال WiFi',
        default=False,
        help="يتطلب الاتصال بشبكة WiFi المكتب لتسجيل الحضور"
    )

    wifi_name = fields.Char(
        string='اسم شبكة WiFi',
        help="اسم شبكة WiFi المطلوب الاتصال بها"
    )

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for location in self:
            location.employee_count = len(location.employee_ids)

    @api.depends('department_ids')
    def _compute_department_count(self):
        for location in self:
            location.department_count = len(location.department_ids)

    @api.depends('latitude', 'longitude')
    def _compute_google_maps_url(self):
        for location in self:
            if location.latitude and location.longitude:
                location.google_maps_url = f"https://www.google.com/maps?q={location.latitude},{location.longitude}"
            else:
                location.google_maps_url = False

    @api.constrains('latitude')
    def _check_latitude(self):
        for location in self:
            if location.latitude < -90 or location.latitude > 90:
                raise ValidationError(_('خط العرض يجب أن يكون بين -90 و 90'))

    @api.constrains('longitude')
    def _check_longitude(self):
        for location in self:
            if location.longitude < -180 or location.longitude > 180:
                raise ValidationError(_('خط الطول يجب أن يكون بين -180 و 180'))

    @api.constrains('allowed_radius', 'flexible_radius')
    def _check_radius(self):
        for location in self:
            if location.allowed_radius <= 0:
                raise ValidationError(_('النطاق المسموح يجب أن يكون أكبر من صفر'))
            if location.flexible_radius <= 0:
                raise ValidationError(_('النطاق المرن يجب أن يكون أكبر من صفر'))
            if location.flexible_radius < location.allowed_radius:
                raise ValidationError(_('النطاق المرن يجب أن يكون أكبر من أو يساوي النطاق المسموح'))

    def action_view_employees(self):
        """عرض الموظفين المرتبطين بهذا الموقع"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('موظفو %s') % self.name,
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'domain': [('office_location_id', '=', self.id)],
            'context': {'default_office_location_id': self.id}
        }

    def action_view_departments(self):
        """عرض الأقسام المرتبطة بهذا الموقع"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('أقسام %s') % self.name,
            'res_model': 'hr.department',
            'view_mode': 'list,form',
            'domain': [('office_location_id', '=', self.id)],
            'context': {'default_office_location_id': self.id}
        }

    def action_open_map(self):
        """فتح الموقع على خرائط Google"""
        self.ensure_one()
        if self.google_maps_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.google_maps_url,
                'target': 'new',
            }

    @api.model
    def get_nearest_location(self, latitude, longitude):
        """الحصول على أقرب موقع مكتب من إحداثيات معينة"""
        locations = self.search([('active', '=', True)])

        if not locations:
            return False

        nearest_location = None
        min_distance = float('inf')

        for location in locations:
            # حساب المسافة باستخدام دالة من hr.attendance
            attendance_model = self.env['hr.attendance']
            distance = attendance_model._calculate_distance(
                latitude, longitude,
                location.latitude, location.longitude
            )

            if distance < min_distance:
                min_distance = distance
                nearest_location = location

        return {
            'location': nearest_location,
            'distance': min_distance
        }

    def name_get(self):
        """تخصيص عرض الاسم"""
        result = []
        for location in self:
            if location.code:
                name = f"[{location.code}] {location.name}"
            else:
                name = location.name
            result.append((location.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """البحث بالاسم أو الرمز"""
        if args is None:
            args = []

        if name:
            args = ['|', ('name', operator, name), ('code', operator, name)] + args

        return self.search(args, limit=limit).name_get()


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    office_location_id = fields.Many2one(
        'hr.office.location',
        string='موقع المكتب',
        help="الموقع الجغرافي لهذا القسم"
    )


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    office_location_id = fields.Many2one(
        'hr.office.location',
        string='موقع المكتب',
        help="الموقع الجغرافي المخصص لهذا الموظف",
        tracking=True
    )

    allow_remote_attendance = fields.Boolean(
        string='السماح بالحضور عن بُعد',
        default=False,
        help="السماح لهذا الموظف بتسجيل الحضور من أي مكان",
        tracking=True
    )

    temporary_location_ids = fields.One2many(
        'hr.employee.temp.location',
        'employee_id',
        string='المواقع المؤقتة',
        help="مواقع مؤقتة مسموح للموظف بالحضور منها"
    )

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """تحديث موقع المكتب عند تغيير القسم"""
        if self.department_id and self.department_id.office_location_id:
            self.office_location_id = self.department_id.office_location_id


class HrEmployeeTempLocation(models.Model):
    _name = 'hr.employee.temp.location'
    _description = 'مواقع مؤقتة للموظف'
    _rec_name = 'reason'

    employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف',
        required=True,
        ondelete='cascade'
    )

    date_from = fields.Date(
        string='من تاريخ',
        required=True,
        default=fields.Date.today
    )

    date_to = fields.Date(
        string='إلى تاريخ',
        required=True
    )

    latitude = fields.Float(
        string='خط العرض',
        digits=(10, 6),
        required=True
    )

    longitude = fields.Float(
        string='خط الطول',
        digits=(10, 6),
        required=True
    )

    allowed_radius = fields.Integer(
        string='النطاق المسموح (متر)',
        default=100,
        required=True
    )

    reason = fields.Text(
        string='السبب',
        required=True,
        help="سبب السماح بالحضور من هذا الموقع"
    )

    approved_by = fields.Many2one(
        'res.users',
        string='تمت الموافقة بواسطة',
        readonly=True
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(_('تاريخ البداية يجب أن يكون قبل تاريخ النهاية'))



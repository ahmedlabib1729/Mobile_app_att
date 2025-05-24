# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class HrAnnouncement(models.Model):
    _name = 'hr.announcement'
    _description = 'إعلانات الموظفين'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'is_pinned desc, priority desc, create_date desc'

    # الحقول الأساسية
    name = fields.Char(
        string='عنوان الإعلان',
        required=True,
        tracking=True,
        help="عنوان واضح ومختصر للإعلان"
    )

    content = fields.Html(
        string='محتوى الإعلان',
        required=True,
        sanitize_style=True,
        help="المحتوى التفصيلي للإعلان"
    )

    summary = fields.Text(
        string='ملخص',
        help="ملخص قصير يظهر في قائمة الإعلانات"
    )

    # التصنيف والنوع
    announcement_type = fields.Selection([
        ('general', 'إعلان عام'),
        ('department', 'حسب القسم'),
        ('job', 'حسب الوظيفة'),
        ('personal', 'شخصي'),
        ('urgent', 'عاجل'),
    ], string='نوع الإعلان', default='general', required=True, tracking=True)

    priority = fields.Selection([
        ('low', 'منخفضة'),
        ('normal', 'عادية'),
        ('high', 'مرتفعة'),
        ('urgent', 'عاجلة جداً'),
    ], string='الأولوية', default='normal', tracking=True)

    # التواريخ
    start_date = fields.Datetime(
        string='تاريخ البداية',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
        help="تاريخ ووقت بداية عرض الإعلان"
    )

    end_date = fields.Datetime(
        string='تاريخ النهاية',
        tracking=True,
        help="تاريخ ووقت انتهاء عرض الإعلان (اختياري)"
    )

    # الاستهداف
    department_ids = fields.Many2many(
        'hr.department',
        string='الأقسام المستهدفة',
        help="اترك فارغاً لاستهداف جميع الأقسام"
    )

    job_ids = fields.Many2many(
        'hr.job',
        string='الوظائف المستهدفة',
        help="اترك فارغاً لاستهداف جميع الوظائف"
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='موظفون محددون',
        help="حدد موظفين معينين لاستلام الإعلان"
    )

    # خيارات العرض
    is_pinned = fields.Boolean(
        string='تثبيت الإعلان',
        default=False,
        tracking=True,
        help="الإعلانات المثبتة تظهر في أعلى القائمة"
    )

    show_in_mobile = fields.Boolean(
        string='عرض في التطبيق المحمول',
        default=True,
        help="عرض هذا الإعلان في التطبيق المحمول"
    )

    # المرفقات
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='المرفقات',
        help="أضف ملفات أو صور مرفقة"
    )

    # معلومات النشر
    author_id = fields.Many2one(
        'res.users',
        string='الناشر',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('published', 'منشور'),
        ('scheduled', 'مجدول'),
        ('expired', 'منتهي'),
        ('archived', 'مؤرشف'),
    ], string='الحالة', default='draft', tracking=True)

    # الإحصائيات
    read_count = fields.Integer(
        string='عدد القراءات',
        compute='_compute_read_count',
        store=True
    )

    read_employee_ids = fields.Many2many(
        'hr.employee',
        'hr_announcement_read_rel',
        'announcement_id',
        'employee_id',
        string='الموظفون الذين قرأوا الإعلان'
    )

    # حقول محسوبة
    is_expired = fields.Boolean(
        string='منتهي الصلاحية',
        compute='_compute_is_expired',
        store=True
    )

    target_employee_count = fields.Integer(
        string='عدد الموظفين المستهدفين',
        compute='_compute_target_employee_count',
        store=True
    )

    read_percentage = fields.Float(
        string='نسبة القراءة',
        compute='_compute_read_percentage',
        store=True
    )

    @api.depends('read_employee_ids')
    def _compute_read_count(self):
        for record in self:
            record.read_count = len(record.read_employee_ids)

    @api.depends('end_date')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            if record.end_date:
                record.is_expired = record.end_date < now
            else:
                record.is_expired = False

    @api.depends('announcement_type', 'department_ids', 'job_ids', 'employee_ids')
    def _compute_target_employee_count(self):
        for record in self:
            if record.announcement_type == 'personal':
                record.target_employee_count = len(record.employee_ids)
            elif record.announcement_type == 'department':
                employees = self.env['hr.employee'].search([
                    ('department_id', 'in', record.department_ids.ids)
                ])
                record.target_employee_count = len(employees)
            elif record.announcement_type == 'job':
                employees = self.env['hr.employee'].search([
                    ('job_id', 'in', record.job_ids.ids)
                ])
                record.target_employee_count = len(employees)
            else:  # general or urgent
                record.target_employee_count = self.env['hr.employee'].search_count([])

    @api.depends('read_count', 'target_employee_count')
    def _compute_read_percentage(self):
        for record in self:
            if record.target_employee_count > 0:
                record.read_percentage = (record.read_count / record.target_employee_count) * 100
            else:
                record.read_percentage = 0

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.end_date and record.start_date > record.end_date:
                raise ValidationError(_('تاريخ البداية يجب أن يكون قبل تاريخ النهاية'))

    def action_publish(self):
        """نشر الإعلان"""
        self.ensure_one()
        if not self.content:
            raise ValidationError(_('يجب إضافة محتوى للإعلان قبل النشر'))

        now = fields.Datetime.now()
        if self.start_date > now:
            self.state = 'scheduled'
        else:
            self.state = 'published'

        # إرسال إشعار للموظفين المستهدفين
        self._send_notification_to_employees()

    def action_draft(self):
        """إرجاع إلى مسودة"""
        self.state = 'draft'

    def action_archive(self):
        """أرشفة الإعلان"""
        self.state = 'archived'

    def action_mark_as_read(self, employee_id=None):
        """تسجيل قراءة الإعلان"""
        if not employee_id:
            employee = self.env.user.employee_id
        else:
            employee = self.env['hr.employee'].browse(employee_id)

        if employee and employee not in self.read_employee_ids:
            self.read_employee_ids = [(4, employee.id)]
            _logger.info(f"الموظف {employee.name} قرأ الإعلان {self.name}")

    def _send_notification_to_employees(self):
        """إرسال إشعار للموظفين المستهدفين"""
        employees = self._get_target_employees()

        # هنا يمكن إضافة منطق إرسال الإشعارات
        # مثل البريد الإلكتروني أو الإشعارات الداخلية
        _logger.info(f"تم إرسال إشعار بالإعلان {self.name} إلى {len(employees)} موظف")

    def _get_target_employees(self):
        """الحصول على قائمة الموظفين المستهدفين"""
        if self.announcement_type == 'personal':
            return self.employee_ids
        elif self.announcement_type == 'department':
            return self.env['hr.employee'].search([
                ('department_id', 'in', self.department_ids.ids)
            ])
        elif self.announcement_type == 'job':
            return self.env['hr.employee'].search([
                ('job_id', 'in', self.job_ids.ids)
            ])
        else:  # general or urgent
            return self.env['hr.employee'].search([])

    @api.model
    def check_scheduled_announcements(self):
        """Cron job للتحقق من الإعلانات المجدولة"""
        now = fields.Datetime.now()

        # نشر الإعلانات المجدولة
        scheduled = self.search([
            ('state', '=', 'scheduled'),
            ('start_date', '<=', now)
        ])
        scheduled.write({'state': 'published'})

        # إنهاء الإعلانات المنتهية
        expired = self.search([
            ('state', '=', 'published'),
            ('end_date', '<', now),
            ('end_date', '!=', False)
        ])
        expired.write({'state': 'expired'})

    def get_announcement_preview(self):
        """عرض معاينة الإعلان"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web#id={self.id}&model=hr.announcement&view_type=form',
            'target': 'new',
        }


class HrAnnouncementRead(models.Model):
    _name = 'hr.announcement.read'
    _description = 'سجل قراءة الإعلانات'
    _rec_name = 'announcement_id'

    announcement_id = fields.Many2one(
        'hr.announcement',
        string='الإعلان',
        required=True,
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف',
        required=True,
        ondelete='cascade'
    )

    read_date = fields.Datetime(
        string='تاريخ القراءة',
        default=fields.Datetime.now,
        required=True
    )

    _sql_constraints = [
        ('unique_read', 'UNIQUE(announcement_id, employee_id)',
         'الموظف قرأ هذا الإعلان بالفعل!')
    ]
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
import calendar

_logger = logging.getLogger(__name__)


class TaxClient(models.Model):
    _name = 'tax.client'
    _description = 'عميل ضريبي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='اسم العميل', required=True, tracking=True)
    email = fields.Char(string='البريد الإلكتروني', required=True, tracking=True)
    phone = fields.Char(string='رقم الهاتف', tracking=True)
    tax_number = fields.Char(string='الرقم الضريبي', tracking=True)
    activity_type = fields.Selection([
        ('trading', 'تجاري'),
        ('industrial', 'صناعي'),
        ('service', 'خدمي'),
        ('professional', 'مهني'),
        ('other', 'أخرى')
    ], string='نوع النشاط', default='trading')

    # العلاقة مع الإقرارات
    declaration_ids = fields.One2many('tax.declaration', 'client_id', string='الإقرارات الضريبية')
    declaration_count = fields.Integer(string='عدد الإقرارات', compute='_compute_declaration_count')

    lang = fields.Selection(
        string='اللغة',
        selection='_get_lang_selection',
        default=lambda self: self.env.lang,
        help="لغة المراسلات مع العميل"
    )
    # إعدادات الإقرارات المتكررة
    tax_setting_ids = fields.One2many('tax.client.settings', 'client_id', string='إعدادات الضرائب')
    auto_generate = fields.Boolean(string='توليد تلقائي للإقرارات', default=True)

    active = fields.Boolean(string='نشط', default=True)
    notes = fields.Text(string='ملاحظات')

    @api.model
    def _get_lang_selection(self):
        """الحصول على قائمة اللغات المتاحة"""
        return self.env['res.lang'].get_installed()

    @api.depends('declaration_ids')
    def _compute_declaration_count(self):
        for record in self:
            record.declaration_count = len(record.declaration_ids)

    def action_view_declarations(self):
        """فتح نافذة الإقرارات الخاصة بالعميل"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'الإقرارات الضريبية',
            'view_mode': 'list,form',
            'res_model': 'tax.declaration',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id}
        }

    def generate_upcoming_declarations(self):
        """توليد الإقرارات القادمة بناءً على الإعدادات"""
        for client in self:
            if not client.auto_generate:
                continue

            for setting in client.tax_setting_ids:
                if not setting.active:
                    continue

                setting.generate_next_declarations()


class TaxDeclaration(models.Model):
    _name = 'tax.declaration'
    _description = 'إقرار ضريبي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'due_date desc'

    name = fields.Char(string='المرجع', required=True, readonly=True, default='New')
    client_id = fields.Many2one('tax.client', string='العميل', required=True, tracking=True)

    tax_type = fields.Selection([
        ('vat', 'ضريبة القيمة المضافة'),
        ('income', 'ضريبة الدخل'),
        ('withholding', 'خصم وإضافة'),
        ('payroll', 'ضريبة المرتبات'),
        ('other', 'أخرى')
    ], string='نوع الضريبة', required=True, tracking=True)

    period_type = fields.Selection([
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي')
    ], string='نوع الفترة', required=True, default='quarterly')

    period = fields.Selection([
        ('1', 'الفترة الأولى'),
        ('2', 'الفترة الثانية'),
        ('3', 'الفترة الثالثة'),
        ('4', 'الفترة الرابعة'),
        ('5', 'الفترة الخامسة'),
        ('6', 'الفترة السادسة'),
        ('7', 'الفترة السابعة'),
        ('8', 'الفترة الثامنة'),
        ('9', 'الفترة التاسعة'),
        ('10', 'الفترة العاشرة'),
        ('11', 'الفترة الحادية عشر'),
        ('12', 'الفترة الثانية عشر'),
    ], string='الفترة', required=True)

    year = fields.Integer(string='السنة', required=True, default=lambda self: fields.Date.today().year)
    due_date = fields.Date(string='تاريخ الاستحقاق', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('waiting', 'في الانتظار'),
        ('reminded', 'تم التذكير'),
        ('documents_received', 'تم استلام المستندات'),
        ('submitted', 'تم التقديم'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    # التذكيرات
    reminder_sent = fields.Boolean(string='تم إرسال التذكير', default=False)
    reminder_sent_date = fields.Datetime(string='تاريخ إرسال التذكير')
    days_before_reminder = fields.Integer(string='أيام قبل التذكير', default=7)

    # المستندات
    attachment_ids = fields.Many2many('ir.attachment', string='المستندات المرفقة')
    attachment_count = fields.Integer(string='عدد المستندات', compute='_compute_attachment_count')

    # معلومات إضافية
    notes = fields.Text(string='ملاحظات')
    submission_date = fields.Date(string='تاريخ التقديم الفعلي')

    # حقول محسوبة للعرض
    tax_type_display = fields.Char(string='نوع الضريبة', compute='_compute_display_fields', store=False)
    period_display = fields.Char(string='الفترة', compute='_compute_display_fields', store=False)
    days_remaining = fields.Integer(string='الأيام المتبقية', compute='_compute_days_remaining', store=False)

    @api.depends('tax_type', 'period_type', 'period', 'year')
    def _compute_display_fields(self):
        tax_types = {
            'vat': 'ضريبة القيمة المضافة',
            'income': 'ضريبة الدخل',
            'withholding': 'الخصم والإضافة',
            'payroll': 'ضريبة المرتبات',
            'other': 'أخرى'
        }

        months = ['', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']

        for record in self:
            # نوع الضريبة
            record.tax_type_display = tax_types.get(record.tax_type, record.tax_type or '')

            # الفترة
            if record.period_type == 'quarterly':
                record.period_display = f"الربع {record.period} لسنة {record.year}"
            elif record.period_type == 'monthly' and record.period:
                try:
                    month_idx = int(record.period)
                    if 1 <= month_idx <= 12:
                        record.period_display = f"{months[month_idx]} {record.year}"
                    else:
                        record.period_display = f"شهر {record.period} - {record.year}"
                except:
                    record.period_display = f"شهر {record.period} - {record.year}"
            elif record.period_type == 'semi_annual':
                half = 'الأول' if record.period == '1' else 'الثاني'
                record.period_display = f"النصف {half} لسنة {record.year}"
            elif record.period_type == 'annual':
                record.period_display = f"السنة المالية {record.year}"
            else:
                record.period_display = f"الفترة {record.period} - {record.year}"

    @api.depends('due_date')
    def _compute_days_remaining(self):
        today = fields.Date.today()
        for record in self:
            if record.due_date:
                record.days_remaining = (record.due_date - today).days
            else:
                record.days_remaining = 0

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.model
    def create(self, vals):
        """إنشاء مرجع تلقائي عند إنشاء إقرار جديد"""
        if vals.get('name', 'New') == 'New':
            # تكوين المرجع: TAX/السنة/الرقم التسلسلي
            year = vals.get('year', fields.Date.today().year)
            sequence = self.env['ir.sequence'].next_by_code('tax.declaration.sequence')
            if not sequence:
                # إنشاء تسلسل إذا لم يكن موجود
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': 'Tax Declaration Sequence',
                    'code': 'tax.declaration.sequence',
                    'prefix': 'TAX/',
                    'padding': 4
                }).next_by_code('tax.declaration.sequence')
            vals['name'] = f"TAX/{year}/{sequence}"
        return super(TaxDeclaration, self).create(vals)

    def action_send_reminder(self):
        """إرسال تذكير يدوي للعميل"""
        self.ensure_one()

        # البحث عن القالب
        template_id = self.env.ref('tax_reminder.email_template_tax_reminder', raise_if_not_found=False)

        if not template_id:
            # إذا لم يجد القالب، نبحث عنه بطريقة أخرى
            template_id = self.env['mail.template'].search([
                ('name', '=', 'تذكير بالإقرار الضريبي'),
                ('model_id.model', '=', 'tax.declaration')
            ], limit=1)

        if template_id:
            try:
                # إرسال البريد
                template_id.send_mail(self.id, force_send=True)

                # تحديث الحالة
                self.write({
                    'reminder_sent': True,
                    'reminder_sent_date': fields.Datetime.now(),
                    'state': 'reminded' if self.state in ['draft', 'waiting'] else self.state
                })

                # إضافة رسالة في الشات
                self.message_post(
                    body=f"تم إرسال تذكير بالبريد الإلكتروني إلى {self.client_id.name} على {self.client_id.email}",
                    subject="تذكير بالإقرار الضريبي"
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'تم إرسال التذكير بنجاح',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as e:
                _logger.error(f"خطأ في إرسال البريد: {str(e)}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'حدث خطأ في إرسال البريد: {str(e)}',
                        'type': 'danger',
                        'sticky': True,
                    }
                }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'لم يتم العثور على قالب البريد الإلكتروني',
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def action_mark_submitted(self):
        """تحديد الإقرار كمقدم"""
        self.ensure_one()
        self.write({
            'state': 'submitted',
            'submission_date': fields.Date.today()
        })
        self.message_post(body="تم تقديم الإقرار الضريبي بنجاح")
        return True

    def action_cancel(self):
        """إلغاء الإقرار"""
        self.ensure_one()
        self.write({'state': 'cancelled'})
        self.message_post(body="تم إلغاء الإقرار الضريبي")
        return True

    def action_reset_draft(self):
        """إرجاع الإقرار إلى مسودة"""
        self.ensure_one()
        self.write({'state': 'draft'})
        return True

    def action_view_attachments(self):
        """عرض المستندات المرفقة"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'المستندات المرفقة',
            'view_mode': 'kanban,form',
            'res_model': 'ir.attachment',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {
                'default_res_model': 'tax.declaration',
                'default_res_id': self.id,
            }
        }

    @api.model
    def check_and_send_reminders(self):
        """دالة تعمل يومياً للتحقق من الإقرارات وإرسال التذكيرات"""
        today = fields.Date.today()

        # البحث عن الإقرارات التي تحتاج تذكير
        declarations = self.search([
            ('state', 'in', ['draft', 'waiting']),
            ('reminder_sent', '=', False),
            ('due_date', '!=', False)
        ])

        for declaration in declarations:
            # حساب الأيام المتبقية
            days_remaining = (declaration.due_date - today).days

            # إذا كانت الأيام المتبقية = أيام التذكير المحددة
            if days_remaining == declaration.days_before_reminder:
                declaration.action_send_reminder()
                _logger.info(f"تم إرسال تذكير للإقرار: {declaration.name}")

        return True

    def get_period_display(self):
        """الحصول على اسم الفترة بشكل واضح"""
        self.ensure_one()
        if self.period_type == 'quarterly':
            return f"الربع {self.period} - {self.year}"
        elif self.period_type == 'monthly':
            months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                      'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
            month_idx = int(self.period) - 1
            return f"{months[month_idx]} {self.year}"
        elif self.period_type == 'semi_annual':
            half = 'الأول' if self.period == '1' else 'الثاني'
            return f"النصف {half} - {self.year}"
        elif self.period_type == 'annual':
            return f"السنة المالية {self.year}"
        else:
            return f"الفترة {self.period} - {self.year}"

    def get_tax_type_display(self):
        """الحصول على اسم نوع الضريبة بالعربي"""
        self.ensure_one()
        tax_types = {
            'vat': 'ضريبة القيمة المضافة',
            'income': 'ضريبة الدخل',
            'withholding': 'الخصم والإضافة',
            'payroll': 'ضريبة المرتبات',
            'other': 'أخرى'
        }
        return tax_types.get(self.tax_type, self.tax_type)


class TaxClientSettings(models.Model):
    """إعدادات الضرائب المتكررة لكل عميل"""
    _name = 'tax.client.settings'
    _description = 'إعدادات ضرائب العميل'
    _rec_name = 'tax_type'

    client_id = fields.Many2one('tax.client', string='العميل', required=True, ondelete='cascade')
    tax_type = fields.Selection([
        ('vat', 'ضريبة القيمة المضافة'),
        ('income', 'ضريبة الدخل'),
        ('withholding', 'خصم وإضافة'),
        ('payroll', 'ضريبة المرتبات'),
        ('other', 'أخرى')
    ], string='نوع الضريبة', required=True)

    period_type = fields.Selection([
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي')
    ], string='دورية التقديم', required=True, default='quarterly')

    # مواعيد الاستحقاق
    day_of_month = fields.Integer(string='يوم الاستحقاق من الشهر', default=15,
                                  help='اليوم من الشهر الذي يستحق فيه الإقرار')
    months_after_period = fields.Integer(string='شهور بعد انتهاء الفترة', default=1,
                                         help='عدد الشهور بعد انتهاء الفترة لموعد الاستحقاق')

    # التذكير
    days_before_reminder = fields.Integer(string='أيام التذكير قبل الاستحقاق', default=7)

    # عدد الفترات للتوليد
    periods_to_generate = fields.Integer(string='عدد الفترات للتوليد', default=4,
                                         help='عدد الفترات المطلوب توليدها مسبقاً (مثلاً: 12 شهر، 4 أرباع، إلخ)')
    generation_type = fields.Selection([
        ('periods', 'عدد ثابت من الفترات'),
        ('months', 'لعدد شهور قادمة'),
        ('years', 'لعدد سنوات قادمة')
    ], string='نوع التوليد', default='periods',
        help='طريقة حساب الفترات المطلوب توليدها')
    generation_months = fields.Integer(string='شهور التوليد المسبق', default=6,
                                       help='توليد الإقرارات للشهور القادمة')
    generation_years = fields.Integer(string='سنوات التوليد المسبق', default=1,
                                      help='توليد الإقرارات للسنوات القادمة')

    # التحكم
    active = fields.Boolean(string='نشط', default=True)
    last_generated_year = fields.Integer(string='آخر سنة تم توليدها')
    last_generated_period = fields.Char(string='آخر فترة تم توليدها')

    @api.model
    def get_due_date(self, year, period):
        """حساب تاريخ الاستحقاق بناءً على الإعدادات"""
        if self.period_type == 'monthly':
            # الشهر التالي للفترة
            month = int(period) + self.months_after_period
            if month > 12:
                year += month // 12
                month = month % 12
            if month == 0:
                month = 12
                year -= 1

            # محاولة إنشاء التاريخ مع معالجة الأيام غير الموجودة
            try:
                due_date = datetime(year, month, self.day_of_month).date()
            except ValueError:
                # إذا كان اليوم غير موجود (مثل 31 فبراير)، استخدم آخر يوم في الشهر
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                due_date = datetime(year, month, min(self.day_of_month, last_day)).date()

        elif self.period_type == 'quarterly':
            # حساب الشهر الأول بعد انتهاء الربع
            quarter = int(period)
            end_month = quarter * 3  # الشهر الأخير في الربع
            month = end_month + self.months_after_period

            if month > 12:
                year += month // 12
                month = month % 12
            if month == 0:
                month = 12
                year -= 1

            try:
                due_date = datetime(year, month, self.day_of_month).date()
            except ValueError:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                due_date = datetime(year, month, min(self.day_of_month, last_day)).date()

        elif self.period_type == 'annual':
            # السنة التالية
            year = year + 1
            month = self.months_after_period
            try:
                due_date = datetime(year, month, self.day_of_month).date()
            except ValueError:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                due_date = datetime(year, month, min(self.day_of_month, last_day)).date()
        else:
            # semi_annual
            period_int = int(period)
            if period_int == 1:
                month = 6 + self.months_after_period
            else:
                month = 12 + self.months_after_period

            if month > 12:
                year += 1
                month = month - 12

            try:
                due_date = datetime(year, month, self.day_of_month).date()
            except ValueError:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                due_date = datetime(year, month, min(self.day_of_month, last_day)).date()

        return due_date

    def generate_next_declarations(self, force_regenerate=False):
        """توليد الإقرارات للفترات القادمة بناءً على الإعدادات"""
        self.ensure_one()

        today = fields.Date.today()
        current_year = today.year
        current_month = today.month

        declarations_to_create = []

        # تحديد عدد الفترات المطلوب توليدها
        if self.generation_type == 'months':
            # حساب عدد الفترات بناءً على الشهور
            if self.period_type == 'monthly':
                periods_count = self.generation_months
            elif self.period_type == 'quarterly':
                periods_count = (self.generation_months // 3) + (1 if self.generation_months % 3 else 0)
            elif self.period_type == 'semi_annual':
                periods_count = (self.generation_months // 6) + (1 if self.generation_months % 6 else 0)
            else:  # annual
                periods_count = (self.generation_months // 12) + (1 if self.generation_months % 12 else 0)
        elif self.generation_type == 'years':
            # حساب عدد الفترات بناءً على السنوات
            if self.period_type == 'monthly':
                periods_count = self.generation_years * 12
            elif self.period_type == 'quarterly':
                periods_count = self.generation_years * 4
            elif self.period_type == 'semi_annual':
                periods_count = self.generation_years * 2
            else:  # annual
                periods_count = self.generation_years
        else:  # periods
            periods_count = self.periods_to_generate

        if self.period_type == 'monthly':
            # توليد الإقرارات الشهرية
            for i in range(periods_count):
                month = current_month + i
                year = current_year

                # معالجة تجاوز الشهور
                while month > 12:
                    year += 1
                    month -= 12

                period = str(month)

                # التحقق من عدم وجود إقرار مسبق
                existing = self.env['tax.declaration'].search([
                    ('client_id', '=', self.client_id.id),
                    ('tax_type', '=', self.tax_type),
                    ('period', '=', period),
                    ('year', '=', year),
                    ('state', '!=', 'cancelled')
                ], limit=1)

                if not existing or force_regenerate:
                    due_date = self.get_due_date(year, period)

                    if force_regenerate and existing:
                        # تحديث الإقرار الموجود إذا كان في حالة draft أو waiting
                        if existing.state in ['draft', 'waiting']:
                            existing.write({
                                'due_date': due_date,
                                'days_before_reminder': self.days_before_reminder,
                            })
                    else:
                        declarations_to_create.append({
                            'client_id': self.client_id.id,
                            'tax_type': self.tax_type,
                            'period_type': self.period_type,
                            'period': period,
                            'year': year,
                            'due_date': due_date,
                            'days_before_reminder': self.days_before_reminder,
                            'state': 'waiting'
                        })

        elif self.period_type == 'quarterly':
            # توليد الإقرارات الربعية
            current_quarter = (current_month - 1) // 3 + 1

            for i in range(periods_count):
                quarter = current_quarter + i
                year = current_year

                # معالجة تجاوز الأرباع
                while quarter > 4:
                    year += 1
                    quarter -= 4

                period = str(quarter)

                # التحقق من عدم وجود إقرار مسبق
                existing = self.env['tax.declaration'].search([
                    ('client_id', '=', self.client_id.id),
                    ('tax_type', '=', self.tax_type),
                    ('period', '=', period),
                    ('year', '=', year),
                    ('state', '!=', 'cancelled')
                ], limit=1)

                if not existing or force_regenerate:
                    due_date = self.get_due_date(year, period)

                    if force_regenerate and existing:
                        if existing.state in ['draft', 'waiting']:
                            existing.write({
                                'due_date': due_date,
                                'days_before_reminder': self.days_before_reminder,
                            })
                    else:
                        declarations_to_create.append({
                            'client_id': self.client_id.id,
                            'tax_type': self.tax_type,
                            'period_type': self.period_type,
                            'period': period,
                            'year': year,
                            'due_date': due_date,
                            'days_before_reminder': self.days_before_reminder,
                            'state': 'waiting'
                        })

        elif self.period_type == 'semi_annual':
            # توليد الإقرارات النصف سنوية
            current_half = 1 if current_month <= 6 else 2

            for i in range(periods_count):
                half = current_half + i
                year = current_year

                # معالجة تجاوز الفترات
                while half > 2:
                    year += 1
                    half -= 2

                period = str(half)

                # التحقق من عدم وجود إقرار مسبق
                existing = self.env['tax.declaration'].search([
                    ('client_id', '=', self.client_id.id),
                    ('tax_type', '=', self.tax_type),
                    ('period', '=', period),
                    ('year', '=', year),
                    ('state', '!=', 'cancelled')
                ], limit=1)

                if not existing or force_regenerate:
                    due_date = self.get_due_date(year, period)

                    if force_regenerate and existing:
                        if existing.state in ['draft', 'waiting']:
                            existing.write({
                                'due_date': due_date,
                                'days_before_reminder': self.days_before_reminder,
                            })
                    else:
                        declarations_to_create.append({
                            'client_id': self.client_id.id,
                            'tax_type': self.tax_type,
                            'period_type': self.period_type,
                            'period': period,
                            'year': year,
                            'due_date': due_date,
                            'days_before_reminder': self.days_before_reminder,
                            'state': 'waiting'
                        })

        elif self.period_type == 'annual':
            # توليد الإقرارات السنوية
            for i in range(periods_count):
                year = current_year + i
                period = '1'

                existing = self.env['tax.declaration'].search([
                    ('client_id', '=', self.client_id.id),
                    ('tax_type', '=', self.tax_type),
                    ('period', '=', period),
                    ('year', '=', year),
                    ('state', '!=', 'cancelled')
                ], limit=1)

                if not existing or force_regenerate:
                    due_date = self.get_due_date(year, period)

                    if force_regenerate and existing:
                        if existing.state in ['draft', 'waiting']:
                            existing.write({
                                'due_date': due_date,
                                'days_before_reminder': self.days_before_reminder,
                            })
                    else:
                        declarations_to_create.append({
                            'client_id': self.client_id.id,
                            'tax_type': self.tax_type,
                            'period_type': self.period_type,
                            'period': period,
                            'year': year,
                            'due_date': due_date,
                            'days_before_reminder': self.days_before_reminder,
                            'state': 'waiting'
                        })

        # إنشاء الإقرارات الجديدة
        created_count = 0
        if declarations_to_create:
            created = self.env['tax.declaration'].create(declarations_to_create)
            created_count = len(created)

            # تحديث آخر فترة تم توليدها
            if created:
                last_dec = declarations_to_create[-1]
                self.write({
                    'last_generated_year': last_dec['year'],
                    'last_generated_period': last_dec['period']
                })

        # إضافة رسالة في سجل العميل
        if created_count > 0:
            self.client_id.message_post(
                body=f"تم توليد {created_count} إقرار ضريبي جديد لنوع {dict(self._fields['tax_type'].selection).get(self.tax_type)}"
            )

        return created_count
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # أضف هذا السطر أيضاً
import logging
from odoo.exceptions import UserError
import calendar

_logger = logging.getLogger(__name__)


class TaxClient(models.Model):
    _name = 'tax.client'
    _description = 'عميل ضريبي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='اسم العميل', required=True, tracking=True)
    email = fields.Char(string='  البريد الإلكترونى للعميل', required=True, tracking=True)
    phone = fields.Char(string='رقم الهاتف', tracking=True)
    manager_name = fields.Char(string='اسم المدير', tracking=True)
    company_address = fields.Text(string='عنوان الشركة', tracking=True)
    tax_email = fields.Char(string='إيميل الضريبة', tracking=True, help='البريد الإلكتروني المستخدم في موقع الضرائب')
    tax_password = fields.Char(string='باسورد الضريبة', tracking=True, help='كلمة المرور المستخدمة في موقع الضرائب')
    tax_number = fields.Char(string='رقم تسجيل ضريبة القيمة المضافة', tracking=True)

    license_number = fields.Char(string='رقم الرخصة', tracking=True )
    legal_form = fields.Selection([
        ('llc', 'شركة ذات مسؤولية محدودة'),
        ('single_llc', 'شركة ذات مسؤولية للشخص الواحد'),
        ('sole_proprietorship', 'شركة فردية'),
        ('free_zone', 'منطقة حرة')
    ], string='الشكل القانوني للرخصة', tracking=True , required=True)

    has_corporate_tax = fields.Boolean(string='له ضريبة شركات', default=False, tracking=True)
    corporate_tax_registration = fields.Char(
        string='رقم التسجيل الضريبي لضريبة الشركات',
        tracking=True,
        help='رقم التسجيل في ضريبة الشركات'
    )

    license_issue_date = fields.Date(string='تاريخ إصدار الرخصة', tracking=True)
    license_expiry_date = fields.Date(string='تاريخ انتهاء الرخصة', tracking=True)

    # حقول محسوبة لحالة الرخصة
    license_status = fields.Selection([
        ('valid', 'سارية'),
        ('expiring_soon', 'قريبة من الانتهاء'),
        ('expired', 'منتهية الصلاحية')
    ], string='حالة الرخصة', compute='_compute_license_status', store=True)

    days_to_license_expiry = fields.Integer(
        string='أيام متبقية على انتهاء الرخصة',
        compute='_compute_license_status',
        store=False
    )
    activity_type = fields.Selection([
        ('trading', 'تجاري'),
        ('industrial', 'صناعي'),
        ('service', 'خدمي'),
        ('professional', 'مهني'),
        ('other', 'أخرى')
    ], string='نوع الرخصة', default='trading')


    declaration_ids = fields.One2many('tax.declaration', 'client_id', string='الإقرارات الضريبية')
    declaration_count = fields.Integer(string='عدد الإقرارات', compute='_compute_declaration_count')

    lang = fields.Selection(
        string='اللغة',
        selection='_get_lang_selection',
        default=lambda self: self.env.lang,
        help="لغة المراسلات مع العميل"
    )

    tax_setting_ids = fields.One2many('tax.client.settings', 'client_id', string='إعدادات الضرائب')
    auto_generate = fields.Boolean(string='توليد تلقائي للإقرارات', default=True)

    active = fields.Boolean(string='حالة العميل', default=True)
    notes = fields.Text(string='ملاحظات')

    ownership_type = fields.Selection([
        ('single_owner', 'مالك واحد'),
        ('partners', 'شركاء')
    ], string='الشركاء', tracking=True)

    partner_ids = fields.One2many('tax.client.partner', 'client_id', string='الشركاء/المالكين')
    partners_count = fields.Integer(string='عدد الشركاء', compute='_compute_partners_count')
    total_ownership_percentage = fields.Float(
        string='إجمالي النسب',
        compute='_compute_total_ownership',
        store=False
    )

    _sql_constraints = [
        ('tax_number_unique', 'UNIQUE(tax_number)',
         'الرقم الضريبي موجود مسبقاً! يجب أن يكون الرقم الضريبي فريداً لكل عميل.'),
        ('corporate_tax_registration_unique', 'UNIQUE(corporate_tax_registration)',
         'رقم التسجيل الضريبي لضريبة الشركات موجود مسبقاً! يجب أن يكون رقم التسجيل فريداً.'),
    ]

    submitted_declarations_count = fields.Integer(
        string='الإقرارات المقدمة',
        compute='_compute_declarations_stats'
    )
    pending_declarations_count = fields.Integer(
        string='الإقرارات المعلقة',
        compute='_compute_declarations_stats'
    )
    overdue_declarations_count = fields.Integer(
        string='الإقرارات المتأخرة',
        compute='_compute_declarations_stats'
    )

    submitted_declaration_ids = fields.One2many(
        'tax.declaration',
        'client_id',
        string='الإقرارات المقدمة',
        domain=[('state', '=', 'submitted')]
    )

    @api.depends('declaration_ids', 'declaration_ids.state', 'declaration_ids.due_date')
    def _compute_declarations_stats(self):
        """حساب إحصائيات الإقرارات"""
        today = fields.Date.today()
        for record in self:
            record.submitted_declarations_count = len(record.declaration_ids.filtered(
                lambda d: d.state == 'submitted'
            ))
            record.pending_declarations_count = len(record.declaration_ids.filtered(
                lambda d: d.state not in ['submitted', 'cancelled']
            ))
            record.overdue_declarations_count = len(record.declaration_ids.filtered(
                lambda d: d.due_date < today and d.state not in ['submitted', 'cancelled']
            ))

    @api.depends('partner_ids')
    def _compute_partners_count(self):
        for record in self:
            record.partners_count = len(record.partner_ids)

    @api.depends('partner_ids.ownership_percentage')
    def _compute_total_ownership(self):
        """حساب إجمالي نسب الملكية"""
        for record in self:
            record.total_ownership_percentage = sum(record.partner_ids.mapped('ownership_percentage'))

    @api.constrains('ownership_type', 'partner_ids')
    def _check_partners_constraint(self):
        """التحقق من عدد الشركاء حسب النوع"""
        for record in self:
            if record.ownership_type == 'single_owner' and len(record.partner_ids) > 1:
                raise UserError('في حالة مالك واحد، لا يمكن إضافة أكثر من شريك واحد')

            # التحقق من إجمالي النسب
            if record.partner_ids:
                total = sum(partner.ownership_percentage for partner in record.partner_ids)
                if total > 100:
                    raise UserError(
                        f'إجمالي نسب الملكية ({total:.2f}%) تجاوز 100%.\n'
                        f'الإجمالي الحالي: {total}%\n'
                        f'الرجاء تعديل النسب بحيث لا يتجاوز الإجمالي 100%.'
                    )



    @api.depends('license_expiry_date')
    def _compute_license_status(self):
        """حساب حالة الرخصة والأيام المتبقية"""
        today = fields.Date.today()
        for record in self:
            if not record.license_expiry_date:
                record.license_status = False
                record.days_to_license_expiry = 0
                continue

            days_remaining = (record.license_expiry_date - today).days
            record.days_to_license_expiry = days_remaining

            if days_remaining < 0:
                record.license_status = 'expired'
            elif days_remaining <= 30:
                record.license_status = 'expiring_soon'
            else:
                record.license_status = 'valid'

    @api.onchange('has_corporate_tax')
    def _onchange_has_corporate_tax(self):
        """مسح رقم التسجيل الضريبي إذا تم إلغاء تفعيل ضريبة الشركات"""
        if not self.has_corporate_tax:
            self.corporate_tax_registration = False

    @api.constrains('license_issue_date', 'license_expiry_date')
    def _check_license_dates(self):
        """التحقق من صحة تواريخ الرخصة"""
        for record in self:
            if record.license_issue_date and record.license_expiry_date:
                if record.license_expiry_date <= record.license_issue_date:
                    raise UserError('تاريخ انتهاء الرخصة يجب أن يكون بعد تاريخ الإصدار')

    @api.model
    def check_expiring_licenses(self):
        """دالة للتحقق من الرخص القريبة من الانتهاء وإرسال تنبيهات"""
        today = fields.Date.today()
        warning_date = today + timedelta(days=30)

        expiring_clients = self.search([
            ('license_expiry_date', '<=', warning_date),
            ('license_expiry_date', '>=', today),
            ('active', '=', True)
        ])

        for client in expiring_clients:
            days_remaining = (client.license_expiry_date - today).days
            client.message_post(
                body=f"تنبيه: الرخصة التجارية ستنتهي خلال {days_remaining} يوم في {client.license_expiry_date.strftime('%d/%m/%Y')}",
                subject="تنبيه انتهاء الرخصة التجارية",
                message_type='notification'
            )

        return True



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
        ('9%', ' ضريبة %9 '),
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

    vat_start_month = fields.Selection([
        ('1', 'يناير'),
        ('2', 'فبراير'),
        ('3', 'مارس'),
        ('4', 'أبريل'),
        ('5', 'مايو'),
        ('6', 'يونيو'),
        ('7', 'يوليو'),
        ('8', 'أغسطس'),
        ('9', 'سبتمبر'),
        ('10', 'أكتوبر'),
        ('11', 'نوفمبر'),
        ('12', 'ديسمبر')
    ], string='شهر بداية السنة الضريبية',
        help='الشهر الذي تبدأ فيه السنة الضريبية للقيمة المضافة (يؤثر على حساب الفترات)')

    year = fields.Integer(string='السنة', required=True, default=lambda self: fields.Date.today().year)
    due_date = fields.Date(string='تاريخ الاستحقاق', required=True, tracking=True)

    # تواريخ الفترة الضريبية
    period_start_date = fields.Date(string='بداية الفترة', compute='_compute_period_dates', store=True)
    period_end_date = fields.Date(string='نهاية الفترة', compute='_compute_period_dates', store=True)

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('waiting', 'في الانتظار'),
        ('first_reminded', 'تذكير أول'),
        ('second_reminded', 'تذكير ثاني'),
        ('documents_received', 'تم استلام المستندات'),
        ('submitted', 'تم التقديم'),
        ('cancelled', 'ملغي')
    ], string='الحالة', default='draft', tracking=True)

    # التذكير الأول
    enable_first_reminder = fields.Boolean(string='تفعيل التذكير الأول', default=True)
    days_after_period_first = fields.Integer(string='أيام بعد انتهاء الفترة (تذكير أول)', default=5,
                                             help='عدد الأيام بعد انتهاء الفترة الضريبية لإرسال التذكير الأول')
    first_reminder_sent = fields.Boolean(string='تم إرسال التذكير الأول', default=False)
    first_reminder_sent_date = fields.Datetime(string='تاريخ إرسال التذكير الأول')
    first_reminder_date = fields.Date(string='موعد التذكير الأول', compute='_compute_reminder_dates', store=True)

    # التذكير الثاني
    enable_second_reminder = fields.Boolean(string='تفعيل التذكير الثاني', default=True)
    days_after_period_second = fields.Integer(string='أيام بعد انتهاء الفترة (تذكير ثاني)', default=10,
                                              help='عدد الأيام بعد انتهاء الفترة الضريبية لإرسال التذكير الثاني')
    second_reminder_sent = fields.Boolean(string='تم إرسال التذكير الثاني', default=False)
    second_reminder_sent_date = fields.Datetime(string='تاريخ إرسال التذكير الثاني')
    second_reminder_date = fields.Date(string='موعد التذكير الثاني', compute='_compute_reminder_dates', store=True)

    # حقل التوافق مع النظام القديم
    reminder_sent = fields.Boolean(string='تم إرسال التذكير', compute='_compute_reminder_sent', store=True)
    reminder_sent_date = fields.Datetime(string='تاريخ إرسال التذكير', compute='_compute_reminder_sent_date',
                                         store=True)
    days_before_reminder = fields.Integer(string='أيام قبل التذكير (قديم)', default=7,
                                          help='هذا الحقل للتوافق مع النظام القديم، استخدم الحقول الجديدة')

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

    @api.depends('period_type', 'period', 'year', 'client_id')
    def _compute_period_dates(self):
        """حساب تواريخ بداية ونهاية الفترة الضريبية"""
        for record in self:
            if not record.period or not record.year:
                record.period_start_date = False
                record.period_end_date = False
                continue

            try:
                period_num = int(record.period)

                if record.period_type == 'monthly':
                    # الشهور مباشرة
                    record.period_start_date = datetime(record.year, period_num, 1).date()
                    last_day = calendar.monthrange(record.year, period_num)[1]
                    record.period_end_date = datetime(record.year, period_num, last_day).date()

                elif record.period_type == 'quarterly':
                    # للقيمة المضافة مع تاريخ بداية خاص
                    if record.tax_type == 'vat' and record.client_id:
                        setting = self.env['tax.client.settings'].search([
                            ('client_id', '=', record.client_id.id),
                            ('tax_type', '=', 'vat'),
                            ('active', '=', True)
                        ], limit=1)

                        if setting and setting.tax_year_start_date:
                            start_date = setting.tax_year_start_date
                            start_month = start_date.month
                            start_day = start_date.day
                            quarter_start_month = start_month + ((period_num - 1) * 3)
                            quarter_start_year = record.year
                            if quarter_start_month > 12:
                                quarter_start_month -= 12
                                quarter_start_year += 1

                            # بداية الفترة
                            record.period_start_date = datetime(quarter_start_year, quarter_start_month,
                                                                start_day).date()

                            # نهاية الفترة (3 شهور بعد البداية - يوم واحد)
                            from dateutil.relativedelta import relativedelta
                            record.period_end_date = record.period_start_date + relativedelta(months=3, days=-1)

                        else:
                            start_month = (period_num - 1) * 3 + 1
                            end_month = period_num * 3

                            record.period_start_date = datetime(record.year, start_month, 1).date()
                            last_day = calendar.monthrange(record.year, end_month)[1]
                            record.period_end_date = datetime(record.year, end_month, last_day).date()
                    else:
                        start_month = (period_num - 1) * 3 + 1
                        end_month = period_num * 3

                        record.period_start_date = datetime(record.year, start_month, 1).date()
                        last_day = calendar.monthrange(record.year, end_month)[1]
                        record.period_end_date = datetime(record.year, end_month, last_day).date()

                elif record.period_type == 'semi_annual':
                    if period_num == 1:
                        record.period_start_date = datetime(record.year, 1, 1).date()
                        record.period_end_date = datetime(record.year, 6, 30).date()
                    else:
                        record.period_start_date = datetime(record.year, 7, 1).date()
                        record.period_end_date = datetime(record.year, 12, 31).date()

                elif record.period_type == 'annual':
                    record.period_start_date = datetime(record.year, 1, 1).date()
                    record.period_end_date = datetime(record.year, 12, 31).date()

            except Exception as e:
                _logger.error(f"خطأ في حساب تواريخ الفترة: {str(e)}")
                record.period_start_date = False
                record.period_end_date = False

    @api.depends('period_end_date', 'days_after_period_first', 'days_after_period_second',
                 'enable_first_reminder', 'enable_second_reminder')
    def _compute_reminder_dates(self):
        """حساب مواعيد التذكيرات بناءً على تاريخ انتهاء الفترة"""
        for record in self:
            if record.period_end_date:
                if record.enable_first_reminder:
                    record.first_reminder_date = record.period_end_date + timedelta(days=record.days_after_period_first)
                else:
                    record.first_reminder_date = False

                if record.enable_second_reminder:
                    record.second_reminder_date = record.period_end_date + timedelta(
                        days=record.days_after_period_second)
                else:
                    record.second_reminder_date = False
            else:
                record.first_reminder_date = False
                record.second_reminder_date = False

    @api.depends('first_reminder_sent', 'second_reminder_sent')
    def _compute_reminder_sent(self):
        """للتوافق مع النظام القديم"""
        for record in self:
            record.reminder_sent = record.first_reminder_sent or record.second_reminder_sent

    @api.depends('first_reminder_sent_date', 'second_reminder_sent_date')
    def _compute_reminder_sent_date(self):
        """للتوافق مع النظام القديم"""
        for record in self:
            if record.second_reminder_sent_date:
                record.reminder_sent_date = record.second_reminder_sent_date
            elif record.first_reminder_sent_date:
                record.reminder_sent_date = record.first_reminder_sent_date
            else:
                record.reminder_sent_date = False

    @api.depends('tax_type', 'period_type', 'period', 'year')
    def _compute_display_fields(self):
        tax_types = {
            'vat': 'ضريبة القيمة المضافة',
            '9%': 'ضريبة %9',

            'other': 'أخرى'
        }

        months = ['', 'يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']

        for record in self:
            record.tax_type_display = tax_types.get(record.tax_type, record.tax_type or '')

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
                record.days_remaining = ((record.due_date - today ).days) - 2
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
            year = vals.get('year', fields.Date.today().year)
            sequence = self.env['ir.sequence'].next_by_code('tax.declaration.sequence')
            if not sequence:
                sequence = self.env['ir.sequence'].sudo().create({
                    'name': 'Tax Declaration Sequence',
                    'code': 'tax.declaration.sequence',
                    'prefix': 'TAX/',
                    'padding': 4
                }).next_by_code('tax.declaration.sequence')
            vals['name'] = f"TAX/{year}/{sequence}"
        return super(TaxDeclaration, self).create(vals)

    def action_send_first_reminder(self):
        """إرسال التذكير الأول للعميل"""
        self.ensure_one()
        return self._send_reminder('first')

    def action_send_second_reminder(self):
        """إرسال التذكير الثاني للعميل"""
        self.ensure_one()
        return self._send_reminder('second')

    def action_send_reminder(self):
        self.ensure_one()
        if not self.first_reminder_sent and self.enable_first_reminder:
            return self._send_reminder('first')
        elif not self.second_reminder_sent and self.enable_second_reminder:
            return self._send_reminder('second')
        else:
            if self.second_reminder_sent:
                return self._send_reminder('second')
            else:
                return self._send_reminder('first')

    def _send_reminder(self, reminder_type):

        self.ensure_one()

        template_id = self.env.ref('tax_reminder.email_template_tax_reminder', raise_if_not_found=False)

        if not template_id:
            template_id = self.env['mail.template'].search([
                ('name', '=', 'تذكير بالإقرار الضريبي'),
                ('model_id.model', '=', 'tax.declaration')
            ], limit=1)

        if template_id:
            try:
                ctx = self.env.context.copy()
                ctx['reminder_type'] = reminder_type
                ctx['reminder_number'] = 'الأول' if reminder_type == 'first' else 'الثاني'

                template_id.with_context(ctx).send_mail(self.id, force_send=True)

                update_vals = {}
                if reminder_type == 'first':
                    update_vals = {
                        'first_reminder_sent': True,
                        'first_reminder_sent_date': fields.Datetime.now(),
                        'state': 'first_reminded' if self.state in ['draft', 'waiting'] else self.state
                    }
                else:  # second
                    update_vals = {
                        'second_reminder_sent': True,
                        'second_reminder_sent_date': fields.Datetime.now(),
                        'state': 'second_reminded' if self.state in ['draft', 'waiting',
                                                                     'first_reminded'] else self.state
                    }

                self.write(update_vals)

                reminder_text = 'الأول' if reminder_type == 'first' else 'الثاني'
                self.message_post(
                    body=f"تم إرسال التذكير {reminder_text} بالبريد الإلكتروني إلى {self.client_id.name} على {self.client_id.email}",
                    subject=f"التذكير {reminder_text} بالإقرار الضريبي"
                )

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f'تم إرسال التذكير {reminder_text} بنجاح',
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
        self.write({
            'state': 'draft',
            'first_reminder_sent': False,
            'second_reminder_sent': False,
            'first_reminder_sent_date': False,
            'second_reminder_sent_date': False
        })
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

        # البحث عن الإقرارات التي تحتاج تذكير أول
        first_reminder_declarations = self.search([
            ('state', 'in', ['draft', 'waiting']),
            ('enable_first_reminder', '=', True),
            ('first_reminder_sent', '=', False),
            ('first_reminder_date', '!=', False),
            ('first_reminder_date', '<=', today)
        ])

        for declaration in first_reminder_declarations:
            declaration._send_reminder('first')
            _logger.info(f"تم إرسال التذكير الأول للإقرار: {declaration.name}")

        # البحث عن الإقرارات التي تحتاج تذكير ثاني
        second_reminder_declarations = self.search([
            ('state', 'in', ['draft', 'waiting', 'first_reminded']),
            ('enable_second_reminder', '=', True),
            ('second_reminder_sent', '=', False),
            ('second_reminder_date', '!=', False),
            ('second_reminder_date', '<=', today)
        ])

        for declaration in second_reminder_declarations:
            declaration._send_reminder('second')
            _logger.info(f"تم إرسال التذكير الثاني للإقرار: {declaration.name}")

        # التوافق مع النظام القديم - التذكير بناءً على تاريخ الاستحقاق
        old_system_declarations = self.search([
            ('state', 'in', ['draft', 'waiting']),
            ('first_reminder_sent', '=', False),
            ('second_reminder_sent', '=', False),
            ('enable_first_reminder', '=', False),
            ('enable_second_reminder', '=', False),
            ('due_date', '!=', False)
        ])

        for declaration in old_system_declarations:
            days_remaining = (declaration.due_date - today).days
            if days_remaining == declaration.days_before_reminder:
                declaration.action_send_reminder()
                _logger.info(f"تم إرسال تذكير (نظام قديم) للإقرار: {declaration.name}")

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
            '9%': 'ضريبة %9',

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
        ('9%', 'ضريبة %9'),

        ('other', 'أخرى')
    ], string='نوع الضريبة', required=True)

    period_type = fields.Selection([
        ('monthly', 'شهري'),
        ('quarterly', 'ربع سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('annual', 'سنوي')
    ], string='دورية التقديم', required=True, default='quarterly')

    # طريقة تحديد موعد الاستحقاق
    due_date_method = fields.Selection([
        ('months_after', 'عدد شهور بعد انتهاء الفترة'),
        ('specific_month', 'شهر محدد')
    ], string='طريقة تحديد الاستحقاق', default='specific_month', required=True)

    # للطريقة القديمة - عدد الشهور
    months_after_period = fields.Integer(string='شهور بعد انتهاء الفترة', default=1,
                                         help='عدد الشهور بعد انتهاء الفترة لموعد الاستحقاق')

    # للطريقة الجديدة - اختيار الشهر مباشرة
    due_month = fields.Selection([
        ('1', 'يناير'),
        ('2', 'فبراير'),
        ('3', 'مارس'),
        ('4', 'أبريل'),
        ('5', 'مايو'),
        ('6', 'يونيو'),
        ('7', 'يوليو'),
        ('8', 'أغسطس'),
        ('9', 'سبتمبر'),
        ('10', 'أكتوبر'),
        ('11', 'نوفمبر'),
        ('12', 'ديسمبر')
    ], string='شهر الاستحقاق', help='الشهر الذي يستحق فيه تقديم الإقرار')

    tax_year_start_date = fields.Date(
        string='تاريخ بداية السنة الضريبية',
        help='التاريخ الفعلي لبداية السنة الضريبية للعميل'
    )

    # حقل محسوب لعرض رقم الفترة الحالية
    current_period_number = fields.Integer(
        string='رقم الفترة الحالية',
        compute='_compute_current_period',
        store=False
    )

    # حقل محسوب لعرض تواريخ الفترة الحالية
    current_period_start = fields.Date(
        string='بداية الفترة الحالية',
        compute='_compute_current_period',
        store=False
    )

    current_period_end = fields.Date(
        string='نهاية الفترة الحالية',
        compute='_compute_current_period',
        store=False
    )

    # يوم الاستحقاق في الشهر
    day_of_month = fields.Integer(string='يوم الاستحقاق من الشهر', default=15,
                                  help='اليوم من الشهر الذي يستحق فيه الإقرار')

    # التذكيرات
    enable_first_reminder = fields.Boolean(string='تفعيل التذكير الأول', default=True)
    days_after_period_first = fields.Integer(string='أيام بعد الفترة (تذكير أول)', default=5,
                                             help='عدد الأيام بعد انتهاء الفترة الضريبية لإرسال التذكير الأول')

    enable_second_reminder = fields.Boolean(string='تفعيل التذكير الثاني', default=True)
    days_after_period_second = fields.Integer(string='أيام بعد الفترة (تذكير ثاني)', default=10,
                                              help='عدد الأيام بعد انتهاء الفترة الضريبية لإرسال التذكير الثاني')

    # حقل قديم للتوافق
    days_before_reminder = fields.Integer(string='أيام التذكير قبل الاستحقاق (قديم)', default=7)

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

    def get_period_dates(self, period_number, year):
        """دالة مساعدة للحصول على تواريخ فترة محددة"""
        if not self.tax_year_start_date:
            return False, False

        if self.period_type == 'monthly':
            period_start = self.tax_year_start_date + relativedelta(months=period_number - 1)
            period_end = period_start + relativedelta(months=1, days=-1)

        elif self.period_type == 'quarterly':
            period_start = self.tax_year_start_date + relativedelta(months=(period_number - 1) * 3)
            period_end = period_start + relativedelta(months=3, days=-1)

        elif self.period_type == 'semi_annual':
            period_start = self.tax_year_start_date + relativedelta(months=(period_number - 1) * 6)
            period_end = period_start + relativedelta(months=6, days=-1)

        elif self.period_type == 'annual':
            period_start = self.tax_year_start_date + relativedelta(years=period_number - 1)
            period_end = period_start + relativedelta(years=1, days=-1)
        else:
            return False, False

        # تعديل السنة إذا لزم
        year_diff = year - self.tax_year_start_date.year
        if year_diff > 0:
            period_start = period_start + relativedelta(years=year_diff)
            period_end = period_end + relativedelta(years=year_diff)

        return period_start, period_end

    @api.depends('tax_year_start_date', 'period_type')
    def _compute_current_period(self):
        """حساب الفترة الحالية بناءً على تاريخ البداية"""
        for record in self:
            if not record.tax_year_start_date:
                record.current_period_number = 0
                record.current_period_start = False
                record.current_period_end = False
                continue

            today = fields.Date.today()
            start_date = record.tax_year_start_date

            if record.period_type == 'monthly':
                # حساب عدد الشهور منذ البداية
                months_diff = (today.year - start_date.year) * 12 + (today.month - start_date.month)
                current_period = (months_diff % 12) + 1

                # حساب تواريخ الفترة الحالية
                period_start = start_date + relativedelta(months=months_diff)
                period_end = period_start + relativedelta(months=1, days=-1)

            elif record.period_type == 'quarterly':
                # حساب عدد الأرباع منذ البداية
                months_diff = (today.year - start_date.year) * 12 + (today.month - start_date.month)
                quarters_diff = months_diff // 3
                current_period = (quarters_diff % 4) + 1

                # حساب تواريخ الفترة الحالية
                period_start = start_date + relativedelta(months=quarters_diff * 3)
                period_end = period_start + relativedelta(months=3, days=-1)

            elif record.period_type == 'semi_annual':
                # حساب عدد الأنصاف منذ البداية
                months_diff = (today.year - start_date.year) * 12 + (today.month - start_date.month)
                halves_diff = months_diff // 6
                current_period = (halves_diff % 2) + 1

                # حساب تواريخ الفترة الحالية
                period_start = start_date + relativedelta(months=halves_diff * 6)
                period_end = period_start + relativedelta(months=6, days=-1)

            elif record.period_type == 'annual':
                # حساب عدد السنوات منذ البداية
                years_diff = today.year - start_date.year
                current_period = 1

                # حساب تواريخ الفترة الحالية
                period_start = start_date + relativedelta(years=years_diff)
                period_end = period_start + relativedelta(years=1, days=-1)
            else:
                current_period = 0
                period_start = False
                period_end = False

            record.current_period_number = current_period
            record.current_period_start = period_start
            record.current_period_end = period_end

    @api.onchange('period_type')
    def _onchange_period_type(self):
        """تحديد شهر الاستحقاق الافتراضي بناءً على نوع الفترة"""
        if self.period_type == 'quarterly':
            # للإقرارات الربعية، الاستحقاق عادة في أبريل، يوليو، أكتوبر، يناير
            self.due_month = '4'  # أبريل كمثال افتراضي
        elif self.period_type == 'annual':
            # للإقرارات السنوية، الاستحقاق عادة في أبريل
            self.due_month = '4'
        elif self.period_type == 'monthly':
            # للإقرارات الشهرية، الاستحقاق في الشهر التالي
            current_month = fields.Date.today().month
            next_month = current_month + 1 if current_month < 12 else 1
            self.due_month = str(next_month)

    @api.model
    def get_due_date(self, year, period):
        """حساب تاريخ الاستحقاق بناءً على الإعدادات"""

        # حساب نهاية الفترة أولاً
        period_start, period_end = self.get_period_dates(int(period), year)

        if not period_end:
            # إذا فشل حساب التواريخ، نستخدم الطريقة القديمة
            return self._get_due_date_old_method(year, period)

        # لضريبة القيمة المضافة: 28 يوم بعد نهاية الفترة
        if self.tax_type == 'vat':
            return period_end + timedelta(days=28)

        # للضرائب الأخرى: استخدام الإعدادات المحددة
        if self.due_date_method == 'specific_month':
            if not self.due_month:
                return self._get_due_date_old_method(year, period)

            due_month = int(self.due_month)
            due_year = year

            # معالجة خاصة حسب نوع الفترة
            if self.period_type == 'quarterly':
                quarter = int(period)
                end_month = quarter * 3
                if due_month <= end_month:
                    due_year += 1

            elif self.period_type == 'annual':
                due_year += 1

            elif self.period_type == 'monthly':
                month = int(period)
                if due_month <= month:
                    due_year += 1

            elif self.period_type == 'semi_annual':
                half = int(period)
                if half == 2 and due_month <= 6:
                    due_year += 1

            try:
                due_date = datetime(due_year, due_month, self.day_of_month).date()
            except ValueError:
                import calendar
                last_day = calendar.monthrange(due_year, due_month)[1]
                due_date = datetime(due_year, due_month, min(self.day_of_month, last_day)).date()
        else:
            # استخدام الطريقة القديمة (عدد شهور بعد انتهاء الفترة)
            due_date = self._get_due_date_old_method(year, period)

        return due_date

    def _get_due_date_old_method(self, year, period):
        """الطريقة القديمة لحساب تاريخ الاستحقاق"""
        if self.period_type == 'monthly':
            month = int(period) + self.months_after_period
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

        elif self.period_type == 'quarterly':
            quarter = int(period)
            end_month = quarter * 3
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

        if not self.tax_year_start_date:
            raise UserError('يجب تحديد تاريخ بداية السنة الضريبية أولاً')

        today = fields.Date.today()
        declarations_to_create = []

        # تحديد عدد الفترات المطلوب توليدها
        if self.generation_type == 'months':
            periods_count = self.generation_months
            if self.period_type == 'quarterly':
                periods_count = self.generation_months // 3
            elif self.period_type == 'semi_annual':
                periods_count = self.generation_months // 6
            elif self.period_type == 'annual':
                periods_count = self.generation_months // 12
        elif self.generation_type == 'years':
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

        # البدء من تاريخ البداية المحدد
        start_date = self.tax_year_start_date

        for i in range(periods_count):
            # حساب بداية ونهاية الفترة الحالية
            if self.period_type == 'monthly':
                from dateutil.relativedelta import relativedelta
                period_start = start_date + relativedelta(months=i)
                period_end = period_start + relativedelta(months=1, days=-1)
                period_num = ((i % 12) + 1)

            elif self.period_type == 'quarterly':
                from dateutil.relativedelta import relativedelta
                period_start = start_date + relativedelta(months=i * 3)
                period_end = period_start + relativedelta(months=3, days=-1)
                period_num = ((i % 4) + 1)

            elif self.period_type == 'semi_annual':
                from dateutil.relativedelta import relativedelta
                period_start = start_date + relativedelta(months=i * 6)
                period_end = period_start + relativedelta(months=6, days=-1)
                period_num = ((i % 2) + 1)

            else:  # annual
                from dateutil.relativedelta import relativedelta
                period_start = start_date + relativedelta(years=i)
                period_end = period_start + relativedelta(years=1, days=-1)
                period_num = 1

            # تحديد السنة المالية بناءً على تاريخ البداية
            fiscal_year = period_start.year

            # حساب تاريخ الاستحقاق
            if self.tax_type == 'vat':
                # لضريبة القيمة المضافة: 28 يوم بعد نهاية الفترة
                due_date = period_end + timedelta(days=28)

            elif self.due_date_method == 'specific_month' and self.due_month:
                # للضرائب الأخرى: استخدام الشهر المحدد
                due_month = int(self.due_month)
                due_year = period_end.year

                if due_month <= period_end.month:
                    due_year += 1

                try:
                    due_date = datetime(due_year, due_month, self.day_of_month).date()
                except ValueError:
                    import calendar
                    last_day = calendar.monthrange(due_year, due_month)[1]
                    due_date = datetime(due_year, due_month, min(self.day_of_month, last_day)).date()
            else:
                # الطريقة الافتراضية للضرائب الأخرى
                from dateutil.relativedelta import relativedelta
                due_date = period_end + relativedelta(months=self.months_after_period)
                due_date = due_date.replace(day=min(self.day_of_month, due_date.day))

            # التحقق من وجود إقرار موجود
            existing = self.env['tax.declaration'].search([
                ('client_id', '=', self.client_id.id),
                ('tax_type', '=', self.tax_type),
                ('period', '=', str(period_num)),
                ('year', '=', fiscal_year),
                ('period_start_date', '=', period_start),
                ('period_end_date', '=', period_end),
                ('state', '!=', 'cancelled')
            ], limit=1)

            if not existing:
                declarations_to_create.append({
                    'client_id': self.client_id.id,
                    'tax_type': self.tax_type,
                    'period_type': self.period_type,
                    'period': str(period_num),
                    'year': fiscal_year,
                    'period_start_date': period_start,
                    'period_end_date': period_end,
                    'due_date': due_date,
                    'enable_first_reminder': self.enable_first_reminder,
                    'days_after_period_first': self.days_after_period_first,
                    'enable_second_reminder': self.enable_second_reminder,
                    'days_after_period_second': self.days_after_period_second,
                    'state': 'waiting'
                })

        # إنشاء الإقرارات
        created_count = 0
        if declarations_to_create:
            # حذف الإقرارات القديمة في حالة force_regenerate
            if force_regenerate:
                old_declarations = self.env['tax.declaration'].search([
                    ('client_id', '=', self.client_id.id),
                    ('tax_type', '=', self.tax_type),
                    ('state', '=', 'waiting')
                ])
                old_declarations.unlink()

            created = self.env['tax.declaration'].create(declarations_to_create)
            created_count = len(created)

            if created:
                last_dec = declarations_to_create[-1]
                self.write({
                    'last_generated_year': last_dec['year'],
                    'last_generated_period': last_dec['period']
                })

        if created_count > 0:
            self.client_id.message_post(
                body=f"تم توليد {created_count} إقرار ضريبي جديد لنوع {dict(self._fields['tax_type'].selection).get(self.tax_type)}"
            )

        return created_count


class TaxClientPartner(models.Model):
    _name = 'tax.client.partner'
    _description = 'شريك/مالك'
    _rec_name = 'name'

    client_id = fields.Many2one('tax.client', string='العميل', required=True, ondelete='cascade')
    name = fields.Char(string='الاسم', required=True, tracking=True)
    identity_number = fields.Char(string='رقم الهوية', tracking=True)
    identity_expiry_date = fields.Date(string='تاريخ انتهاء الهوية', tracking=True)
    passport_number = fields.Char(string='رقم جواز السفر', tracking=True)
    passport_expiry_date = fields.Date(string='تاريخ انتهاء جواز السفر', tracking=True)
    ownership_percentage = fields.Float(string='النسبة %', digits=(5, 2), tracking=True)

    # حقول محسوبة لحالة الوثائق
    identity_status = fields.Selection([
        ('valid', 'سارية'),
        ('expiring_soon', 'قريبة من الانتهاء'),
        ('expired', 'منتهية')
    ], string='حالة الهوية', compute='_compute_identity_status', store=True)

    passport_status = fields.Selection([
        ('valid', 'ساري'),
        ('expiring_soon', 'قريب من الانتهاء'),
        ('expired', 'منتهي')
    ], string='حالة الجواز', compute='_compute_passport_status', store=True)

    @api.depends('identity_expiry_date')
    def _compute_identity_status(self):
        """حساب حالة الهوية"""
        today = fields.Date.today()
        for record in self:
            if not record.identity_expiry_date:
                record.identity_status = False
                continue

            days_remaining = (record.identity_expiry_date - today).days

            if days_remaining < 0:
                record.identity_status = 'expired'
            elif days_remaining <= 60:
                record.identity_status = 'expiring_soon'
            else:
                record.identity_status = 'valid'

    @api.constrains('ownership_percentage', 'client_id')
    def _check_total_percentage(self):
        """التحقق من عدم تجاوز إجمالي النسب 100%"""
        for record in self:
            if record.client_id:
                # حساب إجمالي النسب لجميع الشركاء
                total = sum(record.client_id.partner_ids.mapped('ownership_percentage'))
                if total > 100:
                    raise UserError(
                        f'لا يمكن حفظ هذه النسبة!\n'
                        f'إجمالي نسب الملكية سيصبح: {total:.2f}%\n'
                        f'يجب ألا يتجاوز الإجمالي 100%'
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create للتحقق قبل الإنشاء"""
        records = super(TaxClientPartner, self).create(vals_list)
        for record in records:
            record._check_total_percentage()
        return records

    def write(self, vals):
        """Override write للتحقق قبل التعديل"""
        res = super(TaxClientPartner, self).write(vals)
        if 'ownership_percentage' in vals:
            self._check_total_percentage()
        return res

    @api.constrains('ownership_percentage', 'client_id')
    def _check_total_percentage(self):
        """التحقق من عدم تجاوز إجمالي النسب 100%"""
        for record in self:
            if record.client_id:
                total = sum(record.client_id.partner_ids.mapped('ownership_percentage'))
                if total > 100:
                    raise UserError(
                        f'❌ تجاوز النسبة المسموحة!\n\n'
                        f'إجمالي نسب الملكية: {total:.1f}%\n'
                        f'الحد الأقصى المسموح: 100%\n'
                        f'الزيادة: {total - 100:.1f}%\n\n'
                        f'الرجاء تعديل النسب.'
                    )

    @api.depends('passport_expiry_date')
    def _compute_passport_status(self):
        """حساب حالة جواز السفر"""
        today = fields.Date.today()
        for record in self:
            if not record.passport_expiry_date:
                record.passport_status = False
                continue

            days_remaining = (record.passport_expiry_date - today).days

            if days_remaining < 0:
                record.passport_status = 'expired'
            elif days_remaining <= 90:
                record.passport_status = 'expiring_soon'
            else:
                record.passport_status = 'valid'

    @api.constrains('ownership_percentage')
    def _check_ownership_percentage(self):
        """التحقق من صحة النسبة"""
        for record in self:
            if record.ownership_percentage < 0 or record.ownership_percentage > 100:
                raise UserError('النسبة يجب أن تكون بين 0 و 100')
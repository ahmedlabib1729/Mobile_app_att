# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta
import re


class MemberProfile(models.Model):
    _name = 'charity.member.profile'
    _description = 'ملف العضوة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'
    _order = 'member_number desc'

    # رقم العضوية
    member_number = fields.Char(
        string='رقم العضوية',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'جديد',
        tracking=True
    )

    # معلومات العضوة الأساسية
    full_name = fields.Char(
        string='الاسم الثلاثي باللغة العربية',
        required=True,
        tracking=True,
        help='أدخل الاسم الثلاثي'
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        required=True,
        tracking=True,
        help='تاريخ الميلاد'
    )

    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True,
        help='العمر المحسوب من تاريخ الميلاد'
    )

    # معلومات التواصل
    mobile = fields.Char(
        string='رقم التواصل',
        required=True,
        tracking=True,
        help='رقم الهاتف للتواصل'
    )

    whatsapp = fields.Char(
        string='رقم الواتساب',
        required=True,
        help='رقم الواتساب للتواصل'
    )

    email = fields.Char(
        string='البريد الإلكتروني',
        help='البريد الإلكتروني للتواصل'
    )

    # معلومات إضافية
    nationality = fields.Many2one(
        'res.country',
        string='الجنسية',
        help='جنسية العضوة'
    )

    address = fields.Text(
        string='العنوان',
        help='عنوان السكن'
    )

    # حالة العضوية
    membership_status = fields.Selection([
        ('active', 'نشطة'),
        ('inactive', 'غير نشطة'),
        ('suspended', 'موقوفة')
    ], string='حالة العضوية',
        default='active',
        tracking=True,
        compute='_compute_membership_status',
        store=True
    )

    # تواريخ مهمة
    registration_date = fields.Date(
        string='تاريخ التسجيل',
        default=fields.Date.today,
        readonly=True,
        tracking=True
    )

    last_subscription_date = fields.Date(
        string='تاريخ آخر اشتراك',
        compute='_compute_subscription_info',
        store=True
    )

    current_subscription_end = fields.Date(
        string='تاريخ انتهاء الاشتراك الحالي',
        compute='_compute_subscription_info',
        store=True
    )

    # معلومات النظام
    active = fields.Boolean(
        string='نشط',
        default=True,
        help='إذا تم إلغاء التحديد، سيتم أرشفة العضوة'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    # العلاقات
    subscription_ids = fields.One2many(
        'charity.member.subscription',
        'member_id',
        string='الاشتراكات',
        help='جميع الاشتراكات الخاصة بالعضوة'
    )

    subscriptions_count = fields.Integer(
        string='عدد الاشتراكات',
        compute='_compute_subscriptions_count',
        help='عدد الاشتراكات الكلي'
    )

    active_subscription_count = fields.Integer(
        string='الاشتراكات النشطة',
        compute='_compute_subscriptions_count',
        help='عدد الاشتراكات النشطة حالياً'
    )

    id_card_file = fields.Binary(
        string='صورة الهوية',
        attachment=True,
        help='صورة الهوية'
    )

    id_card_filename = fields.Char(
        string='اسم ملف الهوية'
    )

    passport_file = fields.Binary(
        string='صورة الباسبور',
        attachment=True,
        help='صورة جواز السفر'
    )

    passport_filename = fields.Char(
        string='اسم ملف الباسبور'
    )

    residence_file = fields.Binary(
        string='صورة الإقامة',
        attachment=True,
        help='صورة الإقامة'
    )

    residence_filename = fields.Char(
        string='اسم ملف الإقامة'
    )

    @api.model
    def create(self, vals):
        """إنشاء رقم عضوية تلقائي"""
        if vals.get('member_number', 'جديد') == 'جديد':
            vals['member_number'] = self.env['ir.sequence'].next_by_code('charity.member.profile') or 'جديد'
        return super(MemberProfile, self).create(vals)

    @api.depends('birth_date')
    def _compute_age(self):
        """حساب العمر من تاريخ الميلاد"""
        today = date.today()
        for record in self:
            if record.birth_date:
                age = relativedelta(today, record.birth_date)
                record.age = age.years
            else:
                record.age = 0

    @api.depends('subscription_ids', 'subscription_ids.state', 'subscription_ids.end_date')
    def _compute_membership_status(self):
        """حساب حالة العضوية بناءً على الاشتراكات"""
        today = fields.Date.today()
        for record in self:
            active_subs = record.subscription_ids.filtered(
                lambda s: s.state == 'active' and s.end_date >= today
            )
            if active_subs:
                record.membership_status = 'active'
            else:
                record.membership_status = 'inactive'

    @api.depends('subscription_ids', 'subscription_ids.state', 'subscription_ids.start_date', 'subscription_ids.end_date')
    def _compute_subscription_info(self):
        """حساب معلومات الاشتراك"""
        for record in self:
            subscriptions = record.subscription_ids.sorted('start_date', reverse=True)
            if subscriptions:
                record.last_subscription_date = subscriptions[0].start_date
                active_sub = subscriptions.filtered(lambda s: s.state == 'active')
                if active_sub:
                    record.current_subscription_end = active_sub[0].end_date
                else:
                    record.current_subscription_end = False
            else:
                record.last_subscription_date = False
                record.current_subscription_end = False

    @api.depends('subscription_ids')
    def _compute_subscriptions_count(self):
        """حساب عدد الاشتراكات"""
        today = fields.Date.today()
        for record in self:
            record.subscriptions_count = len(record.subscription_ids)
            record.active_subscription_count = len(
                record.subscription_ids.filtered(
                    lambda s: s.state == 'active' and s.end_date >= today
                )
            )

    @api.constrains('mobile', 'whatsapp')
    def _check_phone_numbers(self):
        """التحقق من صحة أرقام الهواتف"""
        phone_pattern = re.compile(r'^[\d\s\-\+]+$')
        for record in self:
            if record.mobile and not phone_pattern.match(record.mobile):
                raise ValidationError('رقم التواصل غير صحيح!')
            if record.whatsapp and not phone_pattern.match(record.whatsapp):
                raise ValidationError('رقم الواتساب غير صحيح!')

    @api.constrains('email')
    def _check_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for record in self:
            if record.email and not email_pattern.match(record.email):
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    @api.constrains('birth_date')
    def _check_birth_date(self):
        """التحقق من صحة تاريخ الميلاد"""
        for record in self:
            if record.birth_date:
                if record.birth_date > date.today():
                    raise ValidationError('تاريخ الميلاد لا يمكن أن يكون في المستقبل!')

    def action_view_subscriptions(self):
        """عرض اشتراكات العضوة"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'اشتراكات {self.full_name}',
            'view_mode': 'list,form',
            'res_model': 'charity.member.subscription',
            'domain': [('member_id', '=', self.id)],
            'context': {
                'default_member_id': self.id,
                'default_department_id': self._context.get('department_id')
            }
        }

    def action_create_subscription(self):
        """إنشاء اشتراك جديد"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'اشتراك جديد',
            'view_mode': 'form',
            'res_model': 'charity.member.subscription',
            'target': 'new',
            'context': {
                'default_member_id': self.id,
                'default_department_id': self._context.get('department_id')
            }
        }

    def name_get(self):
        """تخصيص طريقة عرض اسم العضوة"""
        result = []
        for record in self:
            name = f"{record.full_name} - {record.member_number}"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        """البحث في العضوات بالاسم أو رقم العضوية أو رقم الهاتف"""
        args = args or []
        if name:
            args = ['|', '|', '|',
                    ('full_name', operator, name),
                    ('member_number', operator, name),
                    ('mobile', operator, name),
                    ('whatsapp', operator, name)] + args
        return self._search(args, limit=limit)


class MemberSubscription(models.Model):
    _name = 'charity.member.subscription'
    _description = 'اشتراكات العضوات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'subscription_number'
    _order = 'start_date desc'

    # رقم الاشتراك
    subscription_number = fields.Char(
        string='رقم الاشتراك',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: 'جديد',
        tracking=True
    )

    # العضوة
    member_id = fields.Many2one(
        'charity.member.profile',
        string='العضوة',
        required=True,
        ondelete='restrict',
        tracking=True
    )

    member_name = fields.Char(
        related='member_id.full_name',
        string='اسم العضوة',
        store=True
    )

    member_mobile = fields.Char(
        related='member_id.mobile',
        string='رقم الهاتف',
        store=True
    )

    # القسم والمقر
    headquarters_id = fields.Many2one(
        'charity.headquarters',
        string='المقر',
        required=True,
        tracking=True
    )

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',
        domain="[('headquarters_id', '=', headquarters_id), ('type', '=', 'ladies')]",
        required=True,
        tracking=True
    )

    # معلومات الاشتراك
    subscription_type = fields.Selection([
        ('annual', 'سنوي'),
        ('semi_annual', 'نصف سنوي'),
        ('quarterly', 'ربع سنوي'),
        ('monthly', 'شهري')
    ], string='نوع الاشتراك',
        default='annual',
        required=True,
        tracking=True
    )

    # التواريخ
    payment_date = fields.Datetime(
        string='تاريخ الدفع',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )

    start_date = fields.Date(
        string='تاريخ البداية',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    end_date = fields.Date(
        string='تاريخ النهاية',
        compute='_compute_end_date',
        store=True,
        tracking=True
    )

    days_remaining = fields.Integer(
        string='الأيام المتبقية',
        compute='_compute_days_remaining'
    )

    # المبالغ
    amount = fields.Float(
        string='مبلغ الاشتراك',
        required=True,
        tracking=True
    )

    # الحالة
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي')
    ], string='الحالة',
        default='draft',
        tracking=True
    )

    # معلومات إضافية
    notes = fields.Text(
        string='ملاحظات'
    )

    program_ids = fields.Many2many(
        'charity.ladies.program',
        'program_subscription_rel',
        'subscription_id',
        'program_id',
        string='البرامج المختارة',
        domain="[('department_id', '=', department_id), ('is_active', '=', True)]",
        help='البرامج المختارة في هذا الاشتراك'
    )

    programs_count = fields.Integer(
        string='عدد البرامج',
        compute='_compute_programs_count',
        help='عدد البرامج المختارة'
    )

    id_card_file = fields.Binary(
        string='صورة الهوية',
        attachment=True,
        help='صورة الهوية'
    )

    id_card_filename = fields.Char(
        string='اسم ملف الهوية'
    )

    passport_file = fields.Binary(
        string='صورة الباسبور',
        attachment=True,
        help='صورة جواز السفر'
    )

    passport_filename = fields.Char(
        string='اسم ملف الباسبور'
    )

    residence_file = fields.Binary(
        string='صورة الإقامة',
        attachment=True,
        help='صورة الإقامة'
    )

    residence_filename = fields.Char(
        string='اسم ملف الإقامة'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )



    @api.model
    def create(self, vals):
        """إنشاء رقم اشتراك تلقائي"""
        if vals.get('subscription_number', 'جديد') == 'جديد':
            vals['subscription_number'] = self.env['ir.sequence'].next_by_code('charity.member.subscription') or 'جديد'
        return super(MemberSubscription, self).create(vals)

    @api.depends('start_date', 'subscription_type')
    def _compute_end_date(self):
        """حساب تاريخ نهاية الاشتراك"""
        for record in self:
            if record.start_date:
                if record.subscription_type == 'annual':
                    record.end_date = record.start_date + relativedelta(years=1)
                elif record.subscription_type == 'semi_annual':
                    record.end_date = record.start_date + relativedelta(months=6)
                elif record.subscription_type == 'quarterly':
                    record.end_date = record.start_date + relativedelta(months=3)
                elif record.subscription_type == 'monthly':
                    record.end_date = record.start_date + relativedelta(months=1)
            else:
                record.end_date = False

    @api.depends('end_date')
    def _compute_days_remaining(self):
        """حساب الأيام المتبقية"""
        today = fields.Date.today()
        for record in self:
            if record.end_date and record.state == 'active':
                delta = record.end_date - today
                record.days_remaining = delta.days if delta.days > 0 else 0
            else:
                record.days_remaining = 0

    @api.onchange('headquarters_id')
    def _onchange_headquarters_id(self):
        """تحديث domain القسم عند تغيير المقر"""
        if self.headquarters_id:
            self.department_id = False
            return {
                'domain': {
                    'department_id': [
                        ('headquarters_id', '=', self.headquarters_id.id),
                        ('type', '=', 'ladies')
                    ]
                }
            }

    @api.depends('program_ids')
    def _compute_programs_count(self):
        """حساب عدد البرامج المختارة"""
        for record in self:
            record.programs_count = len(record.program_ids)

    @api.constrains('program_ids')
    def _check_programs_capacity(self):
        """التحقق من توفر مقاعد في البرامج المختارة"""
        for record in self:
            if record.state == 'active':
                for program in record.program_ids:
                    if program.available_seats <= 0:
                        raise ValidationError(
                            f'البرنامج "{program.name}" ممتلئ ولا يمكن التسجيل فيه!'
                        )

    @api.constrains('department_id', 'program_ids')
    def _check_programs_department(self):
        """التحقق من أن جميع البرامج تنتمي لنفس القسم"""
        for record in self:
            if record.program_ids:
                invalid_programs = record.program_ids.filtered(
                    lambda p: p.department_id != record.department_id
                )
                if invalid_programs:
                    raise ValidationError(
                        'جميع البرامج يجب أن تكون من نفس القسم!'
                    )

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """تحديث السعر من القسم"""
        if self.department_id and self.department_id.booking_price:
            self.amount = self.department_id.booking_price

    @api.constrains('member_id', 'department_id', 'state')
    def _check_duplicate_active_subscription(self):
        """منع الاشتراكات المكررة النشطة"""
        for record in self:
            if record.state == 'active':
                duplicate = self.search([
                    ('member_id', '=', record.member_id.id),
                    ('department_id', '=', record.department_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f'العضوة {record.member_id.full_name} لديها اشتراك نشط بالفعل في {record.department_id.name}!'
                    )

    def action_confirm(self):
        """تأكيد الاشتراك"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'confirmed'

    def action_activate(self):
        """تفعيل الاشتراك"""
        self.ensure_one()
        if self.state == 'confirmed':
            # التحقق من وجود فاتورة مدفوعة
            booking = self.env['charity.booking.registrations'].search([
                ('subscription_id', '=', self.id),
                ('invoice_payment_state', '=', 'paid')
            ], limit=1)

            if booking or self._context.get('force_activate'):
                self.state = 'active'
            else:
                raise ValidationError('لا يمكن تفعيل الاشتراك قبل دفع الفاتورة!')
    def action_cancel(self):
        """إلغاء الاشتراك"""
        self.ensure_one()
        if self.state in ('draft', 'confirmed'):
            self.state = 'cancelled'

    def action_renew(self):
        """تجديد الاشتراك"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'تجديد الاشتراك',
            'view_mode': 'form',
            'res_model': 'charity.member.subscription',
            'target': 'new',
            'context': {
                'default_member_id': self.member_id.id,
                'default_headquarters_id': self.headquarters_id.id,
                'default_department_id': self.department_id.id,
                'default_start_date': self.end_date + relativedelta(days=1) if self.end_date else fields.Date.today(),
                'default_subscription_type': self.subscription_type,
                'default_amount': self.amount
            }
        }

    @api.model
    def _check_expired_subscriptions(self):
        """Cron job للتحقق من الاشتراكات المنتهية"""
        today = fields.Date.today()
        expired = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        expired.write({'state': 'expired'})

    def name_get(self):
        """تخصيص طريقة عرض اسم الاشتراك"""
        result = []
        for record in self:
            name = f"{record.subscription_number} - {record.member_name}"
            result.append((record.id, name))
        return result
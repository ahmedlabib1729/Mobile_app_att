# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BookingRegistrations(models.Model):
    _name = 'charity.booking.registrations'
    _description = 'حجوزات الأقسام'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'create_date desc'

    # حقل العرض
    display_name = fields.Char(
        string='اسم الحجز',
        compute='_compute_display_name',
        store=True
    )

    # نوع الحجز
    booking_type = fields.Selection([
        ('new', 'عضوة جديدة'),
        ('existing', 'عضوة مسجلة')
    ], string='نوع الحجز',
        default='new',
        tracking=True,
        help='حدد ما إذا كانت عضوة جديدة أو مسجلة سابقاً'
    )

    # العضوة المسجلة (للسيدات)
    member_id = fields.Many2one(
        'charity.member.profile',
        string='العضوة',
        tracking=True,
        help='اختر العضوة المسجلة سابقاً'
    )

    # معلومات المستفيد
    full_name = fields.Char(
        string='الاسم الثلاثي',
        tracking=True,
        help='أدخل الاسم الثلاثي'
    )

    mobile = fields.Char(
        string='رقم التواصل',
        tracking=True,
        help='رقم الهاتف للتواصل'
    )

    whatsapp = fields.Char(
        string='رقم الواتساب',
        help='رقم الواتساب للتواصل'
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        help='تاريخ الميلاد'
    )

    email = fields.Char(
        string='البريد الإلكتروني',
        help='البريد الإلكتروني للتواصل'
    )

    # حقول الحجز
    headquarters_id = fields.Many2one(
        'charity.headquarters',
        string='المقر',
        required=True,
        tracking=True,
        help='اختر المقر'
    )

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',
        domain="[('headquarters_id', '=', headquarters_id), ('type', 'in', ['ladies'])]",
        required=True,
        tracking=True,
        help='اختر القسم'
    )

    department_type = fields.Selection(
        related='department_id.type',
        string='نوع القسم',
        store=True
    )

    department_booking_price = fields.Float(
        string='سعر القسم',
        related='department_id.booking_price',
        readonly=True,
        help='سعر الحجز للقسم'
    )

    # معلومات إضافية
    registration_date = fields.Datetime(
        string='تاريخ إنشاء الحجز',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي')
    ], string='الحالة',
        default='draft',
        tracking=True,
        help='حالة الحجز'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    # العمر المحسوب
    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True,
        help='العمر المحسوب من تاريخ الميلاد'
    )

    # الاشتراك المرتبط (للسيدات)
    subscription_id = fields.Many2one(
        'charity.member.subscription',
        string='الاشتراك',
        readonly=True,
        help='الاشتراك المرتبط بهذا الحجز'
    )

    @api.depends('full_name', 'department_id')
    def _compute_display_name(self):
        """حساب اسم العرض"""
        for record in self:
            if record.full_name and record.department_id:
                record.display_name = f"{record.full_name} - {record.department_id.name}"
            elif record.full_name:
                record.display_name = record.full_name
            else:
                record.display_name = "حجز جديد"

    @api.depends('birth_date', 'member_id')
    def _compute_age(self):
        """حساب العمر من تاريخ الميلاد"""
        from datetime import date
        from dateutil.relativedelta import relativedelta

        today = date.today()
        for record in self:
            birth_date = record.birth_date
            if record.booking_type == 'existing' and record.member_id:
                birth_date = record.member_id.birth_date

            if birth_date:
                age = relativedelta(today, birth_date)
                record.age = age.years
            else:
                record.age = 0

    @api.onchange('booking_type')
    def _onchange_booking_type(self):
        """تنظيف الحقول عند تغيير نوع الحجز"""
        if self.booking_type == 'new':
            self.member_id = False
        else:
            self.full_name = False
            self.mobile = False
            self.whatsapp = False
            self.birth_date = False
            self.email = False

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """ملء البيانات من ملف العضوة"""
        if self.booking_type == 'existing' and self.member_id:
            self.full_name = self.member_id.full_name
            self.birth_date = self.member_id.birth_date
            self.mobile = self.member_id.mobile
            self.whatsapp = self.member_id.whatsapp
            self.email = self.member_id.email

    @api.onchange('headquarters_id')
    def _onchange_headquarters_id(self):
        """تحديث domain الأقسام عند تغيير المقر"""
        if self.headquarters_id:
            self.department_id = False
            return {
                'domain': {
                    'department_id': [
                        ('headquarters_id', '=', self.headquarters_id.id),
                        ('type', 'in', ['ladies', 'nursery'])
                    ]
                }
            }

    def action_search_or_create_member(self):
        """البحث عن عضوة موجودة أو إنشاء جديدة"""
        self.ensure_one()

        # هذه الوظيفة خاصة بأقسام السيدات فقط
        if self.department_type != 'ladies':
            return {'type': 'ir.actions.do_nothing'}

        if self.booking_type != 'new' or not self.mobile:
            return {'type': 'ir.actions.do_nothing'}

        # البحث عن عضوة موجودة بنفس رقم الهاتف
        existing_member = self.env['charity.member.profile'].search([
            '|',
            ('mobile', '=', self.mobile),
            ('whatsapp', '=', self.whatsapp)
        ], limit=1)

        if existing_member:
            # عضوة موجودة
            self.booking_type = 'existing'
            self.member_id = existing_member

            # التحقق من وجود اشتراك نشط
            active_sub = self.env['charity.member.subscription'].search([
                ('member_id', '=', existing_member.id),
                ('department_id', '=', self.department_id.id),
                ('state', '=', 'active')
            ], limit=1)

            if active_sub:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'تنبيه',
                        'message': f'العضوة {existing_member.full_name} لديها اشتراك نشط ينتهي في {active_sub.end_date}',
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'تم العثور على العضوة',
                        'message': f'العضوة {existing_member.full_name} موجودة في النظام',
                        'type': 'info',
                        'sticky': False,
                    }
                }

        return {'type': 'ir.actions.do_nothing'}

    def _create_member_and_subscription(self):
        """إنشاء ملف عضوة واشتراك جديد"""
        self.ensure_one()

        if self.booking_type != 'new' or self.department_type != 'ladies':
            return False

        # إنشاء ملف العضوة
        member_vals = {
            'full_name': self.full_name,
            'birth_date': self.birth_date,
            'mobile': self.mobile,
            'whatsapp': self.whatsapp,
            'email': self.email,
        }
        member = self.env['charity.member.profile'].create(member_vals)

        # إنشاء الاشتراك
        subscription_vals = {
            'member_id': member.id,
            'headquarters_id': self.headquarters_id.id,
            'department_id': self.department_id.id,
            'amount': self.department_booking_price,
            'state': 'confirmed'
        }
        subscription = self.env['charity.member.subscription'].create(subscription_vals)

        # ربط الحجز بالعضوة والاشتراك
        self.booking_type = 'existing'
        self.member_id = member
        self.subscription_id = subscription

        return True

    def _validate_required_fields(self):
        """التحقق من الحقول المطلوبة"""
        for record in self:
            if record.booking_type == 'new':
                if not record.full_name:
                    raise ValidationError('يجب إدخال الاسم الثلاثي!')
                if not record.birth_date:
                    raise ValidationError('يجب إدخال تاريخ الميلاد!')
                if not record.mobile:
                    raise ValidationError('يجب إدخال رقم التواصل!')
                if record.department_type == 'ladies' and not record.whatsapp:
                    raise ValidationError('يجب إدخال رقم الواتساب!')
            elif record.booking_type == 'existing' and record.department_type == 'ladies':
                if not record.member_id:
                    raise ValidationError('يجب اختيار العضوة!')

    @api.constrains('mobile', 'whatsapp')
    def _check_phone_numbers(self):
        """التحقق من صحة أرقام الهواتف"""
        import re
        phone_pattern = re.compile(r'^[\d\s\-\+]+$')

        for record in self:
            if record.booking_type == 'new':
                if record.mobile and not phone_pattern.match(record.mobile):
                    raise ValidationError('رقم التواصل غير صحيح!')
                if record.whatsapp and not phone_pattern.match(record.whatsapp):
                    raise ValidationError('رقم الواتساب غير صحيح!')

    @api.constrains('email')
    def _check_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for record in self:
            if record.booking_type == 'new' and record.email and not email_pattern.match(record.email):
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    @api.constrains('birth_date')
    def _check_birth_date(self):
        """التحقق من صحة تاريخ الميلاد"""
        from datetime import date
        for record in self:
            if record.booking_type == 'new' and record.birth_date:
                if record.birth_date > date.today():
                    raise ValidationError('تاريخ الميلاد لا يمكن أن يكون في المستقبل!')

    @api.constrains('department_id')
    def _check_department_type(self):
        """التحقق من أن القسم من نوع سيدات أو حضانة"""
        for record in self:
            if record.department_id and record.department_id.type not in ['ladies']:
                raise ValidationError('يجب اختيار قسم من نوع سيدات أو حضانة!')

    def action_confirm(self):
        """تأكيد الحجز"""
        self.ensure_one()
        if self.state == 'draft':
            self._validate_required_fields()

            # إنشاء ملف العضوة والاشتراك إذا كان حجز جديد لقسم السيدات
            if self.booking_type == 'new' and self.department_type == 'ladies':
                self._create_member_and_subscription()
            elif self.booking_type == 'existing' and self.member_id and not self.subscription_id and self.department_type == 'ladies':
                # إنشاء اشتراك جديد للعضوة الموجودة
                subscription_vals = {
                    'member_id': self.member_id.id,
                    'headquarters_id': self.headquarters_id.id,
                    'department_id': self.department_id.id,
                    'amount': self.department_booking_price,
                    'state': 'confirmed'
                }
                subscription = self.env['charity.member.subscription'].create(subscription_vals)
                self.subscription_id = subscription

            self.state = 'confirmed'

    def action_approve(self):
        """اعتماد الحجز"""
        self.ensure_one()
        if self.state == 'confirmed':
            # تفعيل الاشتراك للسيدات
            if self.subscription_id and self.subscription_id.state == 'confirmed':
                self.subscription_id.action_activate()
            self.state = 'approved'

    def action_reject(self):
        """رفض الحجز"""
        self.ensure_one()
        if self.state in ('draft', 'confirmed'):
            # إلغاء الاشتراك إذا كان موجود
            if self.subscription_id and self.subscription_id.state != 'active':
                self.subscription_id.action_cancel()
            self.state = 'rejected'

    def action_cancel(self):
        """إلغاء الحجز"""
        self.ensure_one()
        if self.state != 'approved':
            # إلغاء الاشتراك إذا كان موجود
            if self.subscription_id and self.subscription_id.state != 'active':
                self.subscription_id.action_cancel()
            self.state = 'cancelled'

    def action_reset_draft(self):
        """إعادة الحجز إلى مسودة"""
        self.ensure_one()
        self.state = 'draft'

    def action_view_subscription(self):
        """عرض الاشتراك المرتبط"""
        self.ensure_one()
        if not self.subscription_id:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'الاشتراك',
            'view_mode': 'form',
            'res_model': 'charity.member.subscription',
            'res_id': self.subscription_id.id,
            'target': 'current',
        }

    def action_view_member(self):
        """عرض ملف العضوة"""
        self.ensure_one()
        if not self.member_id:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'ملف العضوة',
            'view_mode': 'form',
            'res_model': 'charity.member.profile',
            'res_id': self.member_id.id,
            'target': 'current',
        }

    def name_get(self):
        """تخصيص طريقة عرض اسم الحجز"""
        result = []
        for record in self:
            result.append((record.id, record.display_name))
        return result
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NurseryChildRegistration(models.Model):
    _name = 'nursery.child.registration'
    _description = 'تسجيل طفل الحضانة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'child_full_name'

    # حقل محسوب للاسم الكامل
    child_full_name = fields.Char(
        string='اسم الطفل',
        compute='_compute_child_full_name',
        store=True
    )

    # بيانات الطفل
    first_name = fields.Char(string='الاسم الأول', required=True, tracking=True)
    father_name = fields.Char(string='اسم الأب', required=True, tracking=True)
    birth_date = fields.Date(string='تاريخ الميلاد', required=True, tracking=True)
    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس', required=True, tracking=True)
    family_name = fields.Char(string='العائلة', required=True, tracking=True)
    religion = fields.Char(string='الديانة', required=True)
    nationality = fields.Many2one('res.country', string='الجنسية', required=True)
    mother_language = fields.Char(string='اللغة الأم', required=True)
    passport_number = fields.Char(string='رقم جواز السفر')
    identity_number = fields.Char(string='رقم الهوية')

    # بيانات الأخوة المسجلين
    has_siblings = fields.Boolean(string='له أخوة مسجلين')
    sibling_ids = fields.One2many('nursery.child.sibling', 'registration_id', string='الأخوة المسجلين')

    # بيانات الأم
    mother_name = fields.Char(string='اسم الأم', required=True)
    mother_nationality = fields.Many2one('res.country', string='جنسية الأم', required=True)
    mother_job = fields.Char(string='مهنة الأم')
    mother_company = fields.Char(string='شركة الأم')
    mother_mobile = fields.Char(string='هاتف الأم المتحرك', required=True)
    mother_phone = fields.Char(string='هاتف الأم الثابت')
    mother_email = fields.Char(string='بريد الأم الإلكتروني')
    home_address = fields.Text(string='عنوان السكن', required=True)

    # بيانات الأب
    father_full_name = fields.Char(string='اسم الأب الكامل', required=True)
    father_nationality = fields.Many2one('res.country', string='جنسية الأب', required=True)
    father_job = fields.Char(string='مهنة الأب')
    father_company = fields.Char(string='شركة الأب')
    father_mobile = fields.Char(string='هاتف الأب المتحرك', required=True)
    father_phone = fields.Char(string='هاتف الأب الثابت')
    father_email = fields.Char(string='بريد الأب الإلكتروني')

    # التواصل في حالة الطوارئ
    emergency_contact_ids = fields.One2many('nursery.emergency.contact', 'registration_id', string='جهات الطوارئ')

    # معلومات التسجيل
    join_date = fields.Date(string='تاريخ الإلتحاق', required=True, default=fields.Date.today)
    department_id = fields.Many2one('charity.departments', string='القسم', domain=[('type', '=', 'nursery')],
                                    required=True)
    nursery_plan_id = fields.Many2one('charity.nursery.plan', string='الدوام', required=True)

    # التأكيد
    confirm_info = fields.Boolean(string='أؤكد أن جميع المعلومات صحيحة وعلى مسؤوليتي', required=True)

    # كيف تعرفت علينا
    how_know_us = fields.Selection([
        ('instagram', 'إنستغرام'),
        ('facebook', 'فيس بوك'),
        ('google', 'جوجل'),
        ('people', 'أشخاص'),
        ('other', 'أخرى')
    ], string='كيف تعرفت على حضانة رؤيتي؟', required=True)

    # حالة التسجيل
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('confirmed', 'مؤكد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض')
    ], string='الحالة', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='الشركة', default=lambda self: self.env.company)

    registration_type = fields.Selection([
        ('new', 'طفل جديد'),
        ('existing', 'طفل مسجل')
    ], string='نوع التسجيل', default='new', required=True)

    # ملف الطفل
    child_profile_id = fields.Many2one(
        'nursery.child.profile',
        string='ملف الطفل',
        ondelete='restrict'
    )

    attendance_days = fields.Selection([
        ('3', '3 أيام'),
        ('4', '4 أيام'),
        ('5', '5 أيام')
    ], string='عدد أيام الحضور', required=True, default='5')

    # السعر المحسوب
    registration_price = fields.Float(
        string='رسوم التسجيل',
        compute='_compute_registration_price',
        store=True,
        digits=(10, 2)
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='الفاتورة',
        readonly=True,
        copy=False
    )

    @api.depends('nursery_plan_id', 'attendance_days')
    def _compute_registration_price(self):
        for record in self:
            if record.nursery_plan_id and record.attendance_days:
                if record.attendance_days == '5':
                    record.registration_price = record.nursery_plan_id.price_5_days
                elif record.attendance_days == '4':
                    record.registration_price = record.nursery_plan_id.price_4_days
                elif record.attendance_days == '3':
                    record.registration_price = record.nursery_plan_id.price_3_days
                else:
                    record.registration_price = 0.0
            else:
                record.registration_price = 0.0

    @api.onchange('registration_type')
    def _onchange_registration_type(self):
        """تنظيف الحقول عند تغيير نوع التسجيل"""
        if self.registration_type == 'existing':
            # مسح بيانات الطفل اليدوية
            self.first_name = False
            self.father_name = False
            self.family_name = False
            self.birth_date = False
            self.gender = False
            self.passport_number = False
            self.identity_number = False
        else:
            self.child_profile_id = False

    @api.onchange('child_profile_id')
    def _onchange_child_profile_id(self):
        """ملء البيانات من ملف الطفل"""
        if self.child_profile_id:
            self.first_name = self.child_profile_id.first_name
            self.father_name = self.child_profile_id.father_name
            self.family_name = self.child_profile_id.family_name
            self.birth_date = self.child_profile_id.birth_date
            self.gender = self.child_profile_id.gender
            self.passport_number = self.child_profile_id.passport_number
            self.identity_number = self.child_profile_id.identity_number

    @api.onchange('identity_number', 'passport_number')
    def _onchange_check_existing_child(self):
        """البحث عن طفل موجود عند إدخال رقم الهوية أو الجواز"""
        if self.registration_type == 'new':
            existing_child = False

            # البحث برقم الهوية
            if self.identity_number:
                existing_child = self.env['nursery.child.profile'].search([
                    ('identity_number', '=', self.identity_number)
                ], limit=1)

            # البحث برقم الجواز إذا لم نجد برقم الهوية
            if not existing_child and self.passport_number:
                existing_child = self.env['nursery.child.profile'].search([
                    ('passport_number', '=', self.passport_number)
                ], limit=1)

            if existing_child:
                return {
                    'warning': {
                        'title': 'طفل موجود',
                        'message': f'الطفل {existing_child.full_name} موجود بالفعل في النظام. هل تريد استخدام ملفه الموجود؟'
                    }
                }

    def action_confirm(self):
        """تأكيد التسجيل وإنشاء ملف الطفل إذا كان جديد"""
        self.ensure_one()

        # التحقق من البيانات المطلوبة
        if self.registration_type == 'new':
            if not all([self.first_name, self.father_name, self.family_name,
                        self.birth_date, self.gender, self.identity_number]):
                raise ValidationError('يجب ملء جميع البيانات الأساسية للطفل!')
        elif self.registration_type == 'existing':
            if not self.child_profile_id:
                raise ValidationError('يجب اختيار الطفل المسجل!')

        # إنشاء ملف طفل جديد إذا لم يكن موجود
        if self.registration_type == 'new' and not self.child_profile_id:
            # التحقق مرة أخرى من عدم وجود طفل بنفس الوثائق
            domain = []
            if self.identity_number:
                domain.append(('identity_number', '=', self.identity_number))
            if self.passport_number:
                if domain:
                    domain = ['|'] + domain + [('passport_number', '=', self.passport_number)]
                else:
                    domain = [('passport_number', '=', self.passport_number)]

            if domain:
                existing_child = self.env['nursery.child.profile'].search(domain, limit=1)

                if existing_child:
                    # إعطاء خيار للمستخدم
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'طفل موجود',
                        'res_model': 'nursery.registration.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_registration_id': self.id,
                            'default_child_profile_id': existing_child.id,
                            'default_message': f'الطفل {existing_child.full_name} موجود بالفعل في النظام. هل تريد ربط هذا التسجيل بالطفل الموجود؟'
                        }
                    }

            # إنشاء ملف جديد
            child_vals = {
                'first_name': self.first_name,
                'father_name': self.father_name,
                'family_name': self.family_name,
                'birth_date': self.birth_date,
                'gender': self.gender,
                'passport_number': self.passport_number,
                'identity_number': self.identity_number
            }
            self.child_profile_id = self.env['nursery.child.profile'].create(child_vals)

        # التحقق من عدم وجود تسجيل نشط آخر لنفس الطفل في نفس القسم
        existing_registration = self.search([
            ('child_profile_id', '=', self.child_profile_id.id),
            ('department_id', '=', self.department_id.id),
            ('state', 'in', ['confirmed', 'approved']),
            ('id', '!=', self.id)
        ])

        if existing_registration:
            raise ValidationError(
                f'الطفل {self.child_profile_id.full_name} لديه تسجيل نشط بالفعل في قسم {self.department_id.name}!'
            )

        # تغيير الحالة
        self.state = 'confirmed'

        # إرسال رسالة في الشات
        self.message_post(
            body=f'تم تأكيد تسجيل الطفل {self.child_profile_id.full_name}',
            message_type='notification'
        )

    @api.depends('first_name', 'father_name', 'family_name')
    def _compute_child_full_name(self):
        for record in self:
            names = [record.first_name, record.father_name, record.family_name]
            record.child_full_name = ' '.join(filter(None, names))

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.nursery_plan_id = False
            return {
                'domain': {
                    'nursery_plan_id': [('department_id', '=', self.department_id.id)]
                }
            }

    @api.constrains('confirm_info')
    def _check_confirm_info(self):
        for record in self:
            if not record.confirm_info:
                raise ValidationError('يجب تأكيد صحة المعلومات قبل الحفظ!')

    def action_confirm(self):
        """تأكيد التسجيل وإنشاء ملف الطفل إذا كان جديد"""
        self.ensure_one()

        # إنشاء ملف طفل جديد إذا لم يكن موجود
        if self.registration_type == 'new' and not self.child_profile_id:
            # التحقق مرة أخرى من عدم وجود طفل بنفس الوثائق
            existing_child = self.env['nursery.child.profile'].search([
                '|',
                ('identity_number', '=', self.identity_number),
                ('passport_number', '=', self.passport_number)
            ], limit=1)

            if existing_child:
                self.child_profile_id = existing_child
                self.registration_type = 'existing'
            else:
                # إنشاء ملف جديد
                child_vals = {
                    'first_name': self.first_name,
                    'father_name': self.father_name,
                    'family_name': self.family_name,
                    'birth_date': self.birth_date,
                    'gender': self.gender,
                    'passport_number': self.passport_number,
                    'identity_number': self.identity_number
                }
                self.child_profile_id = self.env['nursery.child.profile'].create(child_vals)

        # استكمال عملية التأكيد
        self.state = 'confirmed'

    def action_approve(self):
        self.ensure_one()
        self.state = 'approved'
        # إنشاء الفاتورة بعد الاعتماد
        self._create_invoice()

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'

    def action_reset_draft(self):
        self.ensure_one()
        self.state = 'draft'

    def _create_invoice(self):
        """إنشاء فاتورة للتسجيل"""
        self.ensure_one()

        # التحقق من عدم وجود فاتورة سابقة
        if self.invoice_id:
            return

        # البحث عن شريك (partner) للأب أو إنشاء واحد جديد
        partner_obj = self.env['res.partner']

        # البحث بالايميل أولاً
        partner = False
        if self.father_email:
            partner = partner_obj.search([
                ('email', '=', self.father_email),
                ('is_company', '=', False)
            ], limit=1)

        # البحث بالموبايل إذا لم نجد بالايميل
        if not partner and self.father_mobile:
            partner = partner_obj.search([
                ('mobile', '=', self.father_mobile),
                ('is_company', '=', False)
            ], limit=1)

        # إنشاء شريك جديد إذا لم نجد
        if not partner:
            partner_vals = {
                'name': self.father_full_name,
                'is_company': False,
                'email': self.father_email,
                'mobile': self.father_mobile,
                'phone': self.father_phone,
                'street': self.home_address,
                'customer_rank': 1,
            }
            partner = partner_obj.create(partner_vals)

        # تحضير بيانات الفاتورة
        invoice_vals = {
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'currency_id': self.env.company.currency_id.id,
            'invoice_line_ids': []
        }

        # تحضير سطر الفاتورة
        line_name = f"تسجيل {self.child_full_name} - {self.department_id.name} - {dict(self._fields['attendance_days'].selection).get(self.attendance_days)}"

        invoice_line_vals = {
            'name': line_name,
            'quantity': 1.0,
            'price_unit': self.registration_price,
        }

        invoice_vals['invoice_line_ids'] = [(0, 0, invoice_line_vals)]

        # إنشاء الفاتورة
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice

        # إضافة رسالة في الشات
        self.message_post(
            body=f'تم إنشاء الفاتورة رقم {invoice.name} بمبلغ {self.registration_price}',
            message_type='notification'
        )

        return invoice
    def action_view_invoice(self):
        """فتح الفاتورة المرتبطة"""
        self.ensure_one()
        if not self.invoice_id:
            raise ValidationError('لا توجد فاتورة مرتبطة بهذا التسجيل')

        return {
            'type': 'ir.actions.act_window',
            'name': 'الفاتورة',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class NurseryChildSibling(models.Model):
    _name = 'nursery.child.sibling'
    _description = 'أخوة الطفل المسجلين'

    registration_id = fields.Many2one('nursery.child.registration', string='التسجيل', required=True, ondelete='cascade')
    sibling_name = fields.Char(string='اسم الأخ/الأخت', required=True)
    sibling_age = fields.Integer(string='العمر')
    sibling_class = fields.Char(string='الصف')


class NurseryEmergencyContact(models.Model):
    _name = 'nursery.emergency.contact'
    _description = 'جهات الطوارئ'

    registration_id = fields.Many2one('nursery.child.registration', string='التسجيل', required=True, ondelete='cascade')
    person_name = fields.Char(string='اسم الشخص', required=True)
    mobile = fields.Char(string='الهاتف المتحرك', required=True)
    relationship = fields.Char(string='صلة القرابة', required=True)


class NurseryRegistrationWizard(models.TransientModel):
    _name = 'nursery.registration.wizard'
    _description = 'معالج تسجيل الحضانة'

    registration_id = fields.Many2one('nursery.child.registration', string='التسجيل')
    child_profile_id = fields.Many2one('nursery.child.profile', string='ملف الطفل')
    message = fields.Text(string='رسالة', readonly=True)

    def action_use_existing(self):
        """استخدام الطفل الموجود"""
        self.registration_id.child_profile_id = self.child_profile_id
        self.registration_id.registration_type = 'existing'
        return self.registration_id.action_confirm()

    def action_create_new(self):
        """إنشاء طفل جديد"""
        # إلغاء ربط الطفل الموجود
        self.registration_id.child_profile_id = False
        # المتابعة مع إنشاء طفل جديد
        return self.registration_id.action_confirm()
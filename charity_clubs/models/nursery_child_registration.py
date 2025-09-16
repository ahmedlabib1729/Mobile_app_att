# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)


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

    # بعد حقل family_name أضف:
    child_order = fields.Integer(string='ترتيب الطفل بين إخوته', required=True)

    # بعد حقل father_company أضف:
    father_education_level = fields.Selection([
        ('high_school', 'دبلوم'),
        ('higher_diploma', 'دبلوم عالي'),
        ('bachelor', 'بكالوريوس'),
        ('master', 'ماجستير'),
        ('phd', 'دكتوراه')
    ], string='المستوى التعليمي للأب/ولي الأمر', required=True)

    father_work_status = fields.Selection([
        ('employee', 'موظف'),
        ('self_employed', 'عامل لحسابه الخاص'),
        ('not_working', 'لا يعمل')
    ], string='حالة عمل الأب/ولي الأمر', required=True)

    nursery_class_id = fields.Many2one(
        'nursery.class.config',
        string='صف الحضانة',
        compute='_compute_nursery_class',
        store=True,
        readonly=True
    )

    child_age_display = fields.Char(
        string='عمر الطفل',
        compute='_compute_child_age',
        store=False
    )

    child_id_front = fields.Binary(
        string='هوية الطفل - الوجه الأمامي',
        attachment=True,

    )
    child_id_front_filename = fields.Char(string='اسم ملف الوجه الأمامي')

    child_id_back = fields.Binary(
        string='هوية الطفل - الوجه الخلفي',
        attachment=True,

    )
    child_id_back_filename = fields.Char(string='اسم ملف الوجه الخلفي')

    guardian_id_front = fields.Binary(
        string='هوية ولي الأمر - الوجه الأمامي',
        attachment=True,

    )
    guardian_id_front_filename = fields.Char(string='اسم ملف الوجه الأمامي لولي الأمر')

    guardian_id_back = fields.Binary(
        string='هوية ولي الأمر - الوجه الخلفي',
        attachment=True,

    )
    guardian_id_back_filename = fields.Char(string='اسم ملف الوجه الخلفي لولي الأمر')

    payment_type = fields.Selection([
        ('full', 'دفعة واحدة'),
        ('installments', 'أقساط')
    ], string='طريقة السداد', default='full', required=True)

    installments_count = fields.Integer(
        string='عدد الأقساط',
        default=1,
        help='عدد الأقساط (1-12)'
    )

    payment_method = fields.Selection([
        ('cash', 'نقدي'),
        ('bank', 'تحويل بنكي'),
        ('cheque', 'شيكات'),
        ('mixed', 'مختلط')
    ], string='وسيلة الدفع', default='cash')

    installment_amount = fields.Float(
        string='قيمة القسط',
        compute='_compute_installment_amount',
        store=True,
        digits=(10, 2)
    )

    # حقول الفواتير
    registration_fee_invoice_id = fields.Many2one(
        'account.move',
        string='فاتورة رسوم التسجيل',
        readonly=True
    )

    # One2many للأقساط
    payment_schedule_ids = fields.One2many(
        'nursery.payment.schedule',
        'registration_id',
        string='جدول الأقساط'
    )

    discount_type = fields.Selection([
        ('none', 'بدون خصم'),
        ('percentage', 'خصم بالنسبة المئوية'),
        ('amount', 'خصم بالمبلغ')
    ], string='نوع الخصم', default='none')

    discount_percentage = fields.Float(
        string='نسبة الخصم (%)',
        digits=(5, 2),
        help='نسبة الخصم من 0 إلى 100'
    )

    discount_amount = fields.Float(
        string='مبلغ الخصم',
        digits=(10, 2)
    )

    # السعر بعد الخصم
    final_price = fields.Float(
        string='السعر النهائي بعد الخصم',
        compute='_compute_final_price',
        store=True,
        digits=(10, 2)
    )

    total_discount = fields.Float(
        string='إجمالي الخصم',
        compute='_compute_final_price',
        store=True,
        digits=(10, 2)
    )

    @api.depends('registration_price', 'discount_type', 'discount_percentage', 'discount_amount')
    def _compute_final_price(self):
        for record in self:
            if record.discount_type == 'none':
                record.final_price = record.registration_price
                record.total_discount = 0.0
            elif record.discount_type == 'percentage':
                discount = record.registration_price * (record.discount_percentage / 100)
                record.total_discount = discount
                record.final_price = record.registration_price - discount
            elif record.discount_type == 'amount':
                record.total_discount = min(record.discount_amount, record.registration_price)
                record.final_price = record.registration_price - record.total_discount
            else:
                record.final_price = record.registration_price
                record.total_discount = 0.0

            _logger.info(f"Computed final price for registration {record.id}: "
                         f"original={record.registration_price}, discount={record.total_discount}, "
                         f"final={record.final_price}")

    @api.depends('final_price', 'payment_type', 'installments_count')
    def _compute_installment_amount(self):
        for record in self:
            if record.payment_type == 'installments' and record.installments_count > 0:
                record.installment_amount = record.final_price / record.installments_count
            else:
                record.installment_amount = record.final_price

            _logger.info(f"Computed installment_amount for registration {record.id}: "
                         f"final_price={record.final_price}, count={record.installments_count}, "
                         f"per installment={record.installment_amount}")

    @api.constrains('discount_percentage')
    def _check_discount_percentage(self):
        for record in self:
            if record.discount_type == 'percentage':
                if record.discount_percentage < 0 or record.discount_percentage > 100:
                    raise ValidationError('نسبة الخصم يجب أن تكون بين 0 و 100!')

    @api.constrains('discount_amount')
    def _check_discount_amount(self):
        for record in self:
            if record.discount_type == 'amount':
                if record.discount_amount < 0:
                    raise ValidationError('مبلغ الخصم لا يمكن أن يكون سالباً!')
                if record.discount_amount > record.registration_price:
                    raise ValidationError('مبلغ الخصم لا يمكن أن يكون أكبر من سعر التسجيل!')

    @api.onchange('discount_type')
    def _onchange_discount_type(self):
        if self.discount_type == 'none':
            self.discount_percentage = 0
            self.discount_amount = 0
        elif self.discount_type == 'percentage':
            self.discount_amount = 0
        elif self.discount_type == 'amount':
            self.discount_percentage = 0

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type == 'full':
            self.installments_count = 1
        elif self.payment_type == 'installments' and self.installments_count < 2:
            self.installments_count = 3  # افتراضي 3 أقساط

    @api.constrains('installments_count', 'payment_type')
    def _check_installments_count(self):
        for record in self:
            if record.payment_type == 'installments':
                if record.installments_count < 2 or record.installments_count > 12:
                    raise ValidationError('عدد الأقساط يجب أن يكون بين 2 و 12!')

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

            _logger.info(f"Computed registration_price for registration {record.id}: {record.registration_price}")

    @api.depends('birth_date', 'department_id')
    def _compute_nursery_class(self):
        """تحديد صف الحضانة تلقائياً بناءً على تاريخ الميلاد"""
        for record in self:
            if record.birth_date and record.department_id:
                config_obj = self.env['nursery.class.config']
                eligible_configs = config_obj.check_child_eligibility(
                    record.birth_date,
                    record.department_id.id
                )
                if eligible_configs:
                    # اختيار أول صف مناسب
                    record.nursery_class_id = eligible_configs[0]
                else:
                    record.nursery_class_id = False

    @api.depends('birth_date')
    def _compute_child_age(self):
        """حساب عمر الطفل الحالي"""
        for record in self:
            if record.birth_date:
                today = fields.Date.today()
                age = today.year - record.birth_date.year
                # تعديل العمر إذا لم يصل لعيد ميلاده بعد
                if today.month < record.birth_date.month or \
                        (today.month == record.birth_date.month and today.day < record.birth_date.day):
                    age -= 1

                months = (today.year - record.birth_date.year) * 12 + today.month - record.birth_date.month
                if today.day < record.birth_date.day:
                    months -= 1

                years = months // 12
                remaining_months = months % 12

                if years > 0:
                    record.child_age_display = f"{years} سنة"
                    if remaining_months > 0:
                        record.child_age_display += f" و {remaining_months} شهر"
                else:
                    record.child_age_display = f"{remaining_months} شهر"
            else:
                record.child_age_display = ''

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
        """تأكيد التسجيل فقط - بدون إنشاء ملف الطفل"""
        self.ensure_one()

        _logger.info(f"Confirming registration {self.id}")

        # التحقق من البيانات المطلوبة
        if self.registration_type == 'new':
            if not all([self.first_name, self.father_name, self.family_name,
                        self.birth_date, self.gender, self.identity_number]):
                raise ValidationError('يجب ملء جميع البيانات الأساسية للطفل!')
        elif self.registration_type == 'existing':
            if not self.child_profile_id:
                raise ValidationError('يجب اختيار الطفل المسجل!')

        # التحقق من أهلية العمر
        birth_date = self.birth_date or (self.child_profile_id.birth_date if self.child_profile_id else False)

        if birth_date and self.department_id:
            config_obj = self.env['nursery.class.config']
            eligible_configs = config_obj.check_child_eligibility(
                birth_date,
                self.department_id.id
            )

            if not eligible_configs:
                today = fields.Date.today()
                age_days = (today - birth_date).days
                age_years = age_days // 365
                age_months = (age_days % 365) // 30

                raise ValidationError(
                    f'عمر الطفل ({age_years} سنة و {age_months} شهر) '
                    f'غير مناسب للتسجيل في أي من صفوف الحضانة المتاحة حالياً.\n'
                    f'يرجى التحقق من تكوين صفوف الحضانة أو الانتظار حتى يصبح الطفل في العمر المناسب.'
                )

        # فقط التحقق من عدم وجود تكرار في رقم الهوية
        if self.registration_type == 'new' and self.identity_number:
            existing_registration = self.search([
                ('identity_number', '=', self.identity_number),
                ('state', 'in', ['confirmed', 'approved']),
                ('id', '!=', self.id)
            ])

            if existing_registration:
                raise ValidationError(
                    f'يوجد تسجيل آخر برقم الهوية {self.identity_number} في حالة نشطة!'
                )

        # تغيير الحالة فقط
        self.state = 'confirmed'

        # إرسال رسالة في الشات
        self.message_post(
            body=f'تم تأكيد التسجيل وفي انتظار الاعتماد من الإدارة',
            message_type='notification'
        )

        _logger.info(f"Registration {self.id} confirmed successfully")

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

    # في دالة action_approve، عدّل قسم معالجة الملفات

    def action_approve(self):
        """اعتماد التسجيل وإنشاء ملف الطفل وفواتير التسجيل والأقساط"""
        self.ensure_one()

        _logger.info(f"Approving registration {self.id}")

        # إنشاء ملف طفل جديد إذا لم يكن موجود
        if self.registration_type == 'new' and not self.child_profile_id:
            # التحقق من عدم وجود طفل بنفس الوثائق
            domain = []
            if self.identity_number:
                domain.append(('identity_number', '=', self.identity_number))
            if self.passport_number:
                if domain:
                    domain = ['|'] + domain + [('passport_number', '=', self.passport_number)]
                else:
                    domain = [('passport_number', '=', self.passport_number)]

            existing_child = False
            if domain:
                existing_child = self.env['nursery.child.profile'].search(domain, limit=1)

            if existing_child:
                # ربط التسجيل بالطفل الموجود بدلاً من إنشاء جديد
                self.child_profile_id = existing_child
                self.registration_type = 'existing'
                _logger.info(f"Found existing child profile {existing_child.id}, linking registration")
            else:
                # إنشاء ملف جديد مع نقل الملفات
                child_vals = {
                    'first_name': self.first_name,
                    'father_name': self.father_name,
                    'family_name': self.family_name,
                    'birth_date': self.birth_date,
                    'gender': self.gender,
                    'passport_number': self.passport_number,
                    'identity_number': self.identity_number,
                    'child_order': self.child_order,
                }

                try:
                    # إنشاء ملف الطفل أولاً
                    self.child_profile_id = self.env['nursery.child.profile'].create(child_vals)
                    _logger.info(f"Child profile created with ID: {self.child_profile_id.id}")

                    # نسخ المرفقات من التسجيل إلى ملف الطفل
                    attachments_to_copy = self.env['ir.attachment'].search([
                        ('res_model', '=', 'nursery.child.registration'),
                        ('res_id', '=', self.id),
                        ('res_field', 'in',
                         ['child_id_front', 'child_id_back', 'guardian_id_front', 'guardian_id_back'])
                    ])

                    for attachment in attachments_to_copy:
                        # إنشاء نسخة للطفل
                        new_attachment = attachment.copy({
                            'res_model': 'nursery.child.profile',
                            'res_id': self.child_profile_id.id,
                        })
                        _logger.info(f"Copied attachment {attachment.name} to child profile")

                    # إرسال رسالة نجاح
                    self.message_post(
                        body=f'تم إنشاء ملف للطفل {self.child_profile_id.full_name}',
                        message_type='notification'
                    )

                except Exception as e:
                    _logger.error(f"Error creating child profile: {str(e)}")
                    raise ValidationError(f"خطأ في إنشاء ملف الطفل: {str(e)}")

        # التحقق من عدم وجود تسجيل نشط آخر لنفس الطفل في نفس القسم
        if self.child_profile_id:
            existing_registration = self.search([
                ('child_profile_id', '=', self.child_profile_id.id),
                ('department_id', '=', self.department_id.id),
                ('state', '=', 'approved'),
                ('id', '!=', self.id)
            ])

            if existing_registration:
                raise ValidationError(
                    f'الطفل {self.child_profile_id.full_name} لديه تسجيل نشط بالفعل في قسم {self.department_id.name}!'
                )

        # التحقق من السعر
        if not self.registration_price or self.registration_price <= 0:
            self._compute_registration_price()
            if not self.registration_price or self.registration_price <= 0:
                raise ValidationError('لا يوجد سعر محدد للتسجيل. يرجى التحقق من خطة الحضانة وعدد الأيام.')

        # التحقق من عدد الأقساط
        if self.payment_type == 'installments' and self.installments_count <= 0:
            raise ValidationError('عدد الأقساط غير صحيح!')

        # التحقق من الحاجة لإدخال بيانات الشيك
        if self.payment_method == 'cheque' and not self.env.context.get('cheque_data'):
            # فتح wizard لإدخال بيانات الشيك (سواء دفعة واحدة أو أقساط)
            wizard_action = {
                'type': 'ir.actions.act_window',
                'name': 'إدخال بيانات الشيك' if self.payment_type == 'full' else 'إدخال بيانات الشيكات',
                'res_model': 'nursery.cheque.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref('charity_clubs.view_nursery_cheque_wizard_form').id,
                'target': 'new',
                'context': {
                    'default_registration_id': self.id,
                }
            }

            _logger.info(f"Opening cheque wizard for registration {self.id} - Payment type: {self.payment_type}")
            return wizard_action

        # تغيير الحالة
        self.state = 'approved'

        # إنشاء الفواتير
        self._create_registration_invoices()

        # إرسال رسالة في الشات
        message = f'تم اعتماد تسجيل الطفل {self.child_full_name or self.child_profile_id.full_name}'

        # إضافة تفاصيل الدفع
        if self.payment_type == 'full':
            message += f'<br/>نوع الدفع: دفعة واحدة'
            message += f'<br/>المبلغ: {self.final_price} درهم'
        else:
            message += f'<br/>نوع الدفع: {self.installments_count} أقساط'
            message += f'<br/>قيمة القسط: {self.installment_amount} درهم'

        if self.payment_method == 'cheque':
            message += f'<br/>طريقة الدفع: شيك'
            # إضافة معلومات الشيك إذا كانت موجودة
            cheque_data = self.env.context.get('cheque_data', [])
            if cheque_data:
                if len(cheque_data) == 1:
                    message += f'<br/>رقم الشيك: {cheque_data[0].get("cheque_no", "")}'
                    message += f'<br/>البنك: {cheque_data[0].get("bank_name", "")}'
                else:
                    message += f'<br/>تم إدخال {len(cheque_data)} شيكات'

        self.message_post(
            body=message,
            message_type='notification'
        )

        _logger.info(f"Registration {self.id} approved successfully")

        # إذا كان هناك view محدد للعودة إليه
        if self.env.context.get('return_view'):
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'nursery.child.registration',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_view_installments(self):
        """فتح جدول الأقساط"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'أقساط {self.child_full_name}',
            'view_mode': 'list,form',
            'res_model': 'nursery.payment.schedule',
            'domain': [('registration_id', '=', self.id)],
            'context': {'default_registration_id': self.id}
        }

    def action_view_registration_fee_invoice(self):
        """فتح فاتورة رسوم التسجيل"""
        self.ensure_one()
        if not self.registration_fee_invoice_id:
            return

        return {
            'type': 'ir.actions.act_window',
            'name': 'فاتورة رسوم التسجيل',
            'res_model': 'account.move',
            'res_id': self.registration_fee_invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_registration_invoices(self):
        """إنشاء فواتير التسجيل والأقساط"""
        self.ensure_one()

        # الحصول على الشريك (ولي الأمر)
        partner = self._get_or_create_partner()

        # 1. إنشاء فاتورة رسوم التسجيل (إذا كان طفل جديد)
        if (self.child_profile_id and
                not self.child_profile_id.has_paid_registration_fee and
                self.department_id.registration_fee > 0):
            reg_invoice = self._create_registration_fee_invoice(partner)
            self.registration_fee_invoice_id = reg_invoice
            self.child_profile_id.registration_fee_invoice_id = reg_invoice
            self.child_profile_id.has_paid_registration_fee = True

            _logger.info(f"Created registration fee invoice {reg_invoice.name}")

        # 2. إنشاء جدول الأقساط وفواتيرها
        self._create_payment_schedule(partner)

    def _get_or_create_partner(self):
        """الحصول على شريك موجود أو إنشاء جديد باسم الطفل"""

        # البحث عن شريك موجود للطفل
        child_name = self.child_full_name or f"{self.first_name} {self.father_name} {self.family_name}"

        # البحث بناءً على اسم الطفل ورقم الهوية
        partner = False
        if self.identity_number:
            partner = self.env['res.partner'].search([
                ('name', '=', child_name),
                ('ref', '=', self.identity_number)
            ], limit=1)

        # إذا لم نجد، ابحث باسم الطفل فقط
        if not partner:
            partner = self.env['res.partner'].search([
                ('name', '=', child_name),
                ('parent_id', '!=', False)  # للتأكد أنه طفل وليس ولي أمر
            ], limit=1)

        # إنشاء شريك جديد باسم الطفل إذا لم نجد
        if not partner:
            partner_vals = {
                'name': child_name,
                'ref': self.identity_number,  # رقم الهوية كمرجع
                'is_company': False,
                'customer_rank': 1,
                'street': self.home_address,
                'comment': f"""معلومات الوالدين:
    الأب: {self.father_full_name}
    هاتف الأب: {self.father_mobile}
    الأم: {self.mother_name}
    هاتف الأم: {self.mother_mobile}"""
            }

            # إضافة الإيميل إذا كان موجود
            if self.father_email:
                partner_vals['email'] = self.father_email
            if self.father_mobile:
                partner_vals['mobile'] = self.father_mobile

            partner = self.env['res.partner'].create(partner_vals)

            _logger.info(f"Created partner for child: {child_name}")

        return partner

    def _create_registration_fee_invoice(self, partner):
        """إنشاء فاتورة رسوم التسجيل"""
        invoice_vals = {
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'currency_id': self.env.company.currency_id.id,
            'narration': f"""معلومات الطفل:
    الاسم: {self.child_full_name}
    تاريخ الميلاد: {self.birth_date}
    رقم الهوية: {self.identity_number}

    معلومات الوالدين:
    الأب: {self.father_full_name}
    هاتف الأب: {self.father_mobile}
    بريد الأب: {self.father_email or 'غير محدد'}

    الأم: {self.mother_name}
    هاتف الأم: {self.mother_mobile}
    بريد الأم: {self.mother_email or 'غير محدد'}

    العنوان: {self.home_address}""",
            'invoice_line_ids': [(0, 0, {
                'name': f"رسوم تسجيل - {self.child_full_name} - {self.department_id.name}",
                'quantity': 1.0,
                'price_unit': self.department_id.registration_fee,
            })]
        }

        invoice = self.env['account.move'].create(invoice_vals)

        # إضافة رسالة في الشات
        self.message_post(
            body=f'تم إنشاء فاتورة رسوم التسجيل رقم {invoice.name} بمبلغ {self.department_id.registration_fee}',
            message_type='notification'
        )

        return invoice

    # تحديث دالة _create_payment_schedule في nursery_child_registration.py

    def _create_payment_schedule(self, partner):
        """إنشاء جدول الأقساط"""
        # حذف أي جدول قديم
        self.payment_schedule_ids.unlink()

        # الحصول على بيانات الشيكات من context
        cheque_data = self.env.context.get('cheque_data', [])
        cheque_dict = {ch['installment_no']: ch for ch in cheque_data}

        # التأكد من حساب السعر النهائي أولاً (مع الخصم إن وجد)
        if hasattr(self, 'final_price') and self.final_price:
            # استخدام السعر النهائي بعد الخصم
            total_amount = float(self.final_price)
        else:
            # استخدام السعر الأصلي إذا لم يكن هناك حقل final_price
            total_amount = float(self.registration_price) if self.registration_price else 0

        if total_amount <= 0:
            # محاولة إعادة حساب السعر
            self._compute_registration_price()
            if hasattr(self, '_compute_final_price'):
                self._compute_final_price()

            # إعادة التحقق
            if hasattr(self, 'final_price') and self.final_price:
                total_amount = float(self.final_price)
            else:
                total_amount = float(self.registration_price) if self.registration_price else 0

            if total_amount <= 0:
                raise ValidationError('لا يمكن إنشاء الأقساط: السعر النهائي غير محدد!')

        # تحديد عدد الأقساط بناءً على نوع الدفع
        if self.payment_type == 'full':
            installments_count = 1  # دفعة واحدة = قسط واحد
        else:
            installments_count = int(self.installments_count)

        # حساب قيمة القسط
        if cheque_data and len(cheque_data) > 0:
            # إذا كانت بيانات الشيكات موجودة، استخدم المبلغ منها
            first_cheque_amount = cheque_data[0].get('cheque_amount', 0)
            if first_cheque_amount and first_cheque_amount > 0:
                installment_amount = float(first_cheque_amount)
            else:
                installment_amount = round(total_amount / installments_count,
                                           2) if installments_count > 0 else total_amount
        else:
            installment_amount = round(total_amount / installments_count, 2) if installments_count > 0 else total_amount

        # تسجيل المعلومات
        _logger.info(f"Creating payment schedule: Original={self.registration_price}, ")
        if hasattr(self, 'total_discount'):
            _logger.info(f"Discount={self.total_discount}, ")
        _logger.info(f"Final={total_amount}, Count={installments_count}, Per installment={installment_amount}")

        # إنشاء الأقساط
        installments = []
        base_date = self.join_date or fields.Date.today()

        for i in range(installments_count):
            # حساب تاريخ الاستحقاق
            if self.payment_type == 'full':
                due_date = base_date  # دفعة واحدة = تاريخ واحد
            else:
                due_date = base_date + relativedelta(months=i)  # أقساط متعددة

            installment_no = i + 1

            installment_vals = {
                'registration_id': self.id,
                'installment_no': installment_no,
                'amount': installment_amount,
                'due_date': due_date,
                'payment_method': self.payment_method,
                'state': 'draft'
            }

            # إضافة بيانات الشيك إن وجدت
            if installment_no in cheque_dict:
                cheque_info = cheque_dict[installment_no]
                installment_vals.update({
                    'cheque_no': cheque_info.get('cheque_no', ''),
                    'bank_name': cheque_info.get('bank_name', ''),
                    'cheque_date': cheque_info.get('cheque_date'),
                })
                _logger.info(f"Adding cheque info for installment {installment_no}: {cheque_info}")

            installments.append((0, 0, installment_vals))
            _logger.info(f"Installment {installment_no}: amount={installment_amount}, due_date={due_date}")

        self.payment_schedule_ids = installments

        # إنشاء فاتورة للقسط الأول (أو الوحيد في حالة الدفعة الواحدة)
        if self.payment_schedule_ids and len(self.payment_schedule_ids) > 0:
            first_installment = self.payment_schedule_ids[0]

            # التحقق من المبلغ قبل إنشاء الفاتورة
            if first_installment.amount <= 0:
                raise ValidationError(f'مبلغ القسط الأول غير صحيح: {first_installment.amount}')

            # تحضير الملاحظات للفاتورة
            narration = f"""معلومات الطفل:
    الاسم: {self.child_full_name}
    تاريخ الميلاد: {self.birth_date}
    رقم الهوية: {self.identity_number}
    الصف: {self.nursery_class_id.class_name if self.nursery_class_id else 'غير محدد'}
    القسم: {self.department_id.name}

    معلومات الوالدين:
    الأب: {self.father_full_name}
    هاتف الأب: {self.father_mobile}
    بريد الأب: {self.father_email or 'غير محدد'}

    الأم: {self.mother_name}
    هاتف الأم: {self.mother_mobile}
    بريد الأم: {self.mother_email or 'غير محدد'}

    العنوان: {self.home_address}

    معلومات الدفع:"""

            # إضافة معلومات الدفع حسب النوع
            if self.payment_type == 'full':
                narration += f"""
    نوع الدفع: دفعة واحدة
    المبلغ الإجمالي: {total_amount} درهم
    طريقة الدفع: {dict(self._fields['payment_method'].selection).get(self.payment_method, '')}"""
            else:
                narration += f"""
    قسط رقم {first_installment.installment_no} من {self.installments_count}
    تاريخ الاستحقاق: {first_installment.due_date}
    طريقة الدفع: {dict(self._fields['payment_method'].selection).get(self.payment_method, '')}"""

            # إضافة معلومات الخصم إن وجدت
            if hasattr(self, 'total_discount') and self.total_discount > 0:
                narration += f"""

    الخصومات المطبقة:
    المبلغ الأصلي: {self.registration_price} درهم"""
                if self.discount_type == 'percentage':
                    narration += f"""
    نسبة الخصم: {self.discount_percentage}%
    قيمة الخصم: {self.total_discount} درهم"""
                elif self.discount_type == 'amount':
                    narration += f"""
    قيمة الخصم: {self.total_discount} درهم"""
                narration += f"""
    المبلغ النهائي: {total_amount} درهم"""

            # إضافة معلومات الشيك إن وجدت
            if first_installment.payment_method == 'cheque' and first_installment.cheque_no:
                narration += f"""

    معلومات الشيك:
    رقم الشيك: {first_installment.cheque_no}
    البنك: {first_installment.bank_name}
    تاريخ الشيك: {first_installment.cheque_date}"""

            # إنشاء فاتورة القسط الأول
            invoice_vals = {
                'partner_id': partner.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'currency_id': self.env.company.currency_id.id,
                'narration': narration,
                'invoice_line_ids': [(0, 0, {
                    'name': f"{'دفعة كاملة' if self.payment_type == 'full' else f'قسط {first_installment.installment_no}'} - {self.child_full_name} - {self.department_id.name}",
                    'quantity': 1.0,
                    'price_unit': float(first_installment.amount),
                })]
            }

            invoice = self.env['account.move'].create(invoice_vals)
            first_installment.invoice_id = invoice
            first_installment.state = 'invoiced'

            # ربط الفاتورة الأولى بالتسجيل
            self.invoice_id = invoice

            # إضافة رسالة في الشات
            if self.payment_type == 'full':
                message = f'تم إنشاء فاتورة الدفعة الكاملة رقم {invoice.name} بمبلغ {first_installment.amount} درهم'
                if self.payment_method == 'cheque' and first_installment.cheque_no:
                    message += f'<br/>رقم الشيك: {first_installment.cheque_no}'
                    message += f'<br/>البنك: {first_installment.bank_name}'
            else:
                message = f'تم إنشاء {self.installments_count} أقساط بقيمة {installment_amount} درهم لكل قسط'
                if hasattr(self, 'total_discount') and self.total_discount > 0:
                    message += f'<br/>تم تطبيق خصم إجمالي قدره {self.total_discount} درهم'
                    message += f'<br/>السعر الأصلي: {self.registration_price} درهم'
                    message += f'<br/>السعر بعد الخصم: {total_amount} درهم'
                message += f'<br/>تم إنشاء فاتورة القسط الأول رقم {invoice.name} بمبلغ {first_installment.amount} درهم'

            self.message_post(
                body=message,
                message_type='notification'
            )

        _logger.info(f"Created {installments_count} installment(s) for registration {self.id}")
        if hasattr(self, 'total_discount'):
            _logger.info(f"With discount {self.total_discount}")

    def action_reject(self):
        self.ensure_one()
        self.state = 'rejected'

    def action_reset_draft(self):
        self.ensure_one()
        self.state = 'draft'

    def _process_binary_field(self, binary_data):
        """معالجة البيانات الثنائية للتأكد من حفظها بشكل صحيح"""
        if not binary_data:
            return False

        # إذا كانت البيانات من نوع bytes، أعدها كما هي
        if isinstance(binary_data, bytes):
            return binary_data

        # إذا كانت البيانات من نوع string (base64)
        if isinstance(binary_data, str):
            try:
                # محاولة فك التشفير من base64
                return base64.b64decode(binary_data)
            except:
                # إذا فشل، ربما تكون البيانات مشفرة بالفعل
                return binary_data.encode('utf-8')

        return binary_data

    @api.model
    def create(self, vals):
        """Override create to track file uploads"""
        record = super(NurseryChildRegistration, self).create(vals)

        # تتبع رفع الملفات
        messages = []
        if vals.get('child_id_front'):
            messages.append("تم رفع صورة الوجه الأمامي لهوية الطفل")
        if vals.get('child_id_back'):
            messages.append("تم رفع صورة الوجه الخلفي لهوية الطفل")
        if vals.get('guardian_id_front'):
            messages.append("تم رفع صورة الوجه الأمامي لهوية ولي الأمر")
        if vals.get('guardian_id_back'):
            messages.append("تم رفع صورة الوجه الخلفي لهوية ولي الأمر")

        if messages:
            record.message_post(body="<br/>".join(messages))

        return record

    def write(self, vals):
        """Override write to track file changes"""
        # تتبع التغييرات في الملفات
        messages = []

        for record in self:
            if vals.get('child_id_front'):
                if record.child_id_front:
                    messages.append("تم تحديث صورة الوجه الأمامي لهوية الطفل")
                else:
                    messages.append("تم رفع صورة الوجه الأمامي لهوية الطفل")

            if vals.get('child_id_back'):
                if record.child_id_back:
                    messages.append("تم تحديث صورة الوجه الخلفي لهوية الطفل")
                else:
                    messages.append("تم رفع صورة الوجه الخلفي لهوية الطفل")

            if vals.get('guardian_id_front'):
                if record.guardian_id_front:
                    messages.append("تم تحديث صورة الوجه الأمامي لهوية ولي الأمر")
                else:
                    messages.append("تم رفع صورة الوجه الأمامي لهوية ولي الأمر")

            if vals.get('guardian_id_back'):
                if record.guardian_id_back:
                    messages.append("تم تحديث صورة الوجه الخلفي لهوية ولي الأمر")
                else:
                    messages.append("تم رفع صورة الوجه الخلفي لهوية ولي الأمر")

        result = super(NurseryChildRegistration, self).write(vals)

        if messages:
            for record in self:
                record.message_post(body="<br/>".join(messages))

        return result

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
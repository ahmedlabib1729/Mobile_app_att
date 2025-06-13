# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class ClubRegistrations(models.Model):
    _name = 'charity.club.registrations'
    _description = 'تسجيلات النوادي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'
    _order = 'create_date desc'

    # معلومات الطالب الأساسية
    full_name = fields.Char(
        string='الاسم الثلاثي كما في الهوية',
        required=True,
        tracking=True,
        help='أدخل الاسم الثلاثي كما هو مكتوب في الهوية'
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        required=True,
        tracking=True,
        help='تاريخ ميلاد الطالب'
    )

    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس',
        required=True,
        tracking=True
    )

    # معلومات التسجيل السابق
    previous_roayati_member = fields.Boolean(
        string='هل كان مشترك بنوادي رؤيتي سابقاً؟',
        default=False,
        help='حدد إذا كان الطالب مشترك سابقاً في نوادي رؤيتي'
    )

    previous_arabic_club = fields.Boolean(
        string='هل كان مشترك بنادي لغة عربية سابقاً؟',
        default=False,
        help='حدد إذا كان الطالب مشترك سابقاً في نادي اللغة العربية'
    )

    previous_qaida_noorania = fields.Boolean(
        string='هل أخذ القاعدة النورانية سابقاً؟',
        default=False,
        help='حدد إذا كان الطالب قد درس القاعدة النورانية سابقاً'
    )

    quran_memorization = fields.Text(
        string='مقدار حفظ القرآن',
        help='اكتب مقدار حفظ الطالب من القرآن الكريم'
    )

    # معلومات اللغة والتعليم
    arabic_education_type = fields.Selection([
        ('non_native', 'لغة عربية لغير الناطقين'),
        ('native', 'لغة عربية للناطقين')
    ], string='تعلم اللغة العربية بالمدرسة',
        required=True,
        help='حدد نوع تعليم اللغة العربية في المدرسة'
    )

    nationality = fields.Many2one(
        'res.country',
        string='الجنسية',
        required=True,
        help='اختر جنسية الطالب'
    )

    student_grade = fields.Char(
        string='الصف',
        required=True,
        help='أدخل الصف الدراسي للطالب'
    )

    # معلومات الوالدين
    mother_name = fields.Char(
        string='اسم الأم',
        required=True,
        help='أدخل اسم والدة الطالب'
    )

    mother_mobile = fields.Char(
        string='هاتف الأم المتحرك',
        required=True,
        help='أدخل رقم هاتف والدة الطالب'
    )

    father_name = fields.Char(
        string='اسم الأب',
        required=True,
        help='أدخل اسم والد الطالب'
    )

    father_mobile = fields.Char(
        string='هاتف الأب المتحرك',
        required=True,
        help='أدخل رقم هاتف والد الطالب'
    )

    mother_whatsapp = fields.Char(
        string='الواتس اب للأم',
        required=True,
        help='أدخل رقم واتساب والدة الطالب'
    )

    email = fields.Char(
        string='البريد الإلكتروني',
        help='البريد الإلكتروني للتواصل'
    )

    # المتطلبات الصحية
    has_health_requirements = fields.Boolean(
        string='هل يوجد متطلبات صحية أو احتياجات خاصة؟',
        default=False,
        help='في حال وجود أي متطلبات صحية أو احتياجات خاصة أو حساسيات لدى الطالب'
    )

    health_requirements = fields.Text(
        string='تفاصيل المتطلبات الصحية',
        help='يرجى كتابة تفاصيل المتطلبات الصحية أو الاحتياجات الخاصة'
    )

    # الموافقات
    photo_consent = fields.Boolean(
        string='الموافقة على التصوير',
        default=False,
        required=True,
        help='ملاحظة: يتم تصوير الطلاب خلال فعاليات النوادي وتوضع في مواقع التواصل الاجتماعي للجمعية'
    )

    # معلومات الهوية
    id_type = fields.Selection([
        ('emirates_id', 'الهوية الإماراتية'),
        ('passport', 'جواز السفر')
    ], string='نوع الهوية',
        required=True,
        default='emirates_id',
        tracking=True,
        help='اختر نوع الهوية'
    )

    id_number = fields.Char(
        string='رقم الهوية/الجواز',
        required=True,
        tracking=True,
        help='أدخل رقم الهوية الإماراتية أو رقم جواز السفر'
    )

    # صور الهوية
    id_front_file = fields.Binary(
        string='صورة الهوية - الوجه الأول',
        required=True,
        attachment=True,
        help='أرفق صورة الوجه الأول من الهوية'
    )

    id_front_filename = fields.Char(
        string='اسم ملف الوجه الأول'
    )

    id_back_file = fields.Binary(
        string='صورة الهوية - الوجه الثاني',
        required=True,
        attachment=True,
        help='أرفق صورة الوجه الثاني من الهوية'
    )

    id_back_filename = fields.Char(
        string='اسم ملف الوجه الثاني'
    )

    # معلومات إضافية
    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True,
        help='العمر المحسوب من تاريخ الميلاد'
    )

    registration_date = fields.Datetime(
        string='تاريخ التسجيل',
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
        help='حالة التسجيل'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    # حقول التسجيل في النوادي
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
        tracking=True,
        domain="[('headquarters_id', '=', headquarters_id), ('type', '=', 'clubs')]",
        required=True,
        help='اختر القسم'
    )

    club_id = fields.Many2one(
        'charity.clubs',
        string='النادي',
        tracking=True,
        domain="[('department_id', '=', department_id)]",
        required=True,
        help='اختر النادي'
    )

    term_id = fields.Many2one(
        'charity.club.terms',
        string='الترم',
        tracking=True,
        domain="[('club_id', '=', club_id), ('is_active', '=', True)]",
        required=True,
        help='اختر الترم'
    )

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

    @api.onchange('has_health_requirements')
    def _onchange_has_health_requirements(self):
        """مسح تفاصيل المتطلبات الصحية عند إلغاء التحديد"""
        if not self.has_health_requirements:
            self.health_requirements = False

    @api.onchange('headquarters_id')
    def _onchange_headquarters_id(self):
        """تحديث domain الأقسام والنوادي عند تغيير المقر"""
        if self.headquarters_id:
            self.department_id = False
            self.club_id = False
            self.term_id = False
            return {
                'domain': {
                    'department_id': [
                        ('headquarters_id', '=', self.headquarters_id.id),
                        ('type', '=', 'clubs')
                    ]
                }
            }

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """تحديث domain النوادي عند تغيير القسم"""
        if self.department_id:
            self.club_id = False
            self.term_id = False
            return {
                'domain': {
                    'club_id': [('department_id', '=', self.department_id.id)]
                }
            }

    @api.onchange('club_id')
    def _onchange_club_id(self):
        """تحديث domain الترمات عند تغيير النادي"""
        if self.club_id:
            self.term_id = False
            # التحقق من العمر والجنس
            if self.age and self.gender:
                # التحقق من العمر
                if self.age < self.club_id.age_from or self.age > self.club_id.age_to:
                    return {
                        'warning': {
                            'title': 'تحذير',
                            'message': f'عمر الطالب ({self.age} سنة) خارج النطاق المسموح للنادي ({self.club_id.age_from} - {self.club_id.age_to} سنة)'
                        }
                    }

                # التحقق من الجنس
                if self.club_id.gender_type != 'both' and self.gender != self.club_id.gender_type:
                    gender_text = 'ذكور' if self.club_id.gender_type == 'male' else 'إناث'
                    return {
                        'warning': {
                            'title': 'تحذير',
                            'message': f'هذا النادي مخصص لـ {gender_text} فقط'
                        }
                    }

            # البحث عن الترمات النشطة
            today = fields.Date.today()
            domain = [
                ('club_id', '=', self.club_id.id),
                ('is_active', '=', True),
                ('date_to', '>=', today),
                '|',
                ('date_from', '<=', today),
                ('date_from', '>', today)
            ]

            available_terms = self.env['charity.club.terms'].search(domain)
            if len(available_terms) == 1:
                self.term_id = available_terms[0]

            return {
                'domain': {
                    'term_id': domain
                }
            }

    @api.onchange('id_type', 'id_number')
    def _onchange_format_id_number(self):
        """تنسيق رقم الهوية تلقائياً"""
        if self.id_type == 'emirates_id' and self.id_number:
            clean_id = self.id_number.replace('-', '').replace(' ', '').strip()
            if len(clean_id) == 15 and clean_id.isdigit():
                self.id_number = f"{clean_id[0:3]}-{clean_id[3:7]}-{clean_id[7:14]}-{clean_id[14]}"
        elif self.id_type == 'passport' and self.id_number:
            self.id_number = self.id_number.upper().strip()

    @api.constrains('id_type', 'id_number')
    def _check_id_number(self):
        """التحقق من صحة رقم الهوية أو الجواز"""
        import re
        for record in self:
            if not record.id_number:
                raise ValidationError('يجب إدخال رقم الهوية أو الجواز!')

            if record.id_type == 'emirates_id':
                emirates_id_pattern = re.compile(r'^784-\d{4}-\d{7}-\d$')
                if not emirates_id_pattern.match(record.id_number):
                    clean_id = record.id_number.replace('-', '').strip()
                    if not (len(clean_id) == 15 and clean_id.startswith('784') and clean_id.isdigit()):
                        raise ValidationError(
                            'رقم الهوية الإماراتية غير صحيح!\n'
                            'يجب أن يكون بالصيغة: 784-YYYY-XXXXXXX-X\n'
                            'مثال: 784-1990-1234567-1'
                        )

            elif record.id_type == 'passport':
                passport_pattern = re.compile(r'^[A-Z0-9]{6,9}$')
                if not passport_pattern.match(record.id_number.upper()):
                    raise ValidationError(
                        'رقم جواز السفر غير صحيح!\n'
                        'يجب أن يحتوي على أحرف وأرقام فقط (6-9 خانات)\n'
                        'مثال: AB1234567'
                    )

    @api.constrains('birth_date')
    def _check_birth_date(self):
        """التحقق من صحة تاريخ الميلاد"""
        for record in self:
            if record.birth_date:
                if record.birth_date > date.today():
                    raise ValidationError('تاريخ الميلاد لا يمكن أن يكون في المستقبل!')

    @api.constrains('mother_mobile', 'father_mobile', 'mother_whatsapp')
    def _check_phone_numbers(self):
        """التحقق من صحة أرقام الهواتف"""
        import re
        phone_pattern = re.compile(r'^[\d\s\-\+]+$')

        for record in self:
            if record.mother_mobile and not phone_pattern.match(record.mother_mobile):
                raise ValidationError('رقم هاتف الأم غير صحيح!')
            if record.father_mobile and not phone_pattern.match(record.father_mobile):
                raise ValidationError('رقم هاتف الأب غير صحيح!')
            if record.mother_whatsapp and not phone_pattern.match(record.mother_whatsapp):
                raise ValidationError('رقم واتساب الأم غير صحيح!')

    @api.constrains('email')
    def _check_email(self):
        """التحقق من صحة البريد الإلكتروني"""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for record in self:
            if record.email and not email_pattern.match(record.email):
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    @api.constrains('has_health_requirements', 'health_requirements')
    def _check_health_requirements(self):
        """التحقق من كتابة المتطلبات الصحية إذا تم التحديد"""
        for record in self:
            if record.has_health_requirements and not record.health_requirements:
                raise ValidationError('يجب كتابة تفاصيل المتطلبات الصحية!')

    @api.constrains('id_front_file', 'id_back_file')
    def _check_id_files(self):
        """التحقق من رفع ملفات الهوية"""
        for record in self:
            if not record.id_front_file:
                raise ValidationError('يجب رفع صورة الوجه الأول من الهوية!')
            if not record.id_back_file:
                raise ValidationError('يجب رفع صورة الوجه الثاني من الهوية!')

    @api.constrains('term_id')
    def _check_term_validity(self):
        """التحقق من صلاحية الترم"""
        for record in self:
            if record.term_id:
                today = fields.Date.today()
                if record.term_id.date_to < today:
                    raise ValidationError('لا يمكن التسجيل في ترم منتهي!')
                if not record.term_id.is_active:
                    raise ValidationError('هذا الترم مغلق للتسجيل!')

    @api.constrains('club_id', 'age', 'gender')
    def _check_club_requirements(self):
        """التحقق من متطلبات النادي"""
        for record in self:
            if record.club_id:
                # التحقق من العمر
                if record.age < record.club_id.age_from or record.age > record.club_id.age_to:
                    raise ValidationError(
                        f'عمر الطالب ({record.age} سنة) خارج النطاق المسموح للنادي '
                        f'({record.club_id.age_from} - {record.club_id.age_to} سنة)!'
                    )

                # التحقق من الجنس
                if record.club_id.gender_type != 'both':
                    if record.club_id.gender_type == 'male' and record.gender != 'male':
                        raise ValidationError('هذا النادي مخصص للذكور فقط!')
                    elif record.club_id.gender_type == 'female' and record.gender != 'female':
                        raise ValidationError('هذا النادي مخصص للإناث فقط!')

    def action_confirm(self):
        """تأكيد التسجيل"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'confirmed'

    def action_approve(self):
        """اعتماد التسجيل"""
        self.ensure_one()
        if self.state == 'confirmed':
            self.state = 'approved'

    def action_reject(self):
        """رفض التسجيل"""
        self.ensure_one()
        if self.state in ('draft', 'confirmed'):
            self.state = 'rejected'

    def action_cancel(self):
        """إلغاء التسجيل"""
        self.ensure_one()
        if self.state != 'approved':
            self.state = 'cancelled'

    def action_reset_draft(self):
        """إعادة التسجيل إلى مسودة"""
        self.ensure_one()
        self.state = 'draft'

    _sql_constraints = [
        ('id_number_unique', 'UNIQUE(id_number, company_id)', 'رقم الهوية/الجواز مسجل مسبقاً!'),
    ]

    def name_get(self):
        """تخصيص طريقة عرض اسم التسجيل"""
        result = []
        for record in self:
            name = f"{record.full_name} - {record.student_grade}"
            result.append((record.id, name))
        return result
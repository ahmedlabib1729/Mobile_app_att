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

    # نوع التسجيل
    registration_type = fields.Selection([
        ('new', 'تسجيل جديد'),
        ('existing', 'طالب مسجل')
    ], string='نوع التسجيل',
        default='new',
        tracking=True,
        help='حدد ما إذا كان طالب جديد أو مسجل سابقاً'
    )

    # حقل الطالب للطلاب المسجلين
    student_profile_id = fields.Many2one(
        'charity.student.profile',
        string='ملف الطالب',
        tracking=True,
        help='اختر ملف الطالب المسجل سابقاً'
    )

    # معلومات الطالب الأساسية (للتسجيل الجديد)
    full_name = fields.Char(
        string='الاسم الثلاثي كما في الهوية',
        tracking=True,
        help='أدخل الاسم الثلاثي كما هو مكتوب في الهوية',
        required=False  # مطلوب فقط عند التأكيد
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        tracking=True,
        help='تاريخ ميلاد الطالب',
        required=False  # مطلوب فقط عند التأكيد
    )

    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس',
        tracking=True,
        required=False  # مطلوب فقط عند التأكيد
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
        help='حدد نوع تعليم اللغة العربية في المدرسة'
    )

    nationality = fields.Many2one(
        'res.country',
        string='الجنسية',
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
        help='أدخل اسم والدة الطالب'
    )

    mother_mobile = fields.Char(
        string='هاتف الأم المتحرك',
        help='أدخل رقم هاتف والدة الطالب'
    )

    father_name = fields.Char(
        string='اسم الأب',
        help='أدخل اسم والد الطالب'
    )

    father_mobile = fields.Char(
        string='هاتف الأب المتحرك',
        help='أدخل رقم هاتف والد الطالب'
    )

    mother_whatsapp = fields.Char(
        string='الواتس اب للأم',
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
        help='ملاحظة: يتم تصوير الطلاب خلال فعاليات النوادي وتوضع في مواقع التواصل الاجتماعي للجمعية'
    )

    # معلومات الهوية
    id_type = fields.Selection([
        ('emirates_id', 'الهوية الإماراتية'),
        ('passport', 'جواز السفر')
    ], string='نوع الهوية',
        default='emirates_id',
        tracking=True,
        help='اختر نوع الهوية'
    )

    id_number = fields.Char(
        string='رقم الهوية/الجواز',
        tracking=True,
        help='أدخل رقم الهوية الإماراتية أو رقم جواز السفر'
    )

    # صور الهوية
    id_front_file = fields.Binary(
        string='صورة الهوية - الوجه الأول',
        attachment=True,
        help='أرفق صورة الوجه الأول من الهوية'
    )

    id_front_filename = fields.Char(
        string='اسم ملف الوجه الأول'
    )

    id_back_file = fields.Binary(
        string='صورة الهوية - الوجه الثاني',
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

    # حقول الفاتورة الجديدة
    invoice_id = fields.Many2one(
        'account.move',
        string='الفاتورة',
        readonly=True,
        help='الفاتورة المرتبطة بهذا التسجيل'
    )

    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='حالة الفاتورة',
        store=True
    )

    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state',
        string='حالة الدفع',
        store=True
    )

    term_price = fields.Float(
        related='term_id.price',
        string='سعر الترم',
        readonly=True
    )

    # حقول الخصومات
    discount_policy = fields.Selection([
        ('cumulative', 'تراكمي'),
        ('highest', 'الأعلى فقط'),
        ('manual', 'يدوي')
    ], string='سياسة الخصم',
        default='cumulative',
        help='كيفية حساب الخصومات المتعددة'
    )

    # خصم الأخوة
    sibling_order = fields.Integer(
        string='ترتيب الطفل بين إخوته',
        compute='_compute_sibling_order',
        store=True,
        help='ترتيب الطفل بين إخوته في الترمات النشطة'
    )

    sibling_discount_rate = fields.Float(
        string='نسبة خصم الأخوة (%)',
        compute='_compute_discounts',
        store=True,
        help='نسبة خصم الأخوة المطبقة'
    )

    # خصم النوادي المتعددة
    has_multi_club = fields.Boolean(
        string='مسجل في نادي آخر',
        compute='_compute_has_multi_club',
        store=True,
        help='هل الطالب مسجل في نادي آخر في نفس الفترة'
    )

    multi_club_discount_rate = fields.Float(
        string='خصم النوادي المتعددة (%)',
        compute='_compute_discounts',
        store=True,
        help='خصم 15% للتسجيل في أكثر من نادي'
    )

    # خصم نصف الترم
    is_half_term = fields.Boolean(
        string='تسجيل بعد نصف الترم',
        compute='_compute_is_half_term',
        store=True,
        help='هل التسجيل تم بعد منتصف الترم'
    )

    half_term_discount_rate = fields.Float(
        string='خصم نصف الترم (%)',
        compute='_compute_discounts',
        store=True,
        help='خصم 50% للتسجيل بعد نصف الترم'
    )

    # إجمالي الخصومات
    total_discount_rate = fields.Float(
        string='إجمالي نسبة الخصم (%)',
        compute='_compute_discounts',
        store=True,
        help='إجمالي نسبة الخصم المطبقة'
    )

    discount_amount = fields.Float(
        string='قيمة الخصم',
        compute='_compute_discounts',
        store=True,
        help='قيمة الخصم بالمبلغ'
    )

    final_amount = fields.Float(
        string='المبلغ النهائي',
        compute='_compute_discounts',
        store=True,
        help='المبلغ النهائي بعد الخصم'
    )

    @api.depends('birth_date', 'student_profile_id')
    def _compute_age(self):
        """حساب العمر من تاريخ الميلاد"""
        today = date.today()
        for record in self:
            birth_date = record.birth_date
            if record.registration_type == 'existing' and record.student_profile_id:
                birth_date = record.student_profile_id.birth_date

            if birth_date:
                age = relativedelta(today, birth_date)
                record.age = age.years
            else:
                record.age = 0

    @api.depends('student_profile_id', 'term_id', 'state', 'father_mobile', 'mother_mobile')
    def _compute_sibling_order(self):
        """حساب ترتيب الطفل بين إخوته في الترمات النشطة"""
        for record in self:
            if record.state == 'cancelled':
                record.sibling_order = 0
                continue

            # الحصول على العائلة
            family_id = False
            if record.student_profile_id and record.student_profile_id.family_profile_id:
                family_id = record.student_profile_id.family_profile_id.id
            elif record.registration_type == 'new' and (record.father_mobile or record.mother_mobile):
                # البحث عن العائلة بناءً على رقم الهاتف
                family_domain = []
                if record.father_mobile:
                    family_domain.append(('father_mobile', '=', record.father_mobile))
                if record.mother_mobile:
                    if family_domain:
                        family_domain = ['|'] + family_domain + [('mother_mobile', '=', record.mother_mobile)]
                    else:
                        family_domain.append(('mother_mobile', '=', record.mother_mobile))

                family = self.env['charity.family.profile'].search(family_domain, limit=1)
                if family:
                    family_id = family.id

            if not family_id:
                record.sibling_order = 1
                continue

            # البحث عن جميع الأطفال في نفس العائلة
            family = self.env['charity.family.profile'].browse(family_id)
            all_children_ids = family.student_ids.ids

            # البحث عن التسجيلات النشطة لهذه العائلة
            domain = [
                ('state', 'not in', ['cancelled', 'rejected']),
                '|',
                ('student_profile_id', 'in', all_children_ids),
                '&',
                ('registration_type', '=', 'new'),
                '|',
                '&',
                ('father_mobile', '!=', False),
                ('father_mobile', '=', record.father_mobile),
                '&',
                ('mother_mobile', '!=', False),
                ('mother_mobile', '=', record.mother_mobile)
            ]

            # التسجيلات في ترمات نشطة
            today = fields.Date.today()
            active_registrations = self.search(domain + [
                ('term_id.date_to', '>=', today),
                ('term_id.is_active', '=', True)
            ])

            # تجميع حسب الطالب (لتجنب حساب نفس الطالب مرتين)
            students_dict = {}
            for reg in active_registrations:
                # مفتاح فريد للطالب
                if reg.student_profile_id:
                    student_key = f'profile_{reg.student_profile_id.id}'
                else:
                    student_key = f'id_{reg.id_number}' if reg.id_number else f'reg_{reg.id}'

                # نأخذ أقدم تسجيل لكل طالب
                if student_key not in students_dict or reg.registration_date < students_dict[
                    student_key].registration_date:
                    students_dict[student_key] = reg

            # ترتيب الطلاب حسب تاريخ أول تسجيل
            sorted_students = sorted(students_dict.values(), key=lambda r: r.registration_date)

            # تحديد ترتيب الطالب الحالي
            current_student_key = None
            if record.student_profile_id:
                current_student_key = f'profile_{record.student_profile_id.id}'
            else:
                current_student_key = f'id_{record.id_number}' if record.id_number else f'reg_{record.id}'

            order = 1
            for idx, reg in enumerate(sorted_students, 1):
                reg_key = None
                if reg.student_profile_id:
                    reg_key = f'profile_{reg.student_profile_id.id}'
                else:
                    reg_key = f'id_{reg.id_number}' if reg.id_number else f'reg_{reg.id}'

                if reg_key == current_student_key:
                    record.sibling_order = idx
                    break
            else:
                record.sibling_order = 1

    @api.depends('student_profile_id', 'term_id', 'state')
    def _compute_has_multi_club(self):
        """التحقق من تسجيل الطالب في نادي آخر"""
        for record in self:
            if record.state == 'cancelled' or not record.term_id:
                record.has_multi_club = False
                continue

            # البحث عن تسجيلات أخرى لنفس الطالب
            domain = [
                ('id', '!=', record.id),
                ('state', 'not in', ['cancelled', 'rejected']),
            ]

            if record.student_profile_id:
                domain.append(('student_profile_id', '=', record.student_profile_id.id))
            elif record.registration_type == 'new' and record.id_number:
                domain.append(('id_number', '=', record.id_number))
            else:
                record.has_multi_club = False
                continue

            # التحقق من التداخل في التواريخ
            other_registrations = self.search(domain)
            for other in other_registrations:
                if other.term_id and record.term_id:
                    # التحقق من تداخل التواريخ
                    if (other.term_id.date_from <= record.term_id.date_to and
                            other.term_id.date_to >= record.term_id.date_from):
                        record.has_multi_club = True
                        return

            record.has_multi_club = False

    @api.depends('registration_date', 'term_id')
    def _compute_is_half_term(self):
        """التحقق من التسجيل بعد نصف الترم"""
        for record in self:
            if not record.term_id or not record.term_id.date_from or not record.term_id.date_to:
                record.is_half_term = False
                continue

            # حساب منتصف الترم
            term_duration = (record.term_id.date_to - record.term_id.date_from).days
            half_duration = term_duration / 2
            mid_date = record.term_id.date_from + relativedelta(days=int(half_duration))

            # مقارنة تاريخ التسجيل
            reg_date = record.registration_date.date() if record.registration_date else fields.Date.today()
            record.is_half_term = reg_date > mid_date

    @api.depends('sibling_order', 'has_multi_club', 'is_half_term', 'term_price', 'discount_policy')
    def _compute_discounts(self):
        """حساب جميع الخصومات"""
        for record in self:
            if not record.term_price or record.state == 'cancelled':
                record.sibling_discount_rate = 0
                record.multi_club_discount_rate = 0
                record.half_term_discount_rate = 0
                record.total_discount_rate = 0
                record.discount_amount = 0
                record.final_amount = record.term_price or 0
                continue

            # حساب خصم الأخوة
            sibling_discount = 0
            if record.sibling_order == 2:
                sibling_discount = 5
            elif record.sibling_order == 3:
                sibling_discount = 10
            elif record.sibling_order >= 4:
                sibling_discount = 15
            record.sibling_discount_rate = sibling_discount

            # خصم النوادي المتعددة
            multi_club_discount = 15 if record.has_multi_club else 0
            record.multi_club_discount_rate = multi_club_discount

            # خصم نصف الترم
            half_term_discount = 50 if record.is_half_term else 0
            record.half_term_discount_rate = half_term_discount

            # حساب إجمالي الخصم حسب السياسة
            if record.discount_policy == 'cumulative':
                # تراكمي - نجمع كل الخصومات
                total_discount = sibling_discount + multi_club_discount + half_term_discount
                # الحد الأقصى 100%
                total_discount = min(total_discount, 100)
            elif record.discount_policy == 'highest':
                # أعلى خصم فقط
                total_discount = max(sibling_discount, multi_club_discount, half_term_discount)
            else:  # manual
                # يدوي - نأخذ القيم المحسوبة كما هي
                total_discount = sibling_discount + multi_club_discount + half_term_discount
                total_discount = min(total_discount, 100)

            record.total_discount_rate = total_discount

            # حساب المبالغ
            record.discount_amount = (record.term_price * total_discount) / 100
            record.final_amount = record.term_price - record.discount_amount

    @api.onchange('registration_type')
    def _onchange_registration_type(self):
        """تنظيف الحقول عند تغيير نوع التسجيل"""
        if self.registration_type == 'new':
            self.student_profile_id = False
        else:
            # مسح الحقول اليدوية
            self.full_name = False
            self.birth_date = False
            self.gender = False
            self.nationality = False
            self.id_type = 'emirates_id'
            self.id_number = False
            self.mother_name = False
            self.mother_mobile = False
            self.father_name = False
            self.father_mobile = False
            self.mother_whatsapp = False
            self.email = False
            self.id_front_file = False
            self.id_back_file = False
            self.has_health_requirements = False
            self.health_requirements = False
            self.photo_consent = False

    @api.onchange('student_profile_id')
    def _onchange_student_profile_id(self):
        """ملء البيانات من ملف الطالب"""
        if self.registration_type == 'existing' and self.student_profile_id:
            # ملء البيانات من ملف الطالب
            self.full_name = self.student_profile_id.full_name
            self.birth_date = self.student_profile_id.birth_date
            self.gender = self.student_profile_id.gender
            self.nationality = self.student_profile_id.nationality
            self.id_type = self.student_profile_id.id_type
            self.id_number = self.student_profile_id.id_number
            self.has_health_requirements = self.student_profile_id.has_health_requirements
            self.health_requirements = self.student_profile_id.health_requirements
            self.photo_consent = self.student_profile_id.photo_consent

            # ملء بيانات العائلة
            if self.student_profile_id.family_profile_id:
                family = self.student_profile_id.family_profile_id
                self.mother_name = family.mother_name
                self.mother_mobile = family.mother_mobile
                self.father_name = family.father_name
                self.father_mobile = family.father_mobile
                self.mother_whatsapp = family.mother_whatsapp
                self.email = family.email

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

    @api.onchange('term_id')
    def _onchange_term_id(self):
        """Force recompute discounts when term changes"""
        if self.term_id:
            self._compute_is_half_term()
            self._compute_discounts()

    @api.onchange('id_type', 'id_number')
    def _onchange_format_id_number(self):
        """تنسيق رقم الهوية تلقائياً"""
        if self.registration_type == 'new' and self.id_type == 'emirates_id' and self.id_number:
            clean_id = self.id_number.replace('-', '').replace(' ', '').strip()
            if len(clean_id) == 15 and clean_id.isdigit():
                self.id_number = f"{clean_id[0:3]}-{clean_id[3:7]}-{clean_id[7:14]}-{clean_id[14]}"
        elif self.id_type == 'passport' and self.id_number:
            self.id_number = self.id_number.upper().strip()

    def action_create_student_profile(self):
        """إنشاء ملف الطالب والعائلة يدوياً"""
        self.ensure_one()

        if self.registration_type != 'new':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'خطأ',
                    'message': 'هذا الإجراء متاح فقط للتسجيلات الجديدة',
                    'type': 'danger',
                    'sticky': False,
                }
            }

        if self.student_profile_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تنبيه',
                    'message': 'تم إنشاء ملف الطالب بالفعل',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # التحقق من البيانات الأساسية
        if not all([self.full_name, self.birth_date, self.gender, self.nationality, self.id_number,
                    self.father_name, self.mother_name, self.father_mobile, self.mother_mobile]):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'خطأ',
                    'message': 'يجب ملء جميع البيانات الأساسية قبل إنشاء ملف الطالب',
                    'type': 'danger',
                    'sticky': False,
                }
            }

        # التحقق من عدم وجود طالب بنفس رقم الهوية
        existing_student = self.env['charity.student.profile'].search([
            ('id_number', '=', self.id_number)
        ], limit=1)

        if existing_student:
            # الطالب موجود بالفعل
            self.registration_type = 'existing'
            self.student_profile_id = existing_student

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تم العثور على الطالب',
                    'message': f'الطالب {existing_student.full_name} موجود بالفعل في النظام برقم الهوية {self.id_number}',
                    'type': 'warning',
                    'sticky': True,
                }
            }

        return self._create_student_and_family()

    def _create_student_and_family(self):
        """إنشاء ملف طالب وعائلة جديد"""
        self.ensure_one()

        if self.registration_type != 'new':
            return {'type': 'ir.actions.do_nothing'}

        # البحث عن عائلة موجودة أولاً
        existing_family = False
        if self.father_mobile or self.mother_mobile:
            # البحث بناءً على رقم هاتف الأب أو الأم
            family_domain = []
            if self.father_mobile:
                family_domain.append(('father_mobile', '=', self.father_mobile))
            if self.mother_mobile:
                if family_domain:
                    family_domain = ['|'] + family_domain + [('mother_mobile', '=', self.mother_mobile)]
                else:
                    family_domain.append(('mother_mobile', '=', self.mother_mobile))

            existing_family = self.env['charity.family.profile'].search(family_domain, limit=1)

        if existing_family:
            # العائلة موجودة - نستخدمها
            family_profile = existing_family

            # تحديث بيانات العائلة إذا كانت ناقصة
            update_vals = {}
            if not existing_family.father_name and self.father_name:
                update_vals['father_name'] = self.father_name
            if not existing_family.father_mobile and self.father_mobile:
                update_vals['father_mobile'] = self.father_mobile
            if not existing_family.mother_name and self.mother_name:
                update_vals['mother_name'] = self.mother_name
            if not existing_family.mother_mobile and self.mother_mobile:
                update_vals['mother_mobile'] = self.mother_mobile
            if not existing_family.mother_whatsapp and self.mother_whatsapp:
                update_vals['mother_whatsapp'] = self.mother_whatsapp
            if not existing_family.email and self.email:
                update_vals['email'] = self.email

            if update_vals:
                existing_family.write(update_vals)

            message = f'تم استخدام العائلة الموجودة: {existing_family.display_name}'
        else:
            # إنشاء عائلة جديدة
            family_vals = {
                'mother_name': self.mother_name,
                'mother_mobile': self.mother_mobile,
                'father_name': self.father_name,
                'father_mobile': self.father_mobile,
                'mother_whatsapp': self.mother_whatsapp,
                'email': self.email,
            }
            family_profile = self.env['charity.family.profile'].create(family_vals)
            message = f'تم إنشاء عائلة جديدة: {family_profile.display_name}'

        # إنشاء ملف الطالب
        student_vals = {
            'full_name': self.full_name,
            'birth_date': self.birth_date,
            'gender': self.gender,
            'nationality': self.nationality.id,
            'id_type': self.id_type,
            'id_number': self.id_number,
            'id_front_file': self.id_front_file,
            'id_front_filename': self.id_front_filename,
            'id_back_file': self.id_back_file,
            'id_back_filename': self.id_back_filename,
            'family_profile_id': family_profile.id,
            'has_health_requirements': self.has_health_requirements,
            'health_requirements': self.health_requirements,
            'photo_consent': self.photo_consent,
        }
        student_profile = self.env['charity.student.profile'].create(student_vals)

        # تحديث التسجيل
        self.registration_type = 'existing'
        self.student_profile_id = student_profile

        # إضافة رسالة في chatter
        self.message_post(
            body=f"{message}<br/>تم إنشاء ملف جديد للطالب {student_profile.full_name}",
            subject="إنشاء ملف طالب"
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم إنشاء ملف الطالب',
                'message': f'{message}\nتم إنشاء ملف جديد للطالب {student_profile.full_name}',
                'type': 'success',
                'sticky': False,
            }
        }

    def _validate_required_fields(self):
        """التحقق من الحقول المطلوبة حسب نوع التسجيل - يتم استدعاؤها عند التأكيد فقط"""
        for record in self:
            if record.registration_type == 'new':
                if not record.full_name:
                    raise ValidationError('يجب إدخال الاسم الثلاثي!')
                if not record.birth_date:
                    raise ValidationError('يجب إدخال تاريخ الميلاد!')
                if not record.gender:
                    raise ValidationError('يجب تحديد الجنس!')
                if not record.nationality:
                    raise ValidationError('يجب تحديد الجنسية!')
                if not record.id_number:
                    raise ValidationError('يجب إدخال رقم الهوية!')
                if not record.mother_name or not record.father_name:
                    raise ValidationError('يجب إدخال أسماء الوالدين!')
                if not record.mother_mobile or not record.father_mobile:
                    raise ValidationError('يجب إدخال أرقام هواتف الوالدين!')
                if not record.photo_consent:
                    raise ValidationError('يجب الموافقة على التصوير!')
                if not record.id_front_file:
                    raise ValidationError('يجب رفع صورة الوجه الأول من الهوية!')
                if not record.id_back_file:
                    raise ValidationError('يجب رفع صورة الوجه الثاني من الهوية!')
            elif record.registration_type == 'existing':
                if not record.student_profile_id:
                    raise ValidationError('يجب اختيار ملف الطالب!')
                # التأكد من وجود full_name للطالب المسجل
                if not record.full_name and record.student_profile_id:
                    record.full_name = record.student_profile_id.full_name

    @api.constrains('id_type', 'id_number')
    def _check_id_number(self):
        """التحقق من صحة رقم الهوية أو الجواز"""
        import re
        for record in self:
            if record.registration_type == 'new' and record.id_number:
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

    @api.constrains('term_id', 'student_profile_id')
    def _check_duplicate_registration(self):
        """منع التسجيل المكرر في نفس الترم"""
        for record in self:
            # للطلاب المسجلين
            if record.registration_type == 'existing' and record.student_profile_id and record.term_id:
                duplicate = self.search([
                    ('student_profile_id', '=', record.student_profile_id.id),
                    ('term_id', '=', record.term_id.id),
                    ('id', '!=', record.id),
                    ('state', '!=', 'cancelled')
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f'الطالب {record.student_profile_id.full_name} مسجل بالفعل في {record.term_id.name}!'
                    )

            # للطلاب الجدد - التحقق برقم الهوية
            elif record.registration_type == 'new' and record.id_number and record.term_id:
                duplicate = self.search([
                    ('id_number', '=', record.id_number),
                    ('term_id', '=', record.term_id.id),
                    ('id', '!=', record.id),
                    ('state', '!=', 'cancelled')
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f'يوجد تسجيل سابق لنفس رقم الهوية في {record.term_id.name}!'
                    )

    @api.constrains('birth_date')
    def _check_birth_date(self):
        """التحقق من صحة تاريخ الميلاد"""
        for record in self:
            if record.registration_type == 'new' and record.birth_date:
                if record.birth_date > date.today():
                    raise ValidationError('تاريخ الميلاد لا يمكن أن يكون في المستقبل!')

    @api.constrains('mother_mobile', 'father_mobile', 'mother_whatsapp')
    def _check_phone_numbers(self):
        """التحقق من صحة أرقام الهواتف"""
        import re
        phone_pattern = re.compile(r'^[\d\s\-\+]+$')

        for record in self:
            if record.registration_type == 'new':
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
            if record.registration_type == 'new' and record.email and not email_pattern.match(record.email):
                raise ValidationError('البريد الإلكتروني غير صحيح!')

    # إزالة constrains القديمة التي تسبب المشاكل

    @api.constrains('id_front_file', 'id_back_file')
    def _check_id_files(self):
        """التحقق من رفع ملفات الهوية"""
        # تم نقل هذا التحقق إلى _validate_required_fields
        pass

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

    def action_view_student_profile(self):
        """فتح ملف الطالب المرتبط"""
        self.ensure_one()
        if not self.student_profile_id:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'ملف الطالب',
            'view_mode': 'form',
            'res_model': 'charity.student.profile',
            'res_id': self.student_profile_id.id,
            'target': 'current',
        }

    def _get_or_create_partner(self):
        """الحصول على أو إنشاء شريك (partner) للطالب"""
        self.ensure_one()

        # التأكد من وجود الاسم
        student_name = self.full_name
        if not student_name and self.student_profile_id:
            student_name = self.student_profile_id.full_name

        if not student_name:
            raise ValidationError('لا يمكن إنشاء فاتورة بدون اسم الطالب!')

        # البحث عن partner موجود للطالب نفسه
        partner = False

        # البحث بناءً على الطالب إذا كان له ملف
        if self.student_profile_id:
            partner = self.env['res.partner'].search([
                ('name', '=', student_name),
                '|',
                ('ref', '=', f'student_{self.student_profile_id.id}'),
                ('comment', 'ilike', f'رقم الهوية: {self.id_number or self.student_profile_id.id_number}')
            ], limit=1)
        elif self.id_number:
            # البحث بناءً على رقم الهوية للطالب
            partner = self.env['res.partner'].search([
                ('name', '=', student_name),
                ('comment', 'ilike', f'رقم الهوية: {self.id_number}')
            ], limit=1)

        if partner:
            return partner

        # جمع بيانات الوالدين
        father_name = self.father_name
        mother_name = self.mother_name
        father_mobile = self.father_mobile
        mother_mobile = self.mother_mobile
        email = self.email

        if self.student_profile_id and self.student_profile_id.family_profile_id:
            family = self.student_profile_id.family_profile_id
            father_name = father_name or family.father_name
            mother_name = mother_name or family.mother_name
            father_mobile = father_mobile or family.father_mobile
            mother_mobile = mother_mobile or family.mother_mobile
            email = email or family.email

        # إنشاء partner جديد للطالب
        partner_vals = {
            'name': student_name,  # اسم الطالب
            'mobile': father_mobile,
            'phone': mother_mobile,
            'email': email,
            'customer_rank': 1,
            'is_company': False,
            'parent_id': False,
            'street': f'الأب: {father_name}' if father_name else '',
            'street2': f'الأم: {mother_name}' if mother_name else '',
            'comment': f'رقم الهوية: {self.id_number or (self.student_profile_id.id_number if self.student_profile_id else "")}\nتاريخ الميلاد: {self.birth_date or (self.student_profile_id.birth_date if self.student_profile_id else "")}',
            'ref': f'student_{self.student_profile_id.id}' if self.student_profile_id else f'temp_{self.id}'
        }

        return self.env['res.partner'].create(partner_vals)

    def _create_invoice(self):
        """إنشاء فاتورة للتسجيل"""
        self.ensure_one()

        if self.invoice_id:
            return False

        # التأكد من وجود الاسم
        student_name = self.full_name
        if not student_name and self.student_profile_id:
            student_name = self.student_profile_id.full_name

        if not student_name:
            raise ValidationError('لا يمكن إنشاء فاتورة بدون اسم الطالب!')

        # الحصول على أو إنشاء Partner
        partner = self._get_or_create_partner()

        # إعداد سطور الفاتورة
        invoice_lines = []

        # سطر الخدمة الأساسي
        main_line_name = f'تسجيل في {self.club_id.name} - {self.term_id.name}'
        if self.sibling_order > 1:
            main_line_name += f' (الطفل رقم {self.sibling_order} في العائلة)'

        invoice_lines.append((0, 0, {
            'name': main_line_name,
            'quantity': 1,
            'price_unit': self.term_price,
            'tax_ids': [(6, 0, [])],  # بدون ضرائب
        }))

        # إضافة سطور الخصومات إذا وجدت
        if self.discount_amount > 0:
            discount_descriptions = []

            if self.sibling_discount_rate > 0:
                discount_descriptions.append(f'خصم الأخوة ({self.sibling_discount_rate}%)')

            if self.multi_club_discount_rate > 0:
                discount_descriptions.append(f'خصم النوادي المتعددة ({self.multi_club_discount_rate}%)')

            if self.half_term_discount_rate > 0:
                discount_descriptions.append(f'خصم نصف الترم ({self.half_term_discount_rate}%)')

            discount_name = 'خصومات: ' + ' + '.join(discount_descriptions)
            discount_name += f' = إجمالي {self.total_discount_rate}%'

            # سطر الخصم (بقيمة سالبة)
            invoice_lines.append((0, 0, {
                'name': discount_name,
                'quantity': 1,
                'price_unit': -self.discount_amount,
                'tax_ids': [(6, 0, [])],
            }))

        # جمع بيانات الوالدين
        father_name = self.father_name
        mother_name = self.mother_name
        if self.student_profile_id and self.student_profile_id.family_profile_id:
            family = self.student_profile_id.family_profile_id
            father_name = father_name or family.father_name
            mother_name = mother_name or family.mother_name

        # إنشاء الفاتورة
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'ref': f'تسجيل الطالب {student_name} - رقم التسجيل {self.id}',
            'narration': f'الأب: {father_name}\nالأم: {mother_name}' if father_name and mother_name else '',
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice

        # تأكيد الفاتورة تلقائياً
        invoice.action_post()

        # إضافة رسالة في الـ chatter
        discount_msg = ""
        if self.discount_amount > 0:
            discount_msg = f"""
            <br/><br/>
            <b>تفاصيل الخصومات المطبقة:</b><br/>
            - السعر الأصلي: {self.term_price} <br/>
            - إجمالي الخصم: {self.total_discount_rate}% ({self.discount_amount})<br/>
            - المبلغ النهائي: {self.final_amount}
            """

        self.message_post(
            body=f"تم إنشاء فاتورة برقم {invoice.name}{discount_msg}",
            subject="إنشاء فاتورة"
        )

        return invoice

    def action_confirm(self):
        """تأكيد التسجيل"""
        self.ensure_one()
        if self.state == 'draft':
            # التحقق من الحقول المطلوبة
            self._validate_required_fields()

            # إنشاء ملف الطالب إذا كان تسجيل جديد
            if self.registration_type == 'new' and not self.student_profile_id:
                self._create_student_and_family()

            # إنشاء الفاتورة
            self._create_invoice()

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
            # إلغاء الفاتورة إذا كانت موجودة وغير مدفوعة
            if self.invoice_id and self.invoice_payment_state != 'paid':
                self.invoice_id.button_cancel()
            self.state = 'cancelled'

    def action_reset_draft(self):
        """إعادة التسجيل إلى مسودة"""
        self.ensure_one()
        self.state = 'draft'

    def action_view_invoice(self):
        """عرض الفاتورة المرتبطة"""
        self.ensure_one()
        if not self.invoice_id:
            return {'type': 'ir.actions.do_nothing'}

        return {
            'type': 'ir.actions.act_window',
            'name': 'الفاتورة',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    def name_get(self):
        """تخصيص طريقة عرض اسم التسجيل"""
        result = []
        for record in self:
            name = f"{record.full_name} - {record.student_grade}" if record.full_name else "تسجيل جديد"
            result.append((record.id, name))
        return result
# -*- coding: utf-8 -*-
import re
import hashlib
import json
import secrets
from datetime import date, datetime, timedelta  # إضافة timedelta هنا
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClubRegistrations(models.Model):
    _name = 'charity.club.registrations'
    _description = 'تسجيلات النوادي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'full_name'
    _order = 'create_date desc'

    registration_number = fields.Char(
        string='رقم التسجيل',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: 'جديد',
        index='btree',
        tracking=True
    )

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
        string='المشترك كان مسجلاً فى بنوادى رؤيتى ',
        default=False,
        help='حدد إذا كان الطالب مشترك سابقاً في نوادي رؤيتي'
    )

    previous_arabic_club = fields.Boolean(
        string='المشترك كان مسجلاً بنوادى اللغة العربية ',
        default=False,
        help='حدد إذا كان الطالب مشترك سابقاً في نادي اللغة العربية'
    )

    previous_qaida_noorania = fields.Boolean(
        string='المشترك تعلم القاعدة النوانية ',
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
        ('pending_review', 'في انتظار المراجعة'),  # حالة جديدة
        ('confirmed', 'مؤكد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي')
    ], string='الحالة',
        default='draft',
        tracking=True,
        help='حالة التسجيل'
    )

    # إضافة حقل لتوضيح سبب المراجعة
    review_reason = fields.Text(
        string='سبب المراجعة',
        readonly=True,
        help='السبب الذي يستدعي مراجعة الإدارة'
    )

    # إضافة حقل للإشارة إلى وجود مشكلة في رقم الهوية
    has_id_conflict = fields.Boolean(
        string='يوجد تعارض في رقم الهوية',
        default=False,
        help='يشير إلى وجود طالب آخر بنفس رقم الهوية'
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

    student_grade_id = fields.Selection(
        selection='_get_grade_selection',
        string='الصف',
        required=True,
        help='اختر الصف الدراسي للطالب'
    )

    how_know_us = fields.Selection([
        ('friend', 'من خلال صديق / أحد المعارف'),
        ('social_media', 'من خلال وسائل التواصل الاجتماعي'),
        ('ads', 'من خلال الإعلانات'),
        ('google', 'عن طريق جوجل أو البحث عبر الإنترنت'),
        ('previous_activity', 'حضرت/حضر طفلي نشاط سابق'),
        ('school', 'من خلال المدرسة أو الحضانة'),
        ('other', 'أخرى')
    ], string='كيف تعرفتم على رؤيتي',
        help='اختر كيف تعرفت على جمعية رؤيتي'
    )

    # خصم بطاقة إسعاد
    esaad_discount = fields.Boolean(
        string='خصم بطاقة إسعاد',
        default=False,
        help='هل لديك بطاقة إسعاد صالحة؟'
    )

    esaad_card_file = fields.Binary(
        string='صورة بطاقة إسعاد',
        attachment=True,
        help='أرفق صورة بطاقة إسعاد - يجب أن تكون البطاقة باسم الطفل المسجل'
    )

    esaad_card_filename = fields.Char(
        string='اسم ملف بطاقة إسعاد'
    )

    esaad_verification_status = fields.Selection([
        ('pending', 'في انتظار التحقق'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض')
    ], string='حالة التحقق من إسعاد',
        default='pending',

        help='حالة التحقق من بطاقة إسعاد'
    )

    esaad_discount_rate = fields.Float(
        string='خصم إسعاد (%)',
        compute='_compute_discounts',
        store=True,
        help='خصم 20% لحاملي بطاقة إسعاد المعتمدة'
    )

    student_grade_display = fields.Char(
        string='الصف',
        compute='_compute_grade_display',
        store=False  # لا نحتاج تخزينه
    )

    @api.depends('student_grade_id')
    def _compute_grade_display(self):
        grades_dict = dict(self._get_grade_selection())
        for record in self:
            record.student_grade_display = grades_dict.get(record.student_grade_id, '')

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

    # عدّل دالة _check_if_needs_book لتصبح:
    def _check_if_needs_book(self):
        """التحقق من احتياج الطالب للكتاب"""
        self.ensure_one()

        # التحقق من أن النادي له كتب
        if not self.club_id.has_books or self.club_id.book_price <= 0:
            return False

        # التحقق من أن صف الطالب من ضمن الصفوف المطبق عليها سعر الكتاب
        if self.student_grade_id:
            student_grade_id = int(self.student_grade_id)
            if student_grade_id not in self.club_id.book_applicable_grades.ids:
                return False
        else:
            return False

        # الحصول على جميع الترمات النشطة للنادي
        active_terms = self.env['charity.club.terms'].search([
            ('club_id', '=', self.club_id.id),
            ('is_active', '=', True)
        ], order='date_from')

        if not active_terms:
            return False

        # تحديد فترة الترمات (من أول ترم إلى آخر ترم)
        period_start = active_terms[0].date_from
        period_end = active_terms[-1].date_to

        # البحث عن تسجيلات سابقة للطالب في نفس النادي خلال نفس الفترة
        domain = [
            ('club_id', '=', self.club_id.id),
            ('id', '!=', self.id),
            ('state', 'not in', ['cancelled', 'rejected']),
            ('term_id.date_from', '>=', period_start),
            ('term_id.date_to', '<=', period_end)
        ]

        if self.student_profile_id:
            domain.append(('student_profile_id', '=', self.student_profile_id.id))
        elif self.id_number:
            domain.append(('id_number', '=', self.id_number))
        else:
            # إذا لم يكن هناك معرف للطالب، نعتبره طالب جديد
            return True

        previous_registrations = self.search(domain)

        # إذا لم توجد تسجيلات سابقة، يحتاج الكتاب
        return not bool(previous_registrations)

    @api.depends('student_profile_id', 'term_id', 'state', 'father_mobile', 'mother_mobile')
    def _compute_sibling_order(self):
        """حساب ترتيب الطفل بين إخوته - نسخة محسنة"""
        for record in self:
            if record.state == 'cancelled':
                record.sibling_order = 0
                continue

            # الحصول على هوية العائلة
            family_phones = []
            if record.father_mobile:
                family_phones.append(record.father_mobile)
            if record.mother_mobile:
                family_phones.append(record.mother_mobile)

            if not family_phones:
                record.sibling_order = 1
                continue

            # البحث عن جميع التسجيلات النشطة لنفس العائلة
            today = fields.Date.today()
            domain = [
                ('state', 'not in', ['cancelled', 'rejected']),
                ('term_id.date_to', '>=', today),
                ('term_id.is_active', '=', True),
                '|',
                ('father_mobile', 'in', family_phones),
                ('mother_mobile', 'in', family_phones)
            ]

            active_registrations = self.search(domain)

            # تجميع حسب رقم الهوية الفريد
            unique_children = {}
            for reg in active_registrations:
                # استخدم رقم الهوية كمعرف فريد
                if reg.id_number:
                    if reg.id_number not in unique_children:
                        unique_children[reg.id_number] = reg
                    elif reg.registration_date < unique_children[reg.id_number].registration_date:
                        unique_children[reg.id_number] = reg

            # ترتيب الأطفال حسب تاريخ أول تسجيل
            sorted_children = sorted(unique_children.values(),
                                     key=lambda r: r.registration_date or fields.Datetime.now())

            # إيجاد ترتيب الطفل الحالي
            sibling_order = 1
            for idx, child in enumerate(sorted_children, 1):
                if child.id_number == record.id_number:
                    sibling_order = idx
                    break

            record.sibling_order = sibling_order

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

    @api.depends('sibling_order', 'has_multi_club', 'is_half_term', 'term_price', 'discount_policy', 'esaad_discount',
                 'esaad_verification_status')
    def _compute_discounts(self):
        """حساب جميع الخصومات بما فيها خصم إسعاد"""
        for record in self:
            if not record.term_price or record.state == 'cancelled':
                record.sibling_discount_rate = 0
                record.multi_club_discount_rate = 0
                record.half_term_discount_rate = 0
                record.esaad_discount_rate = 0
                record.total_discount_rate = 0
                record.discount_amount = 0
                record.final_amount = record.term_price or 0
                continue

            # التحقق من خصم إسعاد أولاً
            if record.esaad_discount and record.esaad_verification_status == 'approved':
                # إذا كان خصم إسعاد معتمد، نطبقه فقط ونلغي باقي الخصومات
                record.sibling_discount_rate = 0
                record.multi_club_discount_rate = 0
                record.half_term_discount_rate = 0
                record.esaad_discount_rate = 20  # خصم إسعاد 20% فقط
                record.total_discount_rate = 20

                # حساب المبالغ
                record.discount_amount = (record.term_price * 20) / 100
                record.final_amount = record.term_price - record.discount_amount
            else:
                # حساب الخصومات العادية إذا لم يكن هناك خصم إسعاد معتمد

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

                # خصم إسعاد غير معتمد أو غير موجود
                record.esaad_discount_rate = 0

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

    def action_reject_esaad(self):
        """رفض بطاقة إسعاد"""
        self.ensure_one()
        if self.state == 'pending_review' and self.esaad_discount:
            self.esaad_verification_status = 'rejected'
            self.message_post(
                body="تم رفض بطاقة إسعاد",
                subject="رفض بطاقة إسعاد"
            )
            # إعادة حساب الخصومات
            self._compute_discounts()

    def action_approve_esaad(self):
        """اعتماد بطاقة إسعاد"""
        self.ensure_one()
        if self.state == 'pending_review' and self.esaad_discount:
            self.esaad_verification_status = 'approved'

            # إعادة حساب الخصومات (ستطبق خصم إسعاد فقط)
            self._compute_discounts()

            self.message_post(
                body="""<div style="background-color: #e3f2fd; border: 1px solid #2196f3; padding: 10px; border-radius: 5px;">
                    <strong>✅ تم اعتماد بطاقة إسعاد</strong><br/>
                    <strong>⚠️ تنبيه مهم:</strong> خصم إسعاد (20%) سيلغي جميع الخصومات الأخرى<br/>
                    الخصومات الملغاة:
                    <ul>
                        <li>خصم الأخوة: {:.0f}%</li>
                        <li>خصم النوادي المتعددة: {:.0f}%</li>
                        <li>خصم نصف الترم: {:.0f}%</li>
                    </ul>
                    <strong>الخصم النهائي: 20% فقط</strong>
                </div>""".format(
                    self.sibling_discount_rate if self.sibling_order > 1 else 0,
                    15 if self.has_multi_club else 0,
                    50 if self.is_half_term else 0
                ),
                subject="اعتماد بطاقة إسعاد"
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'نجاح',
                    'message': 'تم اعتماد بطاقة إسعاد - سيتم تطبيق خصم 20% فقط وإلغاء باقي الخصومات',
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_create_invoice_with_esaad(self):
        """إنشاء فاتورة مع خصم إسعاد المعتمد (يلغي جميع الخصومات الأخرى)"""
        self.ensure_one()

        # التحقق من الشروط
        if not self.esaad_discount or self.esaad_verification_status != 'approved':
            raise ValidationError('يجب أن تكون بطاقة إسعاد معتمدة لإنشاء الفاتورة!')

        if self.state != 'confirmed':
            raise ValidationError('يجب أن يكون التسجيل مؤكد لإنشاء الفاتورة!')

        if self.invoice_id:
            raise ValidationError('توجد فاتورة بالفعل لهذا التسجيل!')

        # إعادة حساب الخصومات للتأكد (ستطبق خصم إسعاد فقط)
        self._compute_discounts()

        # إنشاء الفاتورة
        invoice = self._create_invoice()

        # ترحيل الفاتورة
        if invoice and invoice.state == 'draft':
            invoice.action_post()
            self.message_post(
                body=f"""<div style="background-color: #e8f5e9; border: 1px solid #4caf50; padding: 10px; border-radius: 5px;">
                    <strong>✅ تم إنشاء وترحيل الفاتورة {invoice.name}</strong><br/>
                    <strong>خصم إسعاد: {self.esaad_discount_rate}%</strong><br/>
                    <em>ملاحظة: خصم إسعاد يلغي جميع الخصومات الأخرى</em><br/>
                    المبلغ الأصلي: {self.term_price:.2f} درهم<br/>
                    المبلغ بعد الخصم: {self.final_amount:.2f} درهم
                </div>""",
                subject="إنشاء فاتورة مع خصم إسعاد"
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'نجاح',
                'message': f'تم إنشاء الفاتورة بنجاح مع خصم إسعاد {self.esaad_discount_rate}% (بدون خصومات أخرى)',
                'type': 'success',
                'sticky': False,
            }
        }

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
        """إنشاء ملف طالب وعائلة جديد مع التعامل الذكي مع البيانات الموجودة"""
        self.ensure_one()

        if self.registration_type != 'new':
            return {'type': 'ir.actions.do_nothing'}

        # التحقق من وجود طالب بنفس رقم الهوية أولاً
        existing_student = self.env['charity.student.profile'].search([
            ('id_number', '=', self.id_number)
        ], limit=1)

        if existing_student:
            # الطالب موجود بالفعل - نستخدمه ونحول التسجيل إلى existing
            self.registration_type = 'existing'
            self.student_profile_id = existing_student

            # تحديث بيانات الطالب إذا كانت ناقصة
            student_updates = {}
            if not existing_student.full_name and self.full_name:
                student_updates['full_name'] = self.full_name
            if not existing_student.birth_date and self.birth_date:
                student_updates['birth_date'] = self.birth_date
            if not existing_student.gender and self.gender:
                student_updates['gender'] = self.gender
            if not existing_student.nationality and self.nationality:
                student_updates['nationality'] = self.nationality.id
            if not existing_student.id_front_file and self.id_front_file:
                student_updates['id_front_file'] = self.id_front_file
                student_updates['id_front_filename'] = self.id_front_filename
            if not existing_student.id_back_file and self.id_back_file:
                student_updates['id_back_file'] = self.id_back_file
                student_updates['id_back_filename'] = self.id_back_filename

            if student_updates:
                existing_student.write(student_updates)

            # تحديث بيانات العائلة إذا لزم الأمر
            if existing_student.family_profile_id:
                family_profile = existing_student.family_profile_id
                family_updates = {}

                if not family_profile.father_name and self.father_name:
                    family_updates['father_name'] = self.father_name
                if not family_profile.father_mobile and self.father_mobile:
                    family_updates['father_mobile'] = self.father_mobile
                if not family_profile.mother_name and self.mother_name:
                    family_updates['mother_name'] = self.mother_name
                if not family_profile.mother_mobile and self.mother_mobile:
                    family_updates['mother_mobile'] = self.mother_mobile
                if not family_profile.mother_whatsapp and self.mother_whatsapp:
                    family_updates['mother_whatsapp'] = self.mother_whatsapp
                if not family_profile.email and self.email:
                    family_updates['email'] = self.email

                if family_updates:
                    family_profile.write(family_updates)

            # إضافة رسالة في chatter
            self.message_post(
                body=f"تم ربط التسجيل بملف الطالب الموجود: {existing_student.full_name}",
                subject="ربط بملف طالب موجود"
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تم العثور على الطالب',
                    'message': f'الطالب {existing_student.full_name} موجود بالفعل في النظام وتم ربط التسجيل به',
                    'type': 'info',
                    'sticky': False,
                }
            }

        # إذا لم يكن الطالب موجوداً، نكمل بإنشاء طالب جديد
        # البحث عن عائلة موجودة أولاً
        existing_family = False
        if self.father_mobile or self.mother_mobile:
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
            family_profile = existing_family
            message = f'تم استخدام العائلة الموجودة: {existing_family.display_name}'

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

        # إنشاء ملف الطالب الجديد
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

                if not record.id_front_file:
                    raise ValidationError('يجب رفع صورة الوجه الأول من الهوية!')
                if not record.id_back_file:
                    raise ValidationError('يجب رفع صورة الوجه الثاني من الهوية!')
                if record.esaad_discount and not record.esaad_card_file:
                    raise ValidationError('يجب رفع صورة بطاقة إسعاد عند طلب الخصم!')
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

    @api.constrains('term_id', 'student_profile_id', 'id_number')
    def _check_duplicate_registration(self):
        """منع التسجيل المكرر في نفس الترم - محسّن"""
        for record in self:
            if not record.term_id:
                continue

            # للطلاب المسجلين
            if record.registration_type == 'existing' and record.student_profile_id:
                duplicate = self.search([
                    ('student_profile_id', '=', record.student_profile_id.id),
                    ('term_id', '=', record.term_id.id),
                    ('id', '!=', record.id),
                    ('state', 'not in', ['cancelled', 'rejected'])
                ], limit=1)

                if duplicate:
                    raise ValidationError(
                        f'❌ خطأ: الطالب {record.student_profile_id.full_name} مسجل بالفعل في {record.term_id.name}!\n'
                        f'رقم التسجيل: {duplicate.registration_number}'
                    )

            # للطلاب الجدد - التحقق برقم الهوية
            elif record.registration_type == 'new' and record.id_number:
                # البحث عن أي تسجيل بنفس رقم الهوية في نفس الترم
                duplicate = self.search([
                    ('id_number', '=', record.id_number),
                    ('term_id', '=', record.term_id.id),
                    ('id', '!=', record.id),
                    ('state', 'not in', ['cancelled', 'rejected'])
                ], limit=1)

                if duplicate:
                    student_name = duplicate.full_name or duplicate.student_profile_id.full_name if duplicate.student_profile_id else 'غير محدد'
                    raise ValidationError(
                        f'❌ خطأ: رقم الهوية {record.id_number} مسجل بالفعل في {record.term_id.name}!\n'
                        f'اسم الطالب المسجل: {student_name}\n'
                        f'رقم التسجيل: {duplicate.registration_number}\n\n'
                        f'لا يمكن تسجيل نفس الطالب مرتين في نفس الترم.'
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

    def get_attachment_url(self, field_name):
        """الحصول على رابط المرفق"""
        self.ensure_one()
        if field_name == 'id_front':
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('res_field', '=', 'id_front_file')
            ], limit=1)
        elif field_name == 'id_back':
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('res_field', '=', 'id_back_file')
            ], limit=1)
        elif field_name == 'esaad':
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('res_field', '=', 'esaad_card_file')
            ], limit=1)
        else:
            return False

        if attachment:
            return f'/web/content/{attachment.id}'
        return False

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

            'comment': f'رقم الهوية: {self.id_number or (self.student_profile_id.id_number if self.student_profile_id else "")}\nتاريخ الميلاد: {self.birth_date or (self.student_profile_id.birth_date if self.student_profile_id else "")}',
            'ref': f'student_{self.student_profile_id.id}' if self.student_profile_id else f'temp_{self.id}'
        }

        return self.env['res.partner'].create(partner_vals)

    def _prepare_invoice_line_description(self):
        """إعداد وصف سطر الفاتورة مع تفاصيل الخصومات"""
        self.ensure_one()

        description = f'تسجيل في {self.club_id.name} - {self.term_id.name}'

        if self.registration_number and self.registration_number != 'جديد':
            description = f'[{self.registration_number}] {description}'

        # إضافة تفاصيل الخصومات
        if self.total_discount_rate > 0:
            description += "\n\n📊 تفاصيل الخصومات:"

            if self.sibling_discount_rate > 0:
                description += f"\n• خصم الأخوة (الطفل #{self.sibling_order}): {self.sibling_discount_rate}%"

            if self.multi_club_discount_rate > 0:
                description += f"\n• خصم النوادي المتعددة: {self.multi_club_discount_rate}%"

            if self.half_term_discount_rate > 0:
                description += f"\n• خصم نصف الترم: {self.half_term_discount_rate}%"

            if self.esaad_discount_rate > 0:
                description += f"\n• خصم بطاقة إسعاد: {self.esaad_discount_rate}%"

            description += f"\n────────────────"
            description += f"\nإجمالي الخصم: {self.total_discount_rate}%"

        return description

    def _create_invoice(self):
        """إنشاء فاتورة مع خصم مباشر وضريبة VAT"""
        self.ensure_one()

        if self.invoice_id:
            return self.invoice_id

        # التأكد من وجود الاسم
        student_name = self.full_name
        if not student_name and self.student_profile_id:
            student_name = self.student_profile_id.full_name

        if not student_name:
            raise ValidationError('لا يمكن إنشاء فاتورة بدون اسم الطالب!')

        # الحصول على أو إنشاء Partner
        partner = self._get_or_create_partner()

        # البحث عن ضريبة VAT 5%
        vat_tax = self.env['account.tax'].sudo().search([
            ('amount', '=', 5),
            ('amount_type', '=', 'percent'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_id.id),
            ('active', '=', True)
        ], limit=1)

        if not vat_tax:
            # إنشاء ضريبة VAT إذا لم توجد
            tax_group = self.env.ref('account.tax_group_taxes', raise_if_not_found=False)
            vat_tax = self.env['account.tax'].sudo().create({
                'name': 'VAT 5%',
                'amount': 5.0,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
                'company_id': self.company_id.id,
                'price_include': False,
                'tax_group_id': tax_group.id if tax_group else False,
            })

        # بناء وصف تفصيلي للسطر الأساسي
        main_line_description = f'تسجيل في {self.club_id.name} - {self.term_id.name}'
        if self.registration_number and self.registration_number != 'جديد':
            main_line_description = f'[{self.registration_number}] {main_line_description}'

        # إضافة تفاصيل الخصومات في الوصف
        if self.total_discount_rate > 0:
            main_line_description += "\n\n【 تفاصيل الخصومات المطبقة 】"

            if self.sibling_discount_rate > 0:
                main_line_description += f"\n ◆ خصم الأخوة (الطفل رقم {self.sibling_order}): {self.sibling_discount_rate}%"

            if self.multi_club_discount_rate > 0:
                main_line_description += f"\n ◆ خصم النوادي المتعددة: {self.multi_club_discount_rate}%"

            if self.half_term_discount_rate > 0:
                main_line_description += f"\n ◆ خصم نصف الترم: {self.half_term_discount_rate}%"

            if self.esaad_discount_rate > 0:
                main_line_description += f"\n ◆ خصم بطاقة إسعاد المعتمدة: {self.esaad_discount_rate}%"

            main_line_description += f"\n ━━━━━━━━━━━━━━━"
            main_line_description += f"\n ← إجمالي نسبة الخصم: {self.total_discount_rate}%"

        # إعداد سطور الفاتورة
        invoice_lines = []

        # السطر الأساسي للترم مع الخصم المباشر
        invoice_lines.append((0, 0, {
            'name': main_line_description,
            'quantity': 1,
            'price_unit': self.term_price,
            'discount': self.total_discount_rate,  # النسبة الإجمالية للخصم
            'tax_ids': [(6, 0, [vat_tax.id])]  # ضريبة 5%
        }))

        # سطر الكتاب (إن وجد) - بدون خصم
        needs_book = self._check_if_needs_book()
        if needs_book:
            invoice_lines.append((0, 0, {
                'name': f'كتاب {self.club_id.name}',
                'quantity': 1,
                'price_unit': self.club_id.book_price,
                'discount': 0,  # بدون خصم على الكتاب
                'tax_ids': [(6, 0, [vat_tax.id])]  # نفس الضريبة 5%
            }))

        # جمع بيانات الوالدين
        father_name = self.father_name
        mother_name = self.mother_name
        if self.student_profile_id and self.student_profile_id.family_profile_id:
            family = self.student_profile_id.family_profile_id
            father_name = father_name or family.father_name
            mother_name = mother_name or family.mother_name

        # ====== حساب الإجمالي النهائي مع الضريبة (ننقلها هنا قبل استخدامها) ======
        subtotal_after_discount = self.final_amount
        if needs_book:
            subtotal_after_discount += self.club_id.book_price

        vat_amount = subtotal_after_discount * 0.05
        total_with_vat = subtotal_after_discount + vat_amount
        # ===========================================================================

        # إعداد narration للفاتورة
        narration = ""

        narration += f"◈ رقم التسجيل: {self.registration_number}\n"
        narration += f"◈ الطالب: {student_name}\n"
        narration += f"◈ الأب: {father_name or 'غير محدد'}\n"
        narration += f"◈ الأم: {mother_name or 'غير محدد'}\n"



        # إنشاء الفاتورة
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'ref': f'تسجيل رقم: {self.registration_number}',
            'narration': narration,
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice

        # إضافة رسالة في الـ chatter
        message_body = f"""
        <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; border: 1px solid #b0d4ff;">
            <h4 style="color: #0066cc; margin-bottom: 10px;">
                <i class="fa fa-file-invoice"></i> تم إنشاء فاتورة رقم {invoice.name}
            </h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px;"><strong>رقم التسجيل:</strong></td>
                    <td style="padding: 5px;">{self.registration_number}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>المبلغ قبل الخصم:</strong></td>
                    <td style="padding: 5px;">{self.term_price:.2f} درهم</td>
                </tr>
        """

        if self.total_discount_rate > 0:
            message_body += f"""
                <tr>
                    <td style="padding: 5px;"><strong>نسبة الخصم:</strong></td>
                    <td style="padding: 5px;">{self.total_discount_rate}%</td>
                </tr>
            """

        if needs_book:
            message_body += f"""
                <tr>
                    <td style="padding: 5px;"><strong>كتاب النادي:</strong></td>
                    <td style="padding: 5px;">{self.club_id.book_price:.2f} درهم</td>
                </tr>
            """

        message_body += f"""
                <tr>
                    <td style="padding: 5px;"><strong>المبلغ النهائي (شامل VAT):</strong></td>
                    <td style="padding: 5px; color: #009900; font-weight: bold;">{total_with_vat:.2f} درهم</td>
                </tr>
            </table>
        </div>
        """

        self.message_post(
            body=message_body,
            subject=f"فاتورة التسجيل {self.registration_number}"
        )

        return invoice

    def action_confirm(self):
        """تأكيد التسجيل مع منع التكرار نهائياً"""
        self.ensure_one()
        if self.state == 'draft':
            # التحقق من الحقول المطلوبة
            self._validate_required_fields()

            # ===== منع التسجيل المكرر في نفس الترم - قبل أي معالجة =====
            if self.term_id:
                # للطلاب المسجلين
                if self.registration_type == 'existing' and self.student_profile_id:
                    duplicate = self.search([
                        ('student_profile_id', '=', self.student_profile_id.id),
                        ('term_id', '=', self.term_id.id),
                        ('id', '!=', self.id if self.id else 0),
                        ('state', 'not in', ['cancelled', 'rejected'])
                    ], limit=1)

                    if duplicate:
                        raise ValidationError(
                            f'❌ لا يمكن التسجيل!\n\n'
                            f'الطالب {self.student_profile_id.full_name} مسجل بالفعل في {self.term_id.name}.\n'
                            f'رقم التسجيل السابق: {duplicate.registration_number}\n'
                            f'تاريخ التسجيل: {duplicate.registration_date.strftime("%Y-%m-%d") if duplicate.registration_date else ""}\n\n'
                            f'إذا كنت تريد تعديل التسجيل السابق، يرجى التواصل مع الإدارة.'
                        )

                # للطلاب الجدد - التحقق برقم الهوية
                elif self.registration_type == 'new' and self.id_number:
                    # البحث عن أي تسجيل بنفس رقم الهوية في نفس الترم
                    duplicate = self.search([
                        ('id_number', '=', self.id_number),
                        ('term_id', '=', self.term_id.id),
                        ('id', '!=', self.id if self.id else 0),
                        ('state', 'not in', ['cancelled', 'rejected'])
                    ], limit=1)

                    if duplicate:
                        student_name = duplicate.full_name or (
                            duplicate.student_profile_id.full_name if duplicate.student_profile_id else 'غير محدد')
                        raise ValidationError(
                            f'❌ لا يمكن التسجيل!\n\n'
                            f'رقم الهوية {self.id_number} مسجل بالفعل في {self.term_id.name}.\n'
                            f'اسم الطالب المسجل: {student_name}\n'
                            f'رقم التسجيل السابق: {duplicate.registration_number}\n'
                            f'تاريخ التسجيل: {duplicate.registration_date.strftime("%Y-%m-%d") if duplicate.registration_date else ""}\n\n'
                            f'لا يمكن تسجيل نفس الطالب مرتين في نفس الترم.\n'
                            f'إذا كنت تريد تعديل التسجيل السابق، يرجى التواصل مع الإدارة.'
                        )

            # متغير لتحديد إذا كان يحتاج مراجعة
            needs_review = False
            review_reasons = []

            # التحقق من خصم إسعاد
            if self.esaad_discount:
                if not self.esaad_card_file:
                    raise ValidationError('يجب رفع صورة بطاقة إسعاد!')

                needs_review = True
                review_reasons.append("يحتاج مراجعة بطاقة إسعاد للتحقق من صحتها ومطابقتها لاسم الطفل")

                self.message_post(
                    body="""<div style="background-color: #e3f2fd; border: 1px solid #1976d2; padding: 10px; border-radius: 5px;">
                        <strong>📋 يحتاج مراجعة بطاقة إسعاد</strong><br/>
                        تم طلب خصم بطاقة إسعاد. سيتم مراجعة البطاقة والتحقق من:<br/>
                        <ul>
                            <li>صحة البطاقة وصلاحيتها</li>
                            <li>مطابقة اسم حامل البطاقة مع اسم الطفل المسجل</li>
                        </ul>
                        <strong>تنبيه:</strong> سيتم التواصل معك بعد التحقق من البطاقة.
                    </div>""",
                    subject="مراجعة بطاقة إسعاد",
                    message_type='notification'
                )

            # إنشاء ملف الطالب إذا كان تسجيل جديد
            if self.registration_type == 'new' and not self.student_profile_id:
                # التحقق من وجود طالب بنفس رقم الهوية
                existing_student = self.env['charity.student.profile'].search([
                    ('id_number', '=', self.id_number)
                ], limit=1)

                if existing_student:
                    # مقارنة الأسماء
                    if existing_student.full_name.strip().lower() == self.full_name.strip().lower():
                        # نفس الطالب - نستخدم الملف الموجود
                        self.registration_type = 'existing'
                        self.student_profile_id = existing_student

                        self.message_post(
                            body=f"تم ربط التسجيل بملف الطالب الموجود: {existing_student.full_name}",
                            subject="ربط بملف طالب موجود"
                        )

                        # === التحقق مرة أخرى من عدم وجود تسجيل مكرر بعد الربط ===
                        duplicate_after_link = self.search([
                            ('student_profile_id', '=', existing_student.id),
                            ('term_id', '=', self.term_id.id),
                            ('id', '!=', self.id if self.id else 0),
                            ('state', 'not in', ['cancelled', 'rejected'])
                        ], limit=1)

                        if duplicate_after_link:
                            raise ValidationError(
                                f'❌ لا يمكن التسجيل!\n\n'
                                f'بعد ربط البيانات، تبين أن الطالب {existing_student.full_name} مسجل بالفعل في {self.term_id.name}.\n'
                                f'رقم التسجيل السابق: {duplicate_after_link.registration_number}\n\n'
                                f'لا يمكن تسجيل نفس الطالب مرتين في نفس الترم.'
                            )
                    else:
                        # اسم مختلف - يحتاج مراجعة الإدارة
                        needs_review = True
                        self.has_id_conflict = True
                        review_reasons.append(
                            f"رقم الهوية {self.id_number} مسجل بالفعل للطالب: {existing_student.full_name}\n"
                            f"الاسم المدخل: {self.full_name}"
                        )

                        self.message_post(
                            body=f"""<div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px;">
                                <strong>⚠️ تنبيه: يحتاج مراجعة الإدارة</strong><br/>
                                رقم الهوية {self.id_number} مسجل بالفعل للطالب {existing_student.full_name}<br/>
                                الاسم المدخل في هذا التسجيل: {self.full_name}<br/>
                                <br/>
                                <strong>الإجراءات المطلوبة:</strong>
                                <ul>
                                    <li>التواصل مع ولي الأمر للتحقق من البيانات</li>
                                    <li>تحديد إذا كان خطأ في الإدخال أم طالب جديد</li>
                                    <li>اتخاذ القرار المناسب (تعديل البيانات أو إنشاء ملف جديد)</li>
                                </ul>
                            </div>""",
                            subject="تعارض في رقم الهوية - يحتاج مراجعة",
                            message_type='notification'
                        )
                else:
                    # لا يوجد طالب بنفس رقم الهوية - ننشئ ملف جديد
                    self._create_student_and_family()

                    # === التحقق النهائي بعد إنشاء ملف الطالب ===
                    if self.student_profile_id:
                        final_duplicate_check = self.search([
                            '|',
                            ('student_profile_id', '=', self.student_profile_id.id),
                            ('id_number', '=', self.id_number),
                            ('term_id', '=', self.term_id.id),
                            ('id', '!=', self.id if self.id else 0),
                            ('state', 'not in', ['cancelled', 'rejected'])
                        ], limit=1)

                        if final_duplicate_check:
                            raise ValidationError(
                                f'❌ لا يمكن التسجيل!\n\n'
                                f'تم اكتشاف تسجيل مكرر للطالب في {self.term_id.name}.\n'
                                f'رقم التسجيل السابق: {final_duplicate_check.registration_number}\n\n'
                                f'يرجى التواصل مع الإدارة.'
                            )

            # تحديد الحالة النهائية
            if needs_review:
                self.state = 'pending_review'
                self.review_reason = '\n'.join(review_reasons)

                # في حالة خصم إسعاد، لا نقوم بإنشاء فاتورة الآن
                if not self.esaad_discount:
                    # إنشاء الفاتورة للحالات الأخرى التي تحتاج مراجعة
                    invoice = self._create_invoice()

            else:
                # التأكيد العادي - لا يوجد خصم إسعاد ولا مشاكل أخرى
                self.state = 'confirmed'

                # إنشاء الفاتورة
                invoice = self._create_invoice()

                # ترحيل الفاتورة
                if self.invoice_id and self.invoice_id.state == 'draft':
                    self.invoice_id.action_post()
                    self.message_post(
                        body=f"تم ترحيل الفاتورة {self.invoice_id.name}",
                        subject="ترحيل الفاتورة"
                    )

    def action_confirm_after_review(self):
        """تأكيد التسجيل بعد المراجعة من الإدارة"""
        self.ensure_one()
        if self.state == 'pending_review':
            # إنشاء ملف طالب إذا قررت الإدارة ذلك
            if self.registration_type == 'new' and not self.student_profile_id:
                # يمكن للإدارة اختيار:
                # 1. إنشاء ملف طالب جديد
                # 2. ربط بملف موجود
                # 3. تعديل البيانات
                pass

            self.state = 'confirmed'
            self.has_id_conflict = False

            # التحقق من حالة خصم إسعاد
            if self.esaad_discount:
                if self.esaad_verification_status == 'rejected':
                    # إذا كانت بطاقة إسعاد مرفوضة، ننشئ فاتورة بدون خصم إسعاد
                    # نعيد حساب الخصومات أولاً (ستكون بدون خصم إسعاد)
                    self._compute_discounts()

                    # إنشاء الفاتورة بدون خصم إسعاد
                    if not self.invoice_id:
                        invoice = self._create_invoice()

                    # ترحيل الفاتورة
                    if self.invoice_id and self.invoice_id.state == 'draft':
                        self.invoice_id.action_post()
                        self.message_post(
                            body=f"تم إنشاء وترحيل الفاتورة {self.invoice_id.name} (بدون خصم إسعاد - البطاقة مرفوضة)",
                            subject="فاتورة بدون خصم إسعاد"
                        )
                elif self.esaad_verification_status == 'approved':
                    # إذا كانت معتمدة، ننتظر الضغط على زر إنشاء الفاتورة مع خصم إسعاد
                    self.message_post(
                        body="تم اعتماد بطاقة إسعاد. اضغط على زر 'إنشاء فاتورة مع خصم إسعاد' لإنشاء الفاتورة",
                        subject="بطاقة إسعاد معتمدة"
                    )
                else:  # pending
                    # إذا كانت لا تزال قيد المراجعة
                    self.message_post(
                        body="تم تأكيد التسجيل لكن بطاقة إسعاد لا تزال قيد المراجعة",
                        subject="في انتظار مراجعة إسعاد"
                    )
            else:
                # لا يوجد خصم إسعاد - ننشئ وترحل الفاتورة عادي
                if not self.invoice_id:
                    invoice = self._create_invoice()

                if self.invoice_id and self.invoice_id.state == 'draft':
                    self.invoice_id.action_post()
                    self.message_post(
                        body=f"تم ترحيل الفاتورة {self.invoice_id.name}",
                        subject="ترحيل الفاتورة"
                    )

            self.message_post(
                body="تم تأكيد التسجيل بعد المراجعة",
                subject="تأكيد بعد المراجعة"
            )

    def action_reject_after_review(self):
        """رفض التسجيل بعد المراجعة"""
        self.ensure_one()
        if self.state == 'pending_review':
            self.state = 'rejected'

            # إلغاء الفاتورة إذا كانت موجودة
            if self.invoice_id and self.invoice_id.state == 'draft':
                self.invoice_id.button_cancel()

            self.message_post(
                body="تم رفض التسجيل بعد المراجعة",
                subject="رفض بعد المراجعة"
            )

    def _get_discount_product(self):
        """الحصول على منتج الخصومات"""
        # البحث عن منتج مُعرّف كمنتج خصومات
        discount_product = self.env['product.product'].search([
            ('is_discount_product', '=', True),
            ('type', '=', 'service'),
            ('active', '=', True)
        ], limit=1)

        if not discount_product:
            # إنشاء منتج خصومات افتراضي إذا لم يكن موجود
            discount_product = self.env['product.product'].create({
                'name': 'خصومات',
                'type': 'service',
                'is_discount_product': True,
                'sale_ok': True,
                'purchase_ok': False,
                'list_price': 0.0,
                'standard_price': 0.0,
                'categ_id': self.env.ref('product.product_category_all').id,
            })

        return discount_product

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
        """تخصيص طريقة عرض اسم التسجيل مع الرقم"""
        result = []
        for record in self:
            if record.registration_number and record.registration_number != 'جديد':
                if record.full_name:
                    name = f"{record.registration_number} - {record.full_name}"
                else:
                    name = record.registration_number
            else:
                name = f"{record.full_name}" if record.full_name else "تسجيل جديد"
            result.append((record.id, name))
        return result



    @api.model
    def _get_grade_selection(self):
        grades = []
        # جيب كل الصفوف من الجدول
        all_grades = self.env['school.grade'].search([])
        for grade in all_grades:
            grades.append((str(grade.id), grade.name))
        return grades

    # استبدل دالة create الموجودة بهذه

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate registration number"""
        for vals in vals_list:
            # إنشاء رقم التسجيل للسجلات الجديدة فقط
            if not vals.get('registration_number') or vals.get('registration_number') == 'جديد':
                # استخدام with_context للتأكد من عمل الـ sequence
                vals['registration_number'] = self.env['ir.sequence'].with_context(
                    ir_sequence_date=fields.Date.today()
                ).next_by_code('charity.club.registrations') or 'جديد'


        return super(ClubRegistrations, self).create(vals_list)

    def write(self, vals):
        """منع تحديث رقم هوية خاطئ"""
        if 'id_number' in vals or 'id_type' in vals:
            for record in self:
                if record.registration_type == 'new':
                    id_type = vals.get('id_type', record.id_type)
                    id_number = vals.get('id_number', record.id_number)

                    if id_number:
                        if id_type == 'emirates_id':
                            clean_id = id_number.replace('-', '').replace(' ', '').strip()
                            emirates_id_pattern = re.compile(r'^784-\d{4}-\d{7}-\d$')

                            if not emirates_id_pattern.match(id_number):
                                if not (len(clean_id) == 15 and clean_id.startswith('784') and clean_id.isdigit()):
                                    raise ValidationError(
                                        'لا يمكن تحديث التسجيل برقم هوية خاطئ!'
                                    )
                                else:
                                    vals[
                                        'id_number'] = f"{clean_id[0:3]}-{clean_id[3:7]}-{clean_id[7:14]}-{clean_id[14]}"

                        elif id_type == 'passport':
                            passport_pattern = re.compile(r'^[A-Z0-9]{6,9}$')
                            if not passport_pattern.match(id_number.upper()):
                                raise ValidationError(
                                    'لا يمكن تحديث التسجيل برقم جواز خاطئ!'
                                )
                            vals['id_number'] = id_number.upper()

        return super().write(vals)

    @api.constrains('id_type', 'id_number', 'registration_type')
    def _check_id_number_format(self):
        """التحقق النهائي من صحة رقم الهوية"""
        for record in self:
            if record.registration_type == 'new' and record.id_number:
                if record.id_type == 'emirates_id':
                    emirates_id_pattern = re.compile(r'^784-\d{4}-\d{7}-\d$')
                    if not emirates_id_pattern.match(record.id_number):
                        raise ValidationError(
                            f'رقم الهوية {record.id_number} غير صحيح!\n'
                            'الصيغة الصحيحة: 784-YYYY-XXXXXXX-X'
                        )

                elif record.id_type == 'passport':
                    passport_pattern = re.compile(r'^[A-Z0-9]{6,9}$')
                    if not passport_pattern.match(record.id_number):
                        raise ValidationError(
                            f'رقم جواز السفر {record.id_number} غير صحيح!'
                        )


class SchoolGrade(models.Model):
    _name = 'school.grade'
    _description = 'الصفوف الدراسية'

    name = fields.Char(string='اسم الصف', required=True)




class RegistrationValidationToken(models.Model):
    _name = 'registration.validation.token'
    _description = 'Registration Validation Tokens'
    _rec_name = 'token'

    token = fields.Char(
        string='Token',
        required=True,
        index=True,
        default=lambda self: self._generate_token()
    )

    registration_type = fields.Selection([
        ('club', 'نادي'),
        ('nursery', 'حضانة'),
        ('ladies', 'سيدات')
    ], string='نوع التسجيل', required=True)

    data_hash = fields.Char(
        string='Data Hash',
        required=True,
        help='Hash of validated data to ensure integrity'
    )

    validated_data = fields.Text(
        string='Validated Data',
        help='JSON string of validated form data'
    )

    expires_at = fields.Datetime(
        string='Expiry Time',
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(minutes=5)
    )

    is_used = fields.Boolean(
        string='Used',
        default=False
    )

    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now
    )

    ip_address = fields.Char(
        string='IP Address',
        help='IP address of the user who requested validation'
    )

    @api.model
    def _generate_token(self):
        """Generate secure random token"""
        import secrets
        return secrets.token_urlsafe(32)

    @api.model
    def clean_expired_tokens(self):
        """Cron job to clean expired tokens"""
        expired = self.search([
            ('expires_at', '<', fields.Datetime.now()),
            ('is_used', '=', False)
        ])
        expired.unlink()
        return True

    def validate_token(self, token_string):
        """Validate if token is valid and not expired"""
        self.ensure_one()
        if self.is_used:
            return False, "Token already used"
        if self.expires_at < fields.Datetime.now():
            return False, "Token expired"
        if self.token != token_string:
            return False, "Invalid token"
        return True, "Valid"
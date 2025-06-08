# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
from datetime import date
from dateutil.relativedelta import relativedelta


class QuranStudent(models.Model):
    _name = 'quran.student'
    _description = 'Quran Center Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'student_code'
    _order = 'student_code desc'

    # Student Code
    student_code = fields.Char(
        string='رقم الطالب',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    # Personal Information (copied from application)
    name_ar = fields.Char(
        string='الاسم باللغة العربية',
        required=True,
        tracking=True
    )

    name_en = fields.Char(
        string='Name in English',
        required=True,
        tracking=True
    )

    image = fields.Image(
        string='صورة الطالب',
        max_width=1024,
        max_height=1024
    )

    birth_date = fields.Date(
        string='تاريخ الميلاد',
        required=True,
        tracking=True
    )

    age = fields.Integer(
        string='العمر',
        compute='_compute_age',
        store=True
    )

    gender = fields.Selection([
        ('male', 'ذكر'),
        ('female', 'أنثى')
    ], string='الجنس', required=True, tracking=True)

    nationality = fields.Many2one(
        'res.country',
        string='الجنسية',
        required=True,
        tracking=True
    )

    id_number = fields.Char(
        string='رقم الهوية/الجواز',
        required=True,
        tracking=True,
        copy=False
    )

    # Educational Information
    education_level = fields.Selection([
        ('illiterate', 'أمّي'),
        ('primary', 'ابتدائي'),
        ('intermediate', 'إعدادي'),
        ('secondary', 'ثانوي'),
        ('university', 'جامعي'),
        ('diploma', 'دبلوم'),
        ('masters', 'ماجستير'),
        ('phd', 'دكتوراه')
    ], string='المرحلة الدراسية', required=True)

    # Memorization Information
    current_memorized_pages = fields.Integer(
        string='عدد صفحات الحفظ الحالي',
        required=True,
        default=0
    )

    memorization_level = fields.Selection([
        ('intermediate', 'حفظ'),
        ('advanced', 'خاتم للقرآن')
    ], string='مستوى حفظ الطالب', required=True)

    memorization_start_page = fields.Integer(
        string='بداية الحفظ (من صفحة)',
        required=True,
        default=1
    )

    memorization_end_page = fields.Integer(
        string='نهاية الحفظ (إلى صفحة)',
        required=True,
        default=1
    )

    total_memorization_pages = fields.Integer(
        string='عدد صفحات الحفظ',
        compute='_compute_total_pages',
        store=True
    )

    review_pages = fields.Integer(
        string='عدد صفحات المراجعة',
        required=True,
        default=0
    )

    # Student Specific Fields
    registration_date = fields.Date(
        string='تاريخ التسجيل',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    state = fields.Selection([
        ('active', 'نشط'),
        ('inactive', 'غير نشط'),
        ('graduated', 'متخرج'),
        ('suspended', 'موقوف')
    ], string='الحالة', default='active', tracking=True)

    # Relationship with applications
    application_ids = fields.One2many(
        'quran.enrollment.application',
        'student_id',
        string='طلبات الالتحاق'
    )

    application_count = fields.Integer(
        string='عدد الطلبات',
        compute='_compute_application_count'
    )

    # Contact Information
    phone = fields.Char(string='رقم الهاتف')
    email = fields.Char(string='البريد الإلكتروني')
    address = fields.Text(string='العنوان')

    # Guardian Information (for minors)
    guardian_name = fields.Char(string='اسم ولي الأمر')
    guardian_phone = fields.Char(string='هاتف ولي الأمر')
    guardian_relation = fields.Selection([
        ('father', 'الأب'),
        ('mother', 'الأم'),
        ('brother', 'الأخ'),
        ('sister', 'الأخت'),
        ('other', 'أخرى')
    ], string='صلة القرابة')

    # Notes
    notes = fields.Text(string='ملاحظات')
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'student_attachment_rel',
        'student_id',
        'attachment_id',
        string='المستندات',
        help='المستندات الخاصة بالطالب'
    )

    attachment_count = fields.Integer(
        string='عدد المستندات',
        compute='_compute_attachment_count'
    )
    # Relationship with study covenants
    covenant_ids = fields.Many2many(
        'quran.study.covenant',
        'quran_covenant_student_rel',
        'student_id',
        'covenant_id',
        string='المواثيق الدراسية'
    )

    covenant_count = fields.Integer(
        string='عدد المواثيق',
        compute='_compute_covenant_count'
    )

    # Relationship with classes
    class_ids = fields.Many2many(
        'quran.class',
        'quran_class_student_rel',
        'student_id',
        'class_id',
        string='الصفوف'
    )

    class_count = fields.Integer(
        string='عدد الصفوف',
        compute='_compute_class_count'
    )

    # Attendance records
    attendance_ids = fields.One2many(
        'quran.session.attendance',
        'student_id',
        string='سجلات الحضور'
    )

    completed_attendance_ids = fields.One2many(
        'quran.session.attendance',
        'student_id',
        string='الجلسات المنتهية',
        domain=[('session_id.state', '=', 'completed')]
    )

    # بعد completed_attendance_ids الموجود
    completed_ladies_attendance_ids = fields.One2many(
        'quran.session.attendance',
        'student_id',
        string='جلسات السيدات المنتهية',
        domain=[
            ('session_id.state', '=', 'completed'),
            ('program_type', '=', 'ladies')
        ]
    )

    # NEW FIELDS FOR SESSION NOTEBOOKS
    # جلسات النوادي
    club_session_ids = fields.One2many(
        'quran.session.attendance',
        'student_id',
        string='جلسات النوادي',
        domain=[('program_type', '=', 'clubs')],
        readonly=True
    )

    # جلسات السيدات
    ladies_session_ids = fields.One2many(
        'quran.session.attendance',
        'student_id',
        string='جلسات السيدات',
        domain=[('program_type', '=', 'ladies')],
        readonly=True
    )

    # حقول للتحكم في إظهار النوتبوك
    show_club_notebook = fields.Boolean(
        compute='_compute_show_notebooks',
        string='إظهار نوتبوك النوادي'
    )

    show_ladies_notebook = fields.Boolean(
        compute='_compute_show_notebooks',
        string='إظهار نوتبوك السيدات'
    )

    user_id = fields.Many2one(
        'res.users',
        string='مستخدم البورتال',
        readonly=True,
        copy=False
    )
    access_url = fields.Char(
        string='رابط البورتال',
        compute='_compute_access_url',
        readonly=True
    )
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)


    def can_enroll_in_program(self, program_type):
        """التحقق من إمكانية التسجيل في نوع البرنامج"""
        if program_type == 'clubs':
            return 6 <= self.age <= 18
        elif program_type == 'ladies':
            return self.gender == 'female' and self.age >= 18
        return False

    @api.depends('gender', 'age', 'club_session_ids', 'ladies_session_ids')
    def _compute_show_notebooks(self):
        """حساب إظهار النوتبوك حسب الجنس والعمر"""
        for student in self:
            if student.gender == 'male':
                # الذكور يشوفوا نوتبوك النوادي فقط
                student.show_club_notebook = True
                student.show_ladies_notebook = False
            else:  # female
                # الإناث: نوتبوك النوادي تظهر لأقل من 18 أو لو عندها جلسات
                student.show_club_notebook = student.age < 18 or bool(student.club_session_ids)
                # نوتبوك السيدات تظهر لـ 18+ أو لو عندها جلسات
                student.show_ladies_notebook = student.age >= 18 or bool(student.ladies_session_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('student_code', 'New') == 'New':
                vals['student_code'] = self.env['ir.sequence'].next_by_code('quran.student') or 'New'
        return super().create(vals_list)

    @api.depends('birth_date')
    def _compute_age(self):
        for record in self:
            if record.birth_date:
                today = date.today()
                age = relativedelta(today, record.birth_date).years
                record.age = age
            else:
                record.age = 0

    @api.depends('memorization_start_page', 'memorization_end_page')
    def _compute_total_pages(self):
        for record in self:
            if record.memorization_end_page >= record.memorization_start_page:
                record.total_memorization_pages = record.memorization_end_page - record.memorization_start_page + 1
            else:
                record.total_memorization_pages = 0

    @api.depends('application_ids')
    def _compute_application_count(self):
        for record in self:
            record.application_count = len(record.application_ids)

    @api.depends('covenant_ids')
    def _compute_covenant_count(self):
        for record in self:
            record.covenant_count = len(record.covenant_ids)

    @api.depends('class_ids')
    def _compute_class_count(self):
        for record in self:
            record.class_count = len(record.class_ids)

    @api.constrains('name_ar')
    def _check_arabic_name(self):
        for record in self:
            if record.name_ar:
                arabic_pattern = r'^[\u0600-\u06FF\s]+$'
                if not re.match(arabic_pattern, record.name_ar):
                    raise ValidationError(_('الاسم باللغة العربية يجب أن يحتوي على حروف عربية فقط'))

    @api.constrains('name_en')
    def _check_english_name(self):
        for record in self:
            if record.name_en:
                english_pattern = r'^[a-zA-Z\s]+$'
                if not re.match(english_pattern, record.name_en):
                    raise ValidationError(_('Name in English must contain English letters only'))

    @api.constrains('id_number')
    def _check_unique_id_number(self):
        for record in self:
            existing = self.search([
                ('id_number', '=', record.id_number),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_('رقم الهوية/الجواز مسجل مسبقاً لطالب آخر'))

    def action_activate(self):
        self.state = 'active'

    def action_deactivate(self):
        self.state = 'inactive'

    def action_graduate(self):
        self.state = 'graduated'

    def action_suspend(self):
        self.state = 'suspended'

    def action_view_applications(self):
        return {
            'name': _('طلبات الالتحاق'),
            'view_mode': 'list,form',
            'res_model': 'quran.enrollment.application',
            'type': 'ir.actions.act_window',
            'domain': [('student_id', '=', self.id)],
            'context': {'default_student_id': self.id}
        }

    def action_view_covenants(self):
        return {
            'name': _('المواثيق الدراسية'),
            'view_mode': 'list,form',
            'res_model': 'quran.study.covenant',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.covenant_ids.ids)],
            'context': {'create': False}
        }

    def action_view_classes(self):
        return {
            'name': _('الصفوف'),
            'view_mode': 'list,form',
            'res_model': 'quran.class',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.class_ids.ids)],
            'context': {'create': False}
        }

    def _compute_access_url(self):
        """حساب رابط البورتال للطالب"""
        super()._compute_access_url()
        for student in self:
            student.access_url = f'/my/student/{student.id}'

    def action_create_portal_user(self):
        """إنشاء مستخدم بورتال للطالب"""
        self.ensure_one()

        if self.user_id:
            raise ValidationError(_('يوجد حساب بورتال لهذا الطالب بالفعل'))

        if not self.email:
            raise ValidationError(_('يجب إدخال البريد الإلكتروني لإنشاء حساب البورتال'))

        # التحقق من عدم وجود مستخدم بنفس البريد
        existing_user = self.env['res.users'].sudo().search([
            ('login', '=', self.email)
        ], limit=1)

        if existing_user:
            raise ValidationError(_('يوجد مستخدم بنفس البريد الإلكتروني'))

        # إنشاء المستخدم
        portal_group = self.env.ref('base.group_portal')
        user_vals = {
            'name': self.name_ar,
            'login': self.email,
            'email': self.email,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
            'groups_id': [(6, 0, [portal_group.id])],
            'password': self.id_number,  # كلمة المرور = رقم الهوية
        }

        user = self.env['res.users'].sudo().create(user_vals)

        # ربط المستخدم بالطالب
        self.user_id = user

        # تحديث partner_id إذا لم يكن موجود
        if not self.partner_id:
            # إنشاء partner جديد
            partner_vals = {
                'name': self.name_ar,
                'email': self.email,
                'phone': self.phone,
                'is_company': False,
                'customer_rank': 0,
                'supplier_rank': 0,
            }
            partner = self.env['res.partner'].sudo().create(partner_vals)
            self.partner_id = partner.id

            # تحديث المستخدم بالـ partner
            user.partner_id = partner.id
        else:
            # تحديث بيانات الـ partner الموجود
            self.partner_id.sudo().write({
                'email': self.email,
                'phone': self.phone,
            })
            user.partner_id = self.partner_id.id

        # إرسال بريد إلكتروني بالبيانات
        self._send_portal_access_email()

        # رسالة نجاح
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('نجح'),
                'message': _('تم إنشاء حساب البورتال بنجاح وإرسال البيانات للطالب'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_attachments(self):
        """عرض المستندات المرفقة"""
        self.ensure_one()
        return {
            'name': _('مستندات الطالب'),
            'view_mode': 'list,form',
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            }
        }

    def _send_portal_access_email(self):
        """إرسال بريد إلكتروني ببيانات الدخول"""
        self.ensure_one()

        template = self.env.ref('quran_center.email_template_portal_access', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        else:
            # إرسال بريد بسيط إذا لم يوجد قالب
            mail_content = f"""
            <p>عزيزي الطالب {self.name_ar}،</p>
            <p>تم إنشاء حساب البورتال الخاص بك بنجاح.</p>
            <p><strong>بيانات الدخول:</strong></p>
            <ul>
                <li>البريد الإلكتروني: {self.email}</li>
                <li>كلمة المرور: {self.id_number}</li>
                <li>رقم الطالب: {self.student_code}</li>
            </ul>
            <p>يمكنك الدخول من خلال الرابط: <a href="{self.get_base_url()}/web/login">دخول البورتال</a></p>
            <p>يُنصح بتغيير كلمة المرور بعد أول دخول.</p>
            """

            mail_values = {
                'subject': 'بيانات الدخول لبورتال مركز تحفيظ القرآن',
                'body_html': mail_content,
                'email_to': self.email,
                'email_from': self.env.company.email or 'noreply@quran-center.com',
            }

            self.env['mail.mail'].sudo().create(mail_values).send()

    def action_open_portal(self):
        """فتح البورتال في تبويب جديد"""
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_('لا يوجد حساب بورتال لهذا الطالب'))

        # تسجيل دخول كـ superuser ثم التبديل للمستخدم
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/session/logout?redirect=/web/login?login={self.user_id.login}',
            'target': 'new',
        }

    def action_view_portal(self):
        """عرض البورتال الخاص بالطالب"""
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_('لا يوجد حساب بورتال لهذا الطالب'))

        base_url = self.get_base_url()
        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/my/dashboard',
            'target': 'new',
        }

    def action_reset_portal_password(self):
        """إعادة تعيين كلمة مرور البورتال"""
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_('لا يوجد حساب بورتال لهذا الطالب'))

        # إعادة تعيين كلمة المرور لرقم الهوية
        self.user_id.sudo().write({
            'password': self.id_number
        })

        # إرسال بريد إلكتروني بكلمة المرور الجديدة
        self._send_password_reset_email()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('نجح'),
                'message': _('تم إعادة تعيين كلمة المرور وإرسالها للطالب'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_deactivate_portal(self):
        """إلغاء تفعيل حساب البورتال"""
        self.ensure_one()
        if not self.user_id:
            raise ValidationError(_('لا يوجد حساب بورتال لهذا الطالب'))

        self.user_id.sudo().write({
            'active': False
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('نجح'),
                'message': _('تم إلغاء تفعيل حساب البورتال'),
                'type': 'warning',
                'sticky': False,
            }
        }

    def _send_password_reset_email(self):
        """إرسال بريد إلكتروني بكلمة المرور الجديدة"""
        self.ensure_one()

        mail_content = f"""
        <div style="direction: rtl; text-align: right; font-family: Arial, sans-serif;">
            <p>عزيزي الطالب {self.name_ar}،</p>
            <p>تم إعادة تعيين كلمة مرور حساب البورتال الخاص بك.</p>
            <p><strong>بيانات الدخول الجديدة:</strong></p>
            <ul>
                <li>البريد الإلكتروني: {self.email}</li>
                <li>كلمة المرور الجديدة: {self.id_number}</li>
            </ul>
            <p>يُنصح بتغيير كلمة المرور بعد الدخول.</p>
            <p>يمكنك الدخول من خلال الرابط: <a href="{self.get_base_url()}/web/login">دخول البورتال</a></p>
        </div>
        """

        mail_values = {
            'subject': 'إعادة تعيين كلمة مرور البورتال - مركز تحفيظ القرآن',
            'body_html': mail_content,
            'email_to': self.email,
            'email_from': self.env.company.email or 'noreply@quran-center.com',
        }

        self.env['mail.mail'].sudo().create(mail_values).send()

    @api.onchange('email')
    def _onchange_email(self):
        """تحذير عند تغيير البريد الإلكتروني إذا كان هناك حساب بورتال"""
        if self.user_id and self._origin.email != self.email:
            return {
                'warning': {
                    'title': _('تحذير'),
                    'message': _(
                        'تغيير البريد الإلكتروني لن يؤثر على حساب البورتال الموجود. يجب تحديث البريد في حساب المستخدم يدوياً.')
                }
            }
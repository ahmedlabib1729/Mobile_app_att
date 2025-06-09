# models/enrollment_application.py
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
from datetime import date
from dateutil.relativedelta import relativedelta


class EnrollmentApplication(models.Model):
    _name = 'quran.enrollment.application'
    _description = 'Quran Center Enrollment Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # Application Number
    name = fields.Char(
        string='رقم الطلب',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    # Personal Information
    name_ar = fields.Char(
        string='الاسم باللغة العربية',
        required=True,
        tracking=True,
        help='يقبل الحروف العربية فقط'
    )

    name_en = fields.Char(
        string='Name in English',
        required=True,
        tracking=True,
        help='English letters only'
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
        tracking=True,
        help='اختر الجنسية من قائمة الدول'
    )

    id_number = fields.Char(
        string='رقم الهوية/الجواز',
        required=True,
        tracking=True,
        copy=False
    )

    # Image field
    image = fields.Image(
        string='صورة الطالب',
        max_width=1024,
        max_height=1024,
        help='صورة شخصية للطالب'
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

    enrollment_date = fields.Date(
        string='تاريخ الالتحاق',
        required=True,
        default=fields.Date.context_today
    )

    # Memorization Level
    current_memorized_pages = fields.Integer(
        string='عدد صفحات الحفظ عند الالتحاق',
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

    # Status
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدم'),
        ('approved', 'مقبول'),
        ('rejected', 'مرفوض')
    ], string='الحالة', default='draft', tracking=True)

    # Relationship with Student
    student_id = fields.Many2one(
        'quran.student',
        string='الطالب',
        readonly=True,
        copy=False
    )

    has_student = fields.Boolean(
        string='تم إنشاء طالب',
        compute='_compute_has_student',
        store=True
    )

    email = fields.Char(
        string='البريد الإلكتروني',
        required=True,
        tracking=True,
        help='سيستخدم لإنشاء حساب البورتال'
    )

    phone = fields.Char(
        string='رقم الهاتف',
        tracking=True
    )

    notes = fields.Text(string='ملاحظات')

    # المستندات المرفقة
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'enrollment_attachment_rel',
        'enrollment_id',
        'attachment_id',
        string='المستندات المرفقة',
        help='يمكنك رفع صور الشهادات، شهادة الميلاد، الهوية، إلخ'
    )

    attachment_count = fields.Integer(
        string='عدد المرفقات',
        compute='_compute_attachment_count'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('quran.enrollment.application') or 'New'
        return super().create(vals_list)

    @api.depends('student_id')
    def _compute_has_student(self):
        for record in self:
            record.has_student = bool(record.student_id)

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

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    @api.constrains('name_ar')
    def _check_arabic_name(self):
        for record in self:
            if record.name_ar:
                # Arabic letters pattern
                arabic_pattern = r'^[\u0600-\u06FF\s]+$'
                if not re.match(arabic_pattern, record.name_ar):
                    raise ValidationError(_('الاسم باللغة العربية يجب أن يحتوي على حروف عربية فقط'))

    @api.constrains('name_en')
    def _check_english_name(self):
        for record in self:
            if record.name_en:
                # English letters pattern
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
                raise ValidationError(_('رقم الهوية/الجواز مسجل مسبقاً'))

    @api.constrains('birth_date')
    def _check_age_limits(self):
        for record in self:
            if record.birth_date:
                age = record.age
                if age < 5:
                    raise ValidationError(_('الحد الأدنى للعمر هو 5 سنوات'))
                elif age > 100:
                    raise ValidationError(_('يرجى التحقق من تاريخ الميلاد'))

    @api.constrains('memorization_start_page', 'memorization_end_page')
    def _check_page_range(self):
        for record in self:
            if record.memorization_start_page < 1 or record.memorization_start_page > 604:
                raise ValidationError(_('صفحة البداية يجب أن تكون بين 1 و 604'))
            if record.memorization_end_page < 1 or record.memorization_end_page > 604:
                raise ValidationError(_('صفحة النهاية يجب أن تكون بين 1 و 604'))
            if record.memorization_end_page < record.memorization_start_page:
                raise ValidationError(_('صفحة النهاية يجب أن تكون أكبر من أو تساوي صفحة البداية'))

    @api.constrains('current_memorized_pages', 'review_pages')
    def _check_pages_limits(self):
        for record in self:
            if record.current_memorized_pages < 0 or record.current_memorized_pages > 604:
                raise ValidationError(_('عدد صفحات الحفظ يجب أن يكون بين 0 و 604'))
            if record.review_pages < 0 or record.review_pages > 604:
                raise ValidationError(_('عدد صفحات المراجعة يجب أن يكون بين 0 و 604'))

    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'

    def action_draft(self):
        self.state = 'draft'

    def action_create_student(self):
        """Create a student from approved application"""
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_('يمكن إنشاء طالب فقط من طلب مقبول'))

        if self.student_id:
            raise ValidationError(_('تم إنشاء طالب لهذا الطلب مسبقاً'))

        # Prepare student data
        student_vals = {
            'name_ar': self.name_ar,
            'name_en': self.name_en,
            'birth_date': self.birth_date,
            'gender': self.gender,
            'nationality': self.nationality.id,
            'id_number': self.id_number,
            'education_level': self.education_level,
            'current_memorized_pages': self.current_memorized_pages,
            'memorization_level': self.memorization_level,
            'memorization_start_page': self.memorization_start_page,
            'memorization_end_page': self.memorization_end_page,
            'review_pages': self.review_pages,
            'image': self.image,
            'registration_date': fields.Date.today(),
            'email': self.email,
            'phone': self.phone,
        }

        # Create student
        student = self.env['quran.student'].create(student_vals)

        # Link student to application
        self.student_id = student

        # نسخ المرفقات إلى الطالب
        if self.attachment_ids:
            # نسخ المرفقات للطالب الجديد
            new_attachments = []
            for attachment in self.attachment_ids:
                new_attachment = attachment.copy({
                    'res_model': 'quran.student',
                    'res_id': student.id,
                })
                new_attachments.append(new_attachment.id)

            # ربط المرفقات الجديدة بالطالب
            if new_attachments:
                student.attachment_ids = [(6, 0, new_attachments)]

        # Show success message and open student form
        return {
            'type': 'ir.actions.act_window',
            'name': _('الطالب الجديد'),
            'res_model': 'quran.student',
            'res_id': student.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_attachments(self):
        """عرض المستندات المرفقة"""
        self.ensure_one()
        return {
            'name': _('المستندات المرفقة'),
            'view_mode': 'list,form',
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            }
        }
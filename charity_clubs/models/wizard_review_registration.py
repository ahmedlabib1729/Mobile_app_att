# إنشاء ملف جديد: wizard_review_registration.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClubRegistrationReviewWizard(models.TransientModel):
    _name = 'charity.club.registration.review.wizard'
    _description = 'معالج مراجعة التسجيلات'

    registration_id = fields.Many2one(
        'charity.club.registrations',
        string='التسجيل',
        required=True,
        readonly=True
    )

    # معلومات التسجيل الحالي
    current_name = fields.Char(
        string='الاسم المدخل',
        related='registration_id.full_name',
        readonly=True
    )

    current_id_number = fields.Char(
        string='رقم الهوية المدخل',
        related='registration_id.id_number',
        readonly=True
    )

    # معلومات الطالب الموجود
    existing_student_id = fields.Many2one(
        'charity.student.profile',
        string='الطالب الموجود',
        compute='_compute_existing_student',
        readonly=True
    )

    existing_student_name = fields.Char(
        string='اسم الطالب الموجود',
        related='existing_student_id.full_name',
        readonly=True
    )

    # قرار الإدارة
    action = fields.Selection([
        ('create_new', 'إنشاء ملف طالب جديد'),
        ('link_existing', 'ربط بالملف الموجود'),
        ('update_id', 'تعديل رقم الهوية'),
        ('reject', 'رفض التسجيل')
    ], string='الإجراء المطلوب',
        required=True,
        default='create_new'
    )

    # حقول للتعديل
    new_id_number = fields.Char(
        string='رقم الهوية الجديد',
        help='أدخل رقم الهوية الصحيح في حالة اختيار تعديل رقم الهوية'
    )

    notes = fields.Text(
        string='ملاحظات',
        help='أي ملاحظات إضافية حول القرار'
    )

    @api.depends('registration_id')
    def _compute_existing_student(self):
        for wizard in self:
            if wizard.registration_id and wizard.registration_id.id_number:
                existing = self.env['charity.student.profile'].search([
                    ('id_number', '=', wizard.registration_id.id_number)
                ], limit=1)
                wizard.existing_student_id = existing
            else:
                wizard.existing_student_id = False

    @api.onchange('action')
    def _onchange_action(self):
        """إظهار/إخفاء الحقول حسب الإجراء المختار"""
        if self.action != 'update_id':
            self.new_id_number = False

    def action_apply(self):
        """تطبيق القرار"""
        self.ensure_one()

        registration = self.registration_id

        if self.action == 'create_new':
            # إنشاء ملف طالب جديد
            registration._create_student_and_family()
            registration.has_id_conflict = False
            registration.action_confirm_after_review()

            message = f"تم إنشاء ملف طالب جديد رغم تشابه رقم الهوية"

        elif self.action == 'link_existing':
            # ربط بالملف الموجود
            if self.existing_student_id:
                registration.registration_type = 'existing'
                registration.student_profile_id = self.existing_student_id
                registration.has_id_conflict = False
                registration.action_confirm_after_review()

                message = f"تم ربط التسجيل بملف الطالب الموجود: {self.existing_student_id.full_name}"
            else:
                raise ValidationError('لا يوجد طالب موجود للربط به!')

        elif self.action == 'update_id':
            # تعديل رقم الهوية
            if not self.new_id_number:
                raise ValidationError('يجب إدخال رقم الهوية الجديد!')

            # التحقق من عدم وجود طالب آخر بالرقم الجديد
            existing_with_new_id = self.env['charity.student.profile'].search([
                ('id_number', '=', self.new_id_number)
            ], limit=1)

            if existing_with_new_id:
                raise ValidationError(
                    f'رقم الهوية الجديد {self.new_id_number} مسجل بالفعل للطالب {existing_with_new_id.full_name}!'
                )

            registration.id_number = self.new_id_number
            registration._create_student_and_family()
            registration.has_id_conflict = False
            registration.action_confirm_after_review()

            message = f"تم تعديل رقم الهوية إلى {self.new_id_number} وإنشاء ملف الطالب"

        else:  # reject
            registration.action_reject_after_review()
            message = "تم رفض التسجيل"

        # إضافة الملاحظات
        if self.notes:
            message += f"\n\nملاحظات الإدارة: {self.notes}"

        registration.message_post(
            body=message,
            subject="قرار الإدارة"
        )

        return {'type': 'ir.actions.act_window_close'}
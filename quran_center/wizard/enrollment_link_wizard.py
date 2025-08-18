# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class EnrollmentLinkWizard(models.TransientModel):
    _name = 'quran.enrollment.link.wizard'
    _description = 'Link Enrollment to Existing Student'

    enrollment_id = fields.Many2one(
        'quran.enrollment.application',
        string='طلب الالتحاق',
        required=True,
        readonly=True
    )

    student_id = fields.Many2one(
        'quran.student',
        string='الطالب الموجود',
        required=True,
        readonly=True
    )

    message = fields.Text(
        string='رسالة',
        readonly=True
    )

    # معلومات للمقارنة
    comparison_info = fields.Html(
        string='مقارنة البيانات',
        compute='_compute_comparison_info'
    )

    action = fields.Selection([
        ('link', 'ربط الطلب بالطالب الموجود'),
        ('create_new', 'إنشاء طالب جديد على أي حال'),
        ('cancel', 'إلغاء العملية')
    ], string='الإجراء', default='link', required=True)

    update_student_data = fields.Boolean(
        string='تحديث بيانات الطالب من الطلب الجديد',
        default=False,
        help='تحديث بيانات الطالب الموجود بالبيانات الجديدة من الطلب'
    )

    @api.depends('enrollment_id', 'student_id')
    def _compute_comparison_info(self):
        for wizard in self:
            if wizard.enrollment_id and wizard.student_id:
                enrollment = wizard.enrollment_id
                student = wizard.student_id

                # إنشاء جدول HTML للمقارنة
                html = """
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>البيان</th>
                            <th>في الطلب الجديد</th>
                            <th>في بيانات الطالب</th>
                            <th>مطابق؟</th>
                        </tr>
                    </thead>
                    <tbody>
                """

                # قائمة الحقول للمقارنة
                fields_to_compare = [
                    ('name_ar', 'الاسم بالعربية'),
                    ('name_en', 'الاسم بالإنجليزية'),
                    ('birth_date', 'تاريخ الميلاد'),
                    ('gender', 'الجنس'),
                    ('email', 'البريد الإلكتروني'),
                    ('phone', 'رقم الهاتف'),
                ]

                for field, label in fields_to_compare:
                    enrollment_value = getattr(enrollment, field, '')
                    student_value = getattr(student, field, '')

                    # معالجة قيم Selection fields
                    if field == 'gender':
                        gender_dict = dict(enrollment._fields['gender'].selection)
                        enrollment_value = gender_dict.get(enrollment_value, enrollment_value)
                        student_value = gender_dict.get(student_value, student_value)

                    # التحقق من التطابق
                    is_match = enrollment_value == student_value
                    match_icon = '✅' if is_match else '❌'

                    # تنسيق القيم
                    enrollment_display = enrollment_value or '-'
                    student_display = student_value or '-'

                    # إضافة صف للجدول
                    row_class = '' if is_match else 'table-warning'
                    html += f"""
                        <tr class="{row_class}">
                            <td><strong>{label}</strong></td>
                            <td>{enrollment_display}</td>
                            <td>{student_display}</td>
                            <td class="text-center">{match_icon}</td>
                        </tr>
                    """

                html += """
                    </tbody>
                </table>
                <div class="alert alert-info mt-3">
                    <i class="fa fa-info-circle"></i>
                    البيانات المختلفة ستبقى كما هي في سجل الطالب ما لم تختر "تحديث بيانات الطالب"
                </div>
                """

                wizard.comparison_info = html
            else:
                wizard.comparison_info = False

    def action_confirm(self):
        """تنفيذ الإجراء المختار"""
        self.ensure_one()

        if self.action == 'link':
            # ربط الطلب بالطالب الموجود
            self.enrollment_id.student_id = self.student_id

            # تحديث بيانات الطالب إذا تم اختيار ذلك
            if self.update_student_data:
                update_vals = {
                    'name_ar': self.enrollment_id.name_ar,
                    'name_en': self.enrollment_id.name_en,
                    'birth_date': self.enrollment_id.birth_date,
                    'gender': self.enrollment_id.gender,
                    'email': self.enrollment_id.email,
                    'phone': self.enrollment_id.phone or self.student_id.phone,
                    'education_level': self.enrollment_id.education_level,
                    'current_memorized_pages': self.enrollment_id.current_memorized_pages,
                    'memorization_level': self.enrollment_id.memorization_level,
                    'memorization_start_page': self.enrollment_id.memorization_start_page,
                    'memorization_end_page': self.enrollment_id.memorization_end_page,
                    'review_pages': self.enrollment_id.review_pages,
                }

                # تحديث الصورة إذا كانت موجودة في الطلب
                if self.enrollment_id.image:
                    update_vals['image'] = self.enrollment_id.image

                # نسخ الملفات الثنائية
                if self.enrollment_id.emirates_id_file:
                    update_vals['emirates_id_file'] = self.enrollment_id.emirates_id_file
                    update_vals['emirates_id_filename'] = self.enrollment_id.emirates_id_filename

                if self.enrollment_id.residence_file:
                    update_vals['residence_file'] = self.enrollment_id.residence_file
                    update_vals['residence_filename'] = self.enrollment_id.residence_filename

                if self.enrollment_id.passport_file:
                    update_vals['passport_file'] = self.enrollment_id.passport_file
                    update_vals['passport_filename'] = self.enrollment_id.passport_filename

                if self.enrollment_id.other_document_file:
                    update_vals['other_document_file'] = self.enrollment_id.other_document_file
                    update_vals['other_document_filename'] = self.enrollment_id.other_document_filename

                self.student_id.write(update_vals)

                # نسخ المستندات المرفقة
                self._copy_attachments()

            # عرض رسالة نجاح وفتح سجل الطالب
            return {
                'type': 'ir.actions.act_window',
                'name': _('الطالب'),
                'res_model': 'quran.student',
                'res_id': self.student_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

        elif self.action == 'create_new':
            # إنشاء طالب جديد رغم وجود طالب بنفس رقم الهوية
            # هذا يتطلب تعديل رقم الهوية أو إضافة حقل إضافي للتمييز
            raise UserError(_(
                'لا يمكن إنشاء طالب جديد بنفس رقم الهوية.\n'
                'يرجى تعديل رقم الهوية في الطلب أولاً أو ربط الطلب بالطالب الموجود.'
            ))

        else:  # cancel
            return {'type': 'ir.actions.act_window_close'}

    def _copy_attachments(self):
        """نسخ المرفقات من الطلب إلى الطالب"""
        enrollment = self.enrollment_id
        student = self.student_id

        # نسخ المرفقات attachment_ids
        if enrollment.attachment_ids:
            for attachment in enrollment.attachment_ids:
                # التحقق من عدم وجود نفس المرفق
                existing = self.env['ir.attachment'].search([
                    ('res_model', '=', 'quran.student'),
                    ('res_id', '=', student.id),
                    ('name', '=', attachment.name),
                ], limit=1)

                if not existing:
                    # إنشاء نسخة جديدة من المرفق
                    new_attachment_vals = {
                        'name': attachment.name,
                        'datas': attachment.datas,
                        'type': attachment.type,
                        'res_model': 'quran.student',
                        'res_id': student.id,
                        'mimetype': attachment.mimetype,
                    }
                    self.env['ir.attachment'].create(new_attachment_vals)
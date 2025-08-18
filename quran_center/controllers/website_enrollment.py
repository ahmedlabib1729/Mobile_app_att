# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
import re
from datetime import date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class WebsiteEnrollment(http.Controller):

    @http.route('/enrollment/application', type='http', auth='public', website=True, sitemap=True)
    def enrollment_form(self, **kwargs):
        """عرض نموذج التسجيل"""
        from datetime import date
        countries = request.env['res.country'].sudo().search([])
        values = {
            'countries': countries,
            'error': {},
            'success': False,
            'date': date,
        }
        return request.render('quran_center.enrollment_application_form', values)

    @http.route('/enrollment/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def submit_enrollment(self, **post):
        """معالجة بيانات التسجيل"""
        error = {}
        error_message = []

        # التحقق من البيانات المطلوبة
        required_fields = [
            'name_ar', 'name_en', 'birth_date', 'gender', 'nationality',
            'id_number', 'education_level', 'enrollment_date',
            'current_memorized_pages', 'memorization_level',
            'memorization_start_page', 'memorization_end_page', 'review_pages',
            'email'  # إضافة البريد الإلكتروني كحقل مطلوب
        ]

        for field in required_fields:
            if not post.get(field):
                error[field] = 'missing'
                error_message.append(f'الحقل {field} مطلوب')

        # التحقق من رقم الهوية الإماراتية
        id_number = post.get('id_number', '')
        if id_number:
            # إزالة الشرطات للتحقق
            id_digits = re.sub(r'[^\d]', '', id_number)

            # التحقق من أن الرقم يبدأ بـ 784
            if not id_digits.startswith('784'):
                error['id_number'] = 'invalid'
                error_message.append('رقم الهوية الإماراتية يجب أن يبدأ بـ 784' )
                error_message.append('رقم الهوية الإماراتية يجب أن يكون 15 رقم')
                error_message.append(' (784-XXXX-XXXXXXX-X)رقم الهوية الإماراتية يجب أن يكون بهذا الشكل ')

            # التحقق من طول الرقم
            elif len(id_digits) != 15:
                error['id_number'] = 'invalid'
                error_message.append('رقم الهوية الإماراتية يجب أن يكون 15 رقم')

            # التحقق من الصيغة الصحيحة
            else:
                pattern = r'^784-\d{4}-\d{7}-\d$'
        image = False
        try:
            if 'image' in request.httprequest.files:
                image_file = request.httprequest.files['image']
                if image_file and image_file.filename:
                    image = base64.b64encode(image_file.read())
        except Exception as e:
            _logger.warning(f"Error processing image: {str(e)}")
            # لا نضيف خطأ لأن الصورة اختيارية

        # معالجة الملفات الجديدة
        emirates_id_file = False
        emirates_id_filename = False
        residence_file = False
        residence_filename = False
        passport_file = False
        passport_filename = False
        other_document_file = False
        other_document_filename = False

        # معالجة الهوية الإماراتية
        try:
            if 'emirates_id_file' in request.httprequest.files:
                file = request.httprequest.files['emirates_id_file']
                if file and file.filename:
                    emirates_id_file = base64.b64encode(file.read())
                    emirates_id_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing emirates_id_file: {str(e)}")

        # معالجة الإقامة
        try:
            if 'residence_file' in request.httprequest.files:
                file = request.httprequest.files['residence_file']
                if file and file.filename:
                    residence_file = base64.b64encode(file.read())
                    residence_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing residence_file: {str(e)}")

        # معالجة جواز السفر
        try:
            if 'passport_file' in request.httprequest.files:
                file = request.httprequest.files['passport_file']
                if file and file.filename:
                    passport_file = base64.b64encode(file.read())
                    passport_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing passport_file: {str(e)}")

        # معالجة المستندات الأخرى
        try:
            if 'other_document_file' in request.httprequest.files:
                file = request.httprequest.files['other_document_file']
                if file and file.filename:
                    other_document_file = base64.b64encode(file.read())
                    other_document_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing other_document_file: {str(e)}")

        # التحقق من رفع المستندات المطلوبة (الثلاثة الأولى فقط إجبارية)
        if not emirates_id_file:
            error['emirates_id_file'] = 'missing'
            error_message.append('يجب رفع الهوية الإماراتية')

        if not residence_file:
            error['residence_file'] = 'missing'
            error_message.append('يجب رفع الإقامة')

        if not passport_file:
            error['passport_file'] = 'missing'
            error_message.append('يجب رفع جواز السفر')

        # other_document_file اختياري - لا نتحقق منه

        # معالجة المستندات المرفقة (الحقل الموجود)
        attachments_to_create = []
        try:
            # الحصول على جميع الملفات المرفوعة
            files = request.httprequest.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    # قراءة محتوى الملف
                    file_content = base64.b64encode(file.read())

                    # تجهيز بيانات المرفق
                    attachment_vals = {
                        'name': file.filename,
                        'datas': file_content,
                        'type': 'binary',
                        'res_model': 'quran.enrollment.application',
                    }
                    attachments_to_create.append(attachment_vals)

        except Exception as e:
            _logger.warning(f"Error processing attachments: {str(e)}")

        # إذا كان هناك أخطاء، أعد عرض النموذج مع الأخطاء
        if error:
            from datetime import date
            countries = request.env['res.country'].sudo().search([])
            values = {
                'countries': countries,
                'error': error,
                'error_message': error_message,
                'success': False,
                'date': date,
            }
            # الاحتفاظ بالبيانات المدخلة
            values.update(post)
            return request.render('quran_center.enrollment_application_form', values)

        try:
            # إنشاء طلب الالتحاق
            enrollment_vals = {
                'name_ar': post.get('name_ar'),
                'name_en': post.get('name_en'),
                'birth_date': post.get('birth_date'),
                'gender': post.get('gender'),
                'nationality': int(post.get('nationality')),
                'id_number': post.get('id_number'),
                'education_level': post.get('education_level'),
                'enrollment_date': post.get('enrollment_date'),
                'current_memorized_pages': int(post.get('current_memorized_pages', 1)),
                'memorization_level': post.get('memorization_level'),
                'memorization_start_page': int(post.get('memorization_start_page', 1)),
                'memorization_end_page': int(post.get('memorization_end_page', 1)),
                'review_pages': int(post.get('review_pages', 0)),
                'state': 'submitted',
                'email': post.get('email'),
                'phone': post.get('phone', ''),
            }

            if image:
                enrollment_vals['image'] = image

            # إضافة الملفات الجديدة
            if emirates_id_file:
                enrollment_vals['emirates_id_file'] = emirates_id_file
                enrollment_vals['emirates_id_filename'] = emirates_id_filename

            if residence_file:
                enrollment_vals['residence_file'] = residence_file
                enrollment_vals['residence_filename'] = residence_filename

            if passport_file:
                enrollment_vals['passport_file'] = passport_file
                enrollment_vals['passport_filename'] = passport_filename

            if other_document_file:
                enrollment_vals['other_document_file'] = other_document_file
                enrollment_vals['other_document_filename'] = other_document_filename

            enrollment = request.env['quran.enrollment.application'].sudo().create(enrollment_vals)

            # إنشاء المرفقات وربطها بالطلب
            if attachments_to_create:
                attachment_ids = []
                for att_vals in attachments_to_create:
                    att_vals['res_id'] = enrollment.id
                    attachment = request.env['ir.attachment'].sudo().create(att_vals)
                    attachment_ids.append(attachment.id)

                # ربط المرفقات بالطلب
                if attachment_ids:
                    enrollment.sudo().write({
                        'attachment_ids': [(6, 0, attachment_ids)]
                    })

            # عرض صفحة النجاح
            return request.render('quran_center.enrollment_success', {
                'enrollment': enrollment,
                'success': True
            })

        except Exception as e:
            _logger.error(f"Error creating enrollment: {str(e)}")
            # في حالة حدوث خطأ
            from datetime import date
            countries = request.env['res.country'].sudo().search([])
            values = {
                'countries': countries,
                'error': {'general': str(e)},
                'error_message': ['حدث خطأ أثناء إرسال الطلب. يرجى المحاولة مرة أخرى.'],
                'success': False,
                'date': date,
            }
            values.update(post)
            return request.render('quran_center.enrollment_application_form', values)

    @http.route('/enrollment/check-status/<string:application_number>', type='http', auth='public', website=True)
    def check_application_status(self, application_number, **kwargs):
        """التحقق من حالة الطلب"""
        application = request.env['quran.enrollment.application'].sudo().search([
            ('name', '=', application_number)
        ], limit=1)

        return request.render('quran_center.enrollment_status', {
            'application': application
        })
        if not re.match(pattern, id_number):
            error['id_number'] = 'invalid'
            error_message.append('صيغة رقم الهوية غير صحيحة. يجب أن تكون: 784-XXXX-XXXXXXX-X')

        else:
            error['id_number'] = 'missing'
            error_message.append('رقم الهوية الإماراتية مطلوب')


        # معالجة الصورة إن وجدت
        image = False
        try:
            if 'image' in request.httprequest.files:
                image_file = request.httprequest.files['image']
                if image_file and image_file.filename:
                    image = base64.b64encode(image_file.read())
        except Exception as e:
            _logger.warning(f"Error processing image: {str(e)}")
            # لا نضيف خطأ لأن الصورة اختيارية

        # معالجة الملفات الجديدة
        emirates_id_file = False
        emirates_id_filename = False
        residence_file = False
        residence_filename = False
        passport_file = False
        passport_filename = False
        other_document_file = False
        other_document_filename = False

        # معالجة الهوية الإماراتية
        try:
            if 'emirates_id_file' in request.httprequest.files:
                file = request.httprequest.files['emirates_id_file']
                if file and file.filename:
                    emirates_id_file = base64.b64encode(file.read())
                    emirates_id_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing emirates_id_file: {str(e)}")

        # معالجة الإقامة
        try:
            if 'residence_file' in request.httprequest.files:
                file = request.httprequest.files['residence_file']
                if file and file.filename:
                    residence_file = base64.b64encode(file.read())
                    residence_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing residence_file: {str(e)}")

        # معالجة جواز السفر
        try:
            if 'passport_file' in request.httprequest.files:
                file = request.httprequest.files['passport_file']
                if file and file.filename:
                    passport_file = base64.b64encode(file.read())
                    passport_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing passport_file: {str(e)}")

        # معالجة المستندات الأخرى
        try:
            if 'other_document_file' in request.httprequest.files:
                file = request.httprequest.files['other_document_file']
                if file and file.filename:
                    other_document_file = base64.b64encode(file.read())
                    other_document_filename = file.filename
        except Exception as e:
            _logger.warning(f"Error processing other_document_file: {str(e)}")

        # التحقق من رفع المستندات المطلوبة (الثلاثة الأولى فقط إجبارية)
        if not emirates_id_file:
            error['emirates_id_file'] = 'missing'
            error_message.append('يجب رفع الهوية الإماراتية')

        if not residence_file:
            error['residence_file'] = 'missing'
            error_message.append('يجب رفع الإقامة')

        if not passport_file:
            error['passport_file'] = 'missing'
            error_message.append('يجب رفع جواز السفر')

        # other_document_file اختياري - لا نتحقق منه

        # معالجة المستندات المرفقة (الحقل الموجود)
        attachments_to_create = []
        try:
            # الحصول على جميع الملفات المرفوعة
            files = request.httprequest.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    # قراءة محتوى الملف
                    file_content = base64.b64encode(file.read())

                    # تجهيز بيانات المرفق
                    attachment_vals = {
                        'name': file.filename,
                        'datas': file_content,
                        'type': 'binary',
                        'res_model': 'quran.enrollment.application',
                    }
                    attachments_to_create.append(attachment_vals)

        except Exception as e:
            _logger.warning(f"Error processing attachments: {str(e)}")

        # إذا كان هناك أخطاء، أعد عرض النموذج مع الأخطاء
        if error:
            from datetime import date

            countries = request.env['res.country'].sudo().search([])
            values = {
                'countries': countries,
                'error': error,
                'error_message': error_message,
                'success': False,
                'date': date,
            }
            # الاحتفاظ بالبيانات المدخلة
            values.update(post)
            return request.render('quran_center.enrollment_application_form', values)

        try:
            # إنشاء طلب الالتحاق
            enrollment_vals = {
                'name_ar': post.get('name_ar'),
                'name_en': post.get('name_en'),
                'birth_date': post.get('birth_date'),
                'gender': post.get('gender'),
                'nationality': int(post.get('nationality')),
                'id_number': post.get('id_number'),
                'education_level': post.get('education_level'),
                'enrollment_date': post.get('enrollment_date'),
                'current_memorized_pages': int(post.get('current_memorized_pages', 1)),
                'memorization_level': post.get('memorization_level'),
                'memorization_start_page': int(post.get('memorization_start_page', 1)),
                'memorization_end_page': int(post.get('memorization_end_page', 1)),
                'review_pages': int(post.get('review_pages', 0)),
                'state': 'submitted',
                'email': post.get('email'),
                'phone': post.get('phone', ''),
            }

            if image:
                enrollment_vals['image'] = image

            # إضافة الملفات الجديدة
            if emirates_id_file:
                enrollment_vals['emirates_id_file'] = emirates_id_file
                enrollment_vals['emirates_id_filename'] = emirates_id_filename

            if residence_file:
                enrollment_vals['residence_file'] = residence_file
                enrollment_vals['residence_filename'] = residence_filename

            if passport_file:
                enrollment_vals['passport_file'] = passport_file
                enrollment_vals['passport_filename'] = passport_filename

            if other_document_file:
                enrollment_vals['other_document_file'] = other_document_file
                enrollment_vals['other_document_filename'] = other_document_filename

            enrollment = request.env['quran.enrollment.application'].sudo().create(enrollment_vals)

            # إنشاء المرفقات وربطها بالطلب
            if attachments_to_create:
                attachment_ids = []
                for att_vals in attachments_to_create:
                    att_vals['res_id'] = enrollment.id
                    attachment = request.env['ir.attachment'].sudo().create(att_vals)
                    attachment_ids.append(attachment.id)

                # ربط المرفقات بالطلب
                if attachment_ids:
                    enrollment.sudo().write({
                        'attachment_ids': [(6, 0, attachment_ids)]
                    })

            # عرض صفحة النجاح
            return request.render('quran_center.enrollment_success', {
                'enrollment': enrollment,
                'success': True
            })

        except Exception as e:
            _logger.error(f"Error creating enrollment: {str(e)}")
            # في حالة حدوث خطأ
            from datetime import date

            countries = request.env['res.country'].sudo().search([])
            values = {
                'countries': countries,
                'error': {'general': str(e)},
                'error_message': ['حدث خطأ أثناء إرسال الطلب. يرجى المحاولة مرة أخرى.'],
                'success': False,
                'date': date,
            }
            values.update(post)
            return request.render('quran_center.enrollment_application_form', values)

    @http.route('/enrollment/check-status/<string:application_number>', type='http', auth='public', website=True)
    def check_application_status(self, application_number, **kwargs):
        """التحقق من حالة الطلب"""
        application = request.env['quran.enrollment.application'].sudo().search([
            ('name', '=', application_number)
        ], limit=1)

        return request.render('quran_center.enrollment_status', {
            'application': application
        })
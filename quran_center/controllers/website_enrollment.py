# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64
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
                'email': post.get('email'),  # إضافة البريد الإلكتروني
                'phone': post.get('phone', ''),  # إضافة الهاتف (اختياري)
            }

            if image:
                enrollment_vals['image'] = image

            enrollment = request.env['quran.enrollment.application'].sudo().create(enrollment_vals)

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
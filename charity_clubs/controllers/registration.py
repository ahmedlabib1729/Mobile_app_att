# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
import json
from datetime import datetime


class CharityRegistrationController(http.Controller):

    @http.route('/registration', type='http', auth='public', website=True)
    def registration_home(self, **kwargs):
        """الصفحة الرئيسية للتسجيل - عرض المقرات"""
        headquarters = request.env['charity.headquarters'].sudo().search([
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'headquarters': headquarters,
            'page_title': 'التسجيل في الأنشطة'
        }
        return request.render('charity_clubs.registration_headquarters', values)

    @http.route('/registration/headquarters/<int:headquarters_id>', type='http', auth='public', website=True)
    def registration_departments(self, headquarters_id, **kwargs):
        """عرض أقسام المقر المحدد"""
        headquarters = request.env['charity.headquarters'].sudo().browse(headquarters_id)
        if not headquarters.exists() or not headquarters.is_active:
            return request.redirect('/registration')

        departments = request.env['charity.departments'].sudo().search([
            ('headquarters_id', '=', headquarters_id),
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'headquarters': headquarters,
            'departments': departments,
            'page_title': f'أقسام {headquarters.name}'
        }
        return request.render('charity_clubs.registration_departments', values)

    @http.route('/registration/ladies/<int:department_id>', type='http', auth='public', website=True)
    def ladies_registration_form(self, department_id, **kwargs):
        """فورم تسجيل السيدات"""
        department = request.env['charity.departments'].sudo().browse(department_id)
        if not department.exists() or department.type != 'ladies':
            return request.redirect('/registration')

        # البرامج المتاحة
        programs = request.env['charity.ladies.program'].sudo().search([
            ('department_id', '=', department_id),
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'department': department,
            'headquarters': department.headquarters_id,
            'programs': programs,
            'countries': request.env['res.country'].sudo().search([]),
            'page_title': f'التسجيل في {department.name}'
        }
        return request.render('charity_clubs.ladies_registration_form', values)

    @http.route('/registration/clubs/<int:department_id>', type='http', auth='public', website=True)
    def clubs_list(self, department_id, **kwargs):
        """عرض النوادي في القسم"""
        department = request.env['charity.departments'].sudo().browse(department_id)
        if not department.exists() or department.type != 'clubs':
            return request.redirect('/registration')

        clubs = request.env['charity.clubs'].sudo().search([
            ('department_id', '=', department_id),
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'department': department,
            'headquarters': department.headquarters_id,
            'clubs': clubs,
            'page_title': f'نوادي {department.name}'
        }
        return request.render('charity_clubs.registration_clubs', values)

    @http.route('/registration/club/<int:club_id>', type='http', auth='public', website=True)
    def club_registration_form(self, club_id, **kwargs):
        """فورم تسجيل النوادي"""
        club = request.env['charity.clubs'].sudo().browse(club_id)
        if not club.exists() or not club.is_active:
            return request.redirect('/registration')

        # الترمات المتاحة
        today = fields.Date.today()
        terms = request.env['charity.club.terms'].sudo().search([
            ('club_id', '=', club_id),
            ('is_active', '=', True),
            ('date_to', '>=', today)
        ])

        values = {
            'club': club,
            'department': club.department_id,
            'headquarters': club.department_id.headquarters_id,
            'terms': terms,
            'countries': request.env['res.country'].sudo().search([]),
            'page_title': f'التسجيل في {club.name}'
        }
        return request.render('charity_clubs.club_registration_form', values)

    @http.route('/registration/submit/ladies', type='json', auth='public', website=True, csrf=False)
    def submit_ladies_registration(self, **post):
        """معالجة تسجيل السيدات"""
        try:
            # التحقق من البيانات المطلوبة
            required_fields = ['department_id', 'full_name', 'mobile', 'whatsapp',
                               'birth_date', 'email', 'booking_type']

            for field in required_fields:
                if not post.get(field):
                    return {'success': False, 'error': f'الحقل {field} مطلوب'}

            # التحقق من الملفات المطلوبة
            required_files = ['id_card_file', 'passport_file', 'residence_file']
            for file_field in required_files:
                if not post.get(file_field):
                    file_names = {
                        'id_card_file': 'صورة الهوية',
                        'passport_file': 'صورة جواز السفر',
                        'residence_file': 'صورة الإقامة'
                    }
                    return {'success': False, 'error': f'يجب رفع {file_names.get(file_field, file_field)}'}

            # إنشاء الحجز
            booking_vals = {
                'headquarters_id': int(post.get('headquarters_id')),
                'department_id': int(post.get('department_id')),
                'booking_type': post.get('booking_type'),
                'full_name': post.get('full_name'),
                'mobile': post.get('mobile'),
                'whatsapp': post.get('whatsapp'),
                'birth_date': post.get('birth_date'),
                'email': post.get('email'),
                'state': 'draft'
            }

            # إضافة الملفات
            import base64
            if post.get('id_card_file'):
                booking_vals['id_card_file'] = base64.b64decode(post.get('id_card_file'))
                booking_vals['id_card_filename'] = post.get('id_card_file_name', 'id_card.pdf')

            if post.get('passport_file'):
                booking_vals['passport_file'] = base64.b64decode(post.get('passport_file'))
                booking_vals['passport_filename'] = post.get('passport_file_name', 'passport.pdf')

            if post.get('residence_file'):
                booking_vals['residence_file'] = base64.b64decode(post.get('residence_file'))
                booking_vals['residence_filename'] = post.get('residence_file_name', 'residence.pdf')

            # إضافة البرامج إذا تم اختيارها
            if post.get('program_ids'):
                program_ids = json.loads(post.get('program_ids'))
                booking_vals['program_ids'] = [(6, 0, program_ids)]

            booking = request.env['charity.booking.registrations'].sudo().create(booking_vals)

            # محاولة تأكيد الحجز
            try:
                booking.action_confirm()
            except Exception as e:
                pass  # في حالة فشل التأكيد، نترك الحجز كمسودة

            return {
                'success': True,
                'message': 'تم التسجيل بنجاح',
                'booking_id': booking.id
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/registration/submit/club', type='json', auth='public', website=True, csrf=False)
    def submit_club_registration(self, **post):
        """معالجة تسجيل النوادي"""
        try:
            # التحقق من البيانات المطلوبة
            required_fields = ['headquarters_id', 'department_id', 'club_id', 'term_id',
                               'full_name', 'birth_date', 'gender', 'nationality',
                               'id_number', 'student_grade', 'mother_name', 'mother_mobile',
                               'father_name', 'father_mobile']

            for field in required_fields:
                if not post.get(field):
                    return {'success': False, 'error': f'الحقل {field} مطلوب'}

            # إنشاء التسجيل
            registration_vals = {
                'headquarters_id': int(post.get('headquarters_id')),
                'department_id': int(post.get('department_id')),
                'club_id': int(post.get('club_id')),
                'term_id': int(post.get('term_id')),
                'registration_type': 'new',
                'full_name': post.get('full_name'),
                'birth_date': post.get('birth_date'),
                'gender': post.get('gender'),
                'nationality': int(post.get('nationality')),
                'id_type': post.get('id_type', 'emirates_id'),
                'id_number': post.get('id_number'),
                'student_grade': post.get('student_grade'),
                'mother_name': post.get('mother_name'),
                'mother_mobile': post.get('mother_mobile'),
                'father_name': post.get('father_name'),
                'father_mobile': post.get('father_mobile'),
                'mother_whatsapp': post.get('mother_whatsapp', ''),
                'email': post.get('email', ''),
                'arabic_education_type': post.get('arabic_education_type'),
                'previous_roayati_member': post.get('previous_roayati_member') == 'true',
                'previous_arabic_club': post.get('previous_arabic_club') == 'true',
                'previous_qaida_noorania': post.get('previous_qaida_noorania') == 'true',
                'quran_memorization': post.get('quran_memorization', ''),
                'has_health_requirements': post.get('has_health_requirements') == 'true',
                'health_requirements': post.get('health_requirements', ''),
                'photo_consent': post.get('photo_consent') == 'true',
                'state': 'draft'
            }

            registration = request.env['charity.club.registrations'].sudo().create(registration_vals)

            return {
                'success': True,
                'message': 'تم التسجيل بنجاح',
                'registration_id': registration.id
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/registration/success/<string:type>/<int:record_id>', type='http', auth='public', website=True)
    def registration_success(self, type, record_id, **kwargs):
        """صفحة النجاح بعد التسجيل"""
        if type == 'ladies':
            record = request.env['charity.booking.registrations'].sudo().browse(record_id)
            record_name = 'حجز'
        else:
            record = request.env['charity.club.registrations'].sudo().browse(record_id)
            record_name = 'تسجيل'

        if not record.exists():
            return request.redirect('/registration')

        values = {
            'record': record,
            'record_type': type,
            'record_name': record_name,
            'page_title': 'تم التسجيل بنجاح'
        }
        return request.render('charity_clubs.registration_success', values)
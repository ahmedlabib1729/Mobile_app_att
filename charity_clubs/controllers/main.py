# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import base64


class CharityWebsite(http.Controller):

    @http.route(['/clubs', '/clubs/page/<int:page>'], type='http', auth='public', website=True)
    def clubs_list(self, page=1, **kwargs):
        """عرض قائمة النوادي"""
        Club = request.env['charity.club']

        # عدد النوادي في الصفحة
        clubs_per_page = 6

        # النوادي النشطة فقط
        domain = [('active', '=', True)]

        # حساب الصفحات
        total_clubs = Club.search_count(domain)
        pager = request.website.pager(
            url='/clubs',
            total=total_clubs,
            page=page,
            step=clubs_per_page,
            scope=7,
            url_args=kwargs
        )

        # جلب النوادي
        clubs = Club.search(domain, limit=clubs_per_page, offset=pager['offset'])

        values = {
            'clubs': clubs,
            'pager': pager,
        }

        return request.render('charity_clubs.clubs_list', values)

    @http.route(['/clubs/<model("charity.club"):club>'], type='http', auth='public', website=True)
    def club_details(self, club, **kwargs):
        """عرض تفاصيل النادي وبرامجه"""
        # البرامج النشطة والمفتوحة للتسجيل
        programs = club.program_ids.filtered(
            lambda p: p.active and p.state in ['open', 'ongoing']
        )

        values = {
            'club': club,
            'programs': programs,
            'main_object': club,
        }

        return request.render('charity_clubs.club_details', values)

    @http.route(['/programs/<model("club.program"):program>'], type='http', auth='public', website=True)
    def program_details(self, program, **kwargs):
        """عرض تفاصيل البرنامج"""
        values = {
            'program': program,
            'club': program.club_id,
            'main_object': program,
        }

        return request.render('charity_clubs.program_details', values)

    @http.route(['/programs/<model("club.program"):program>/register'], type='http', auth='public', website=True)
    def program_register_form(self, program, **kwargs):
        """عرض فورم التسجيل"""
        if program.is_full:
            return request.render('charity_clubs.program_full', {'program': program})

        countries = request.env['res.country'].sudo().search([])

        values = {
            'program': program,
            'club': program.club_id,
            'countries': countries,
            'error': {},
            'values': {},
        }

        return request.render('charity_clubs.registration_form', values)

    @http.route(['/programs/<model("club.program"):program>/register/submit'], type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def program_register_submit(self, program, **kwargs):
        """معالجة بيانات التسجيل"""
        error = {}
        values = {}

        # التحقق من البيانات المطلوبة
        required_fields = [
            'student_name', 'birth_date', 'gender', 'nationality_id',
            'native_language', 'father_name', 'mother_name', 'parent_mobile'
        ]

        for field in required_fields:
            if not kwargs.get(field):
                error[field] = 'هذا الحقل مطلوب'
            else:
                values[field] = kwargs.get(field)




        # حفظ باقي البيانات
        optional_fields = [
            'school_name', 'class_level', 'mother_whatsapp',
            'parent_email', 'street', 'city', 'state_id', 'attended_arabic_club',
            'attended_summer_activities', 'interested_quran', 'medical_conditions',
            'allergies', 'photo_permission', 'notes', 'selected_terms','quran_memorisation'
        ]

        for field in optional_fields:
            if kwargs.get(field):
                values[field] = kwargs.get(field)

        # معالجة photo_permission كـ boolean
        if kwargs.get('photo_permission'):
            values['photo_permission'] = True
        else:
            values['photo_permission'] = False

        # معالجة الملفات
        if 'emirates_id_copy' in request.httprequest.files:
            file = request.httprequest.files['emirates_id_copy']
            if file:
                values['emirates_id_copy'] = base64.b64encode(file.read())
                values['emirates_id_filename'] = file.filename

        if 'student_photo' in request.httprequest.files:
            file = request.httprequest.files['student_photo']
            if file:
                values['student_photo'] = base64.b64encode(file.read())
                values['student_photo_filename'] = file.filename

        if error:
            countries = request.env['res.country'].sudo().search([])
            return request.render('charity_clubs.registration_form', {
                'program': program,
                'club': program.club_id,
                'countries': countries,
                'error': error,
                'values': values,
            })

        # إنشاء التسجيل
        try:
            Registration = request.env['program.registration'].sudo()

            # تحضير البيانات
            registration_vals = {
                'program_id': program.id,
                'state': 'draft',
                'selected_terms': values.get('selected_terms', 'all'),
            }

            # نسخ كل القيم
            for key, value in values.items():
                registration_vals[key] = value

            # تحويل القيم للنوع الصحيح
            if 'nationality_id' in registration_vals:
                registration_vals['nationality_id'] = int(registration_vals['nationality_id'])
            if 'state_id' in registration_vals and registration_vals['state_id']:
                registration_vals['state_id'] = int(registration_vals['state_id'])

            # إنشاء التسجيل
            registration = Registration.create(registration_vals)

            # تقديم التسجيل مباشرة
            registration.action_submit()

            # إرسال إيميل تأكيد
            template = request.env.ref('charity_clubs.mail_template_registration_confirmation', False)
            if template:
                template.sudo().send_mail(registration.id, force_send=True)

            return request.render('charity_clubs.registration_success', {
                'registration': registration,
                'program': program,
                'club': program.club_id,
            })

        except Exception as e:
            error['general'] = f'حدث خطأ أثناء التسجيل: {str(e)}'
            countries = request.env['res.country'].sudo().search([])
            return request.render('charity_clubs.registration_form', {
                'program': program,
                'club': program.club_id,
                'countries': countries,
                'error': error,
                'values': values,
            })

    @http.route(['/my/registrations'], type='http', auth='user', website=True)
    def my_registrations(self, **kwargs):
        """عرض تسجيلات المستخدم"""
        partner = request.env.user.partner_id
        registrations = request.env['program.registration'].search([
            ('partner_id', '=', partner.id)
        ])

        values = {
            'registrations': registrations,
        }

        return request.render('charity_clubs.my_registrations', values)
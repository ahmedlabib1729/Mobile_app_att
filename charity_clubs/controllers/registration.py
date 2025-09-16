# -*- coding: utf-8 -*-

import hashlib
import json
import logging
from datetime import datetime, timedelta
import base64
from werkzeug.exceptions import NotFound
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


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
    def ladies_selection(self, department_id, **kwargs):
        """صفحة اختيار نوع التسجيل (برامج أو ورش)"""
        department = request.env['charity.departments'].sudo().browse(department_id)
        if not department.exists() or department.type != 'ladies':
            return request.redirect('/registration')

        values = {
            'department': department,
            'headquarters': department.headquarters_id,
            'page_title': f'التسجيل في {department.name}'
        }
        return request.render('charity_clubs.ladies_selection_page', values)

    @http.route('/registration/ladies/<int:department_id>/programs', type='http', auth='public', website=True)
    def ladies_programs_form(self, department_id, **kwargs):
        """فورم تسجيل البرامج"""
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
            'booking_mode': 'programs',
            'page_title': f'التسجيل في برامج {department.name}'
        }
        return request.render('charity_clubs.ladies_registration_form', values)

    @http.route('/registration/ladies/<int:department_id>/workshops', type='http', auth='public', website=True)
    def ladies_workshops_form(self, department_id, **kwargs):
        """فورم تسجيل الورش"""
        department = request.env['charity.departments'].sudo().browse(department_id)
        if not department.exists() or department.type != 'ladies':
            return request.redirect('/registration')

        # الورش المتاحة
        workshops = request.env['charity.ladies.workshop'].sudo().search([
            ('department_id', '=', department_id),
            ('is_active', '=', True),
            ('active', '=', True)
        ])

        values = {
            'department': department,
            'headquarters': department.headquarters_id,
            'workshops': workshops,
            'countries': request.env['res.country'].sudo().search([]),
            'booking_mode': 'workshop',
            'page_title': f'التسجيل في ورش {department.name}'
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

        # إضافة الصفوف الدراسية
        grades = request.env['school.grade'].sudo().search([], order='id')

        values = {
            'club': club,
            'department': club.department_id,
            'headquarters': club.department_id.headquarters_id,
            'terms': terms,
            'countries': request.env['res.country'].sudo().search([]),
            'grades': grades,  # السطر الجديد
            'page_title': f'التسجيل في {club.name}'
        }
        return request.render('charity_clubs.club_registration_form', values)

    # تحديث معالج تسجيل السيدات
    @http.route('/registration/submit/ladies', type='json', auth='public', website=True, csrf=False)
    def submit_ladies_registration(self, **post):
        """معالجة تسجيل السيدات مع التوجيه المباشر للدفع"""
        try:
            import base64
            _logger.info(f"Received ladies registration data: {post}")

            # التحقق من البيانات المطلوبة
            required_fields = ['department_id', 'full_name', 'mobile', 'whatsapp',
                               'birth_date', 'email', 'booking_type', 'lady_type']

            for field in required_fields:
                if not post.get(field):
                    _logger.error(f"Missing required field: {field}")
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
                    _logger.error(f"Missing required file: {file_field}")
                    return {'success': False, 'error': f'يجب رفع {file_names.get(file_field, file_field)}'}

            # التحقق من نوع الحجز (برامج أو ورش)
            booking_mode = post.get('booking_mode', 'programs')

            # التحقق الإضافي حسب نوع الحجز
            if booking_mode == 'workshop':
                if not post.get('workshop_id'):
                    return {'success': False, 'error': 'يجب اختيار ورشة'}
            # البرامج اختيارية، لذا لا نحتاج للتحقق من وجودها

            # البحث عن عضوة موجودة
            mobile = post.get('mobile')
            whatsapp = post.get('whatsapp')
            department_id = int(post.get('department_id'))

            existing_member = request.env['charity.member.profile'].sudo().search([
                '|',
                ('mobile', '=', mobile),
                ('whatsapp', '=', whatsapp)
            ], limit=1)

            # إعداد بيانات الحجز
            booking_vals = {
                'headquarters_id': int(post.get('headquarters_id')),
                'department_id': department_id,
                'full_name': post.get('full_name'),
                'mobile': post.get('mobile'),
                'whatsapp': post.get('whatsapp'),
                'birth_date': post.get('birth_date'),
                'email': post.get('email'),
                'lady_type': post.get('lady_type'),
                'booking_mode': booking_mode,  # إضافة نوع الحجز
                'state': 'draft'
            }

            if existing_member:
                booking_vals['booking_type'] = 'existing'
                booking_vals['member_id'] = existing_member.id
            else:
                booking_vals['booking_type'] = 'new'

            # معالجة الملفات بالطريقة الصحيحة
            # ملف الهوية
            if post.get('id_card_file'):
                try:
                    file_data = post.get('id_card_file')
                    file_name = post.get('id_card_file_name', 'id_card.jpg')

                    # معالجة البيانات حسب نوعها
                    if isinstance(file_data, str):
                        if file_data.startswith('data:'):
                            # إزالة الـ header والحصول على base64 فقط
                            header, base64_data = file_data.split(',', 1)
                            # التحقق من صحة base64
                            binary_data = base64.b64decode(base64_data)
                            # حفظ كـ base64 string (ما يتوقعه Odoo)
                            booking_vals['id_card_file'] = base64_data
                        else:
                            # افتراض أنها base64 بالفعل
                            # التحقق من صحتها
                            test = base64.b64decode(file_data)
                            booking_vals['id_card_file'] = file_data
                    else:
                        # إذا كانت binary، حولها لـ base64
                        booking_vals['id_card_file'] = base64.b64encode(file_data).decode('ascii')

                    booking_vals['id_card_filename'] = file_name
                    _logger.info(f"Processed id_card_file: {file_name}")

                except Exception as e:
                    _logger.error(f"Error processing id_card_file: {str(e)}")
                    return {'success': False, 'error': f'خطأ في معالجة صورة الهوية: {str(e)}'}

            # ملف جواز السفر
            if post.get('passport_file'):
                try:
                    file_data = post.get('passport_file')
                    file_name = post.get('passport_file_name', 'passport.jpg')

                    if isinstance(file_data, str):
                        if file_data.startswith('data:'):
                            header, base64_data = file_data.split(',', 1)
                            binary_data = base64.b64decode(base64_data)
                            booking_vals['passport_file'] = base64_data
                        else:
                            test = base64.b64decode(file_data)
                            booking_vals['passport_file'] = file_data
                    else:
                        booking_vals['passport_file'] = base64.b64encode(file_data).decode('ascii')

                    booking_vals['passport_filename'] = file_name
                    _logger.info(f"Processed passport_file: {file_name}")

                except Exception as e:
                    _logger.error(f"Error processing passport_file: {str(e)}")
                    return {'success': False, 'error': f'خطأ في معالجة صورة جواز السفر: {str(e)}'}

            # ملف الإقامة
            if post.get('residence_file'):
                try:
                    file_data = post.get('residence_file')
                    file_name = post.get('residence_file_name', 'residence.jpg')

                    if isinstance(file_data, str):
                        if file_data.startswith('data:'):
                            header, base64_data = file_data.split(',', 1)
                            binary_data = base64.b64decode(base64_data)
                            booking_vals['residence_file'] = base64_data
                        else:
                            test = base64.b64decode(file_data)
                            booking_vals['residence_file'] = file_data
                    else:
                        booking_vals['residence_file'] = base64.b64encode(file_data).decode('ascii')

                    booking_vals['residence_filename'] = file_name
                    _logger.info(f"Processed residence_file: {file_name}")

                except Exception as e:
                    _logger.error(f"Error processing residence_file: {str(e)}")
                    return {'success': False, 'error': f'خطأ في معالجة صورة الإقامة: {str(e)}'}

            # إضافة البرامج أو الورشة حسب نوع الحجز
            if booking_mode == 'programs' and post.get('program_ids'):
                try:
                    program_ids = json.loads(post.get('program_ids'))
                    booking_vals['program_ids'] = [(6, 0, program_ids)]
                    _logger.info(f"Programs selected: {program_ids}")
                except Exception as e:
                    _logger.error(f"Error parsing program_ids: {str(e)}")

            elif booking_mode == 'workshop' and post.get('workshop_id'):
                workshop_id = int(post.get('workshop_id'))
                booking_vals['workshop_id'] = workshop_id

                # التحقق من توفر مقاعد في الورشة
                workshop = request.env['charity.ladies.workshop'].sudo().browse(workshop_id)
                if workshop and workshop.available_seats <= 0:
                    return {'success': False, 'error': 'الورشة ممتلئة، لا يمكن التسجيل'}
                _logger.info(f"Workshop selected: {workshop_id}")

            # إنشاء الحجز
            try:
                booking = request.env['charity.booking.registrations'].sudo().create(booking_vals)
                _logger.info(f"Booking created with ID: {booking.id}")
            except Exception as e:
                _logger.error(f"Error creating booking: {str(e)}")
                return {'success': False, 'error': f'خطأ في إنشاء الحجز: {str(e)}'}

            # تأكيد الحجز لإنشاء الفاتورة
            try:
                booking.action_confirm()
                _logger.info(f"Booking confirmed. Invoice created: {bool(booking.invoice_id)}")
            except Exception as e:
                _logger.error(f"Error confirming booking: {str(e)}")
                # إذا فشل التأكيد، نحذف الحجز ونرجع الخطأ
                booking.unlink()
                return {'success': False, 'error': f'خطأ في تأكيد الحجز: {str(e)}'}

            # إعداد النتيجة
            if booking.invoice_id:
                # إنشاء payment link للفاتورة
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

                # إنشاء access token إذا لم يكن موجود
                if not booking.invoice_id.access_token:
                    booking.invoice_id._portal_ensure_token()

                # رابط الدفع المباشر من Odoo
                payment_url = f"{base_url}/my/invoices/{booking.invoice_id.id}?access_token={booking.invoice_id.access_token}"

                # الحصول على السعر النهائي
                final_amount = booking.final_price if hasattr(booking,
                                                              'final_price') else booking.invoice_id.amount_total

                result = {
                    'success': True,
                    'message': 'تم التسجيل بنجاح',
                    'booking_id': booking.id,
                    'payment_url': payment_url,
                    'invoice_id': booking.invoice_id.id,
                    'invoice_name': booking.invoice_id.name,
                    'amount': final_amount,
                    'booking_mode': booking_mode
                }

                if booking_mode == 'workshop' and workshop:
                    result['workshop_name'] = workshop.name

                return result
            else:
                return {
                    'success': True,
                    'message': 'تم التسجيل بنجاح',
                    'booking_id': booking.id,
                    'has_invoice': False,
                    'booking_mode': booking_mode
                }

        except Exception as e:
            _logger.error(f"Error in ladies registration: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}

    @http.route('/registration/payment/confirm/<int:booking_id>', type='http', auth='public', website=True)
    def payment_confirmation(self, booking_id, **kwargs):
        """صفحة تأكيد الدفع"""
        booking = request.env['charity.booking.registrations'].sudo().browse(booking_id)

        if not booking.exists():
            return request.redirect('/registration')

        # التحقق من حالة الدفع
        if booking.invoice_id and booking.invoice_id.payment_state == 'paid':
            return request.redirect(f'/registration/success/ladies/{booking.id}')

        values = {
            'booking': booking,
            'page_title': 'تأكيد الدفع'
        }

        return request.render('charity_clubs.payment_confirmation', values)

    @http.route('/registration/invoice/<int:invoice_id>/<string:access_token>', type='http', auth='public',
                website=True)
    def show_invoice(self, invoice_id, access_token, **kwargs):
        """عرض صفحة الفاتورة للدفع"""
        try:
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', invoice_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not invoice:
                return request.redirect('/registration')

            # التحقق من حالة الدفع
            if invoice.payment_state == 'paid':
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', '=', invoice.id)
                ], limit=1)
                if booking:
                    return request.redirect(f'/registration/success/ladies/{booking.id}')

            # الحصول على طرق الدفع المتاحة
            payment_providers = request.env['payment.provider'].sudo().search([
                ('state', 'in', ['enabled', 'test']),
                ('is_published', '=', True),
                ('company_id', '=', invoice.company_id.id),
            ])

            # الحصول على payment tokens للشريك
            payment_tokens = request.env['payment.token'].sudo().search([
                ('partner_id', '=', invoice.partner_id.id),
                ('provider_id', 'in', payment_providers.ids),
            ])

            # معلومات الدفع
            payment_context = {
                'amount': invoice.amount_residual,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'providers': payment_providers,
                'tokens': payment_tokens,
                'invoice_id': invoice.id,
                'access_token': access_token,
                'landing_route': f'/registration/payment/status?invoice_id={invoice.id}&access_token={access_token}',
            }

            values = {
                'invoice': invoice,
                'page_title': f'الفاتورة {invoice.name}',
                'access_token': access_token,
                'payment_context': payment_context,
                'partner': invoice.partner_id,
                'amount': invoice.amount_residual,
                'currency': invoice.currency_id,
                'show_test_mode': True,
            }

            return request.render('charity_clubs.invoice_payment_page', values)

        except Exception as e:
            _logger.error(f"Error showing invoice: {str(e)}")
            return request.redirect('/registration')

    @http.route('/registration/payment/transaction', type='json', auth='public', website=True, csrf=False)
    def create_payment_transaction(self, **kwargs):
        """إنشاء معاملة دفع جديدة"""
        try:
            invoice_id = int(kwargs.get('invoice_id'))
            access_token = kwargs.get('access_token')
            provider_id = int(kwargs.get('provider_id'))

            # التحقق من الفاتورة
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', invoice_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not invoice:
                return {'error': 'الفاتورة غير موجودة'}

            # التحقق من provider
            provider = request.env['payment.provider'].sudo().browse(provider_id)
            if not provider.exists():
                return {'error': 'طريقة الدفع غير موجودة'}

            # الحصول على payment method
            payment_method = request.env['payment.method'].sudo().search([
                ('code', '=', provider.code),
                ('active', '=', True)
            ], limit=1)

            if not payment_method:
                # إنشاء payment method إذا لم يكن موجود
                payment_method = request.env['payment.method'].sudo().create({
                    'name': provider.name,
                    'code': provider.code,
                    'active': True,
                    'provider_ids': [(4, provider.id)]
                })

            # إنشاء معاملة الدفع
            tx_values = {
                'provider_id': provider_id,
                'payment_method_id': payment_method.id,  # إضافة payment_method_id
                'amount': invoice.amount_residual,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'invoice_ids': [(6, 0, [invoice.id])],
                'reference': f"{invoice.name}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}",
            }

            tx = request.env['payment.transaction'].sudo().create(tx_values)

            # معالجة حسب نوع provider
            if provider.code in ['manual', 'demo', 'wire_transfer']:
                # تأكيد الدفع مباشرة للطرق اليدوية
                tx._set_done()
                try:
                    tx._reconcile_after_done()
                except:
                    pass

                # البحث عن الحجز
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', '=', invoice.id)
                ], limit=1)

                if booking:
                    booking.write({'state': 'approved'})
                    if booking.subscription_id:
                        booking.subscription_id.state = 'active'

                return {
                    'success': True,
                    'message': 'تم الدفع بنجاح',
                    'redirect_url': f'/registration/success/ladies/{booking.id}' if booking else '/registration'
                }
            else:
                # providers أخرى تحتاج معالجة خاصة
                return {
                    'success': True,
                    'transaction_id': tx.id,
                    'needs_redirect': True
                }

        except Exception as e:
            _logger.error(f"Error creating payment transaction: {str(e)}")
            return {'error': str(e)}

    @http.route('/registration/payment/status', type='http', auth='public', website=True)
    def payment_status(self, **kwargs):
        """صفحة حالة الدفع"""
        try:
            invoice_id = int(kwargs.get('invoice_id'))
            access_token = kwargs.get('access_token')

            # التحقق من الفاتورة
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', invoice_id),
                ('access_token', '=', access_token)
            ], limit=1)

            if not invoice:
                return request.redirect('/registration')

            # البحث عن آخر معاملة
            last_tx = request.env['payment.transaction'].sudo().search([
                ('invoice_ids', 'in', invoice.id)
            ], order='id desc', limit=1)

            # البحث عن الحجز
            booking = request.env['charity.booking.registrations'].sudo().search([
                ('invoice_id', '=', invoice.id)
            ], limit=1)

            # التحقق من حالة الدفع
            if invoice.payment_state == 'paid' or (last_tx and last_tx.state == 'done'):
                # تفعيل الاشتراك إذا لم يكن مفعلاً
                if booking and booking.subscription_id and booking.subscription_id.state != 'active':
                    booking.subscription_id.action_activate()

                if booking:
                    return request.redirect(f'/registration/success/ladies/{booking.id}')

            values = {
                'invoice': invoice,
                'transaction': last_tx,
                'booking': booking,
                'page_title': 'حالة الدفع'
            }

            return request.render('charity_clubs.payment_status_page', values)

        except Exception as e:
            _logger.error(f"Error in payment status: {str(e)}")
            return request.redirect('/registration')

    @http.route('/registration/payment/process/<int:provider_id>', type='json', auth='public', csrf=False)
    def process_provider_payment(self, provider_id, **kwargs):
        """معالجة الدفع حسب provider معين"""
        try:
            invoice_id = int(kwargs.get('invoice_id'))
            access_token = kwargs.get('access_token')

            # التحقق من الصلاحيات
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', invoice_id),
                ('access_token', '=', access_token),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid')
            ], limit=1)

            if not invoice:
                return {'success': False, 'error': 'الفاتورة غير صالحة أو مدفوعة بالفعل'}

            provider = request.env['payment.provider'].sudo().browse(provider_id)
            if not provider.exists() or provider.state != 'enabled':
                return {'success': False, 'error': 'طريقة الدفع غير متاحة'}

            # إنشاء معاملة دفع
            tx_values = {
                'provider_id': provider.id,
                'amount': invoice.amount_residual,
                'currency_id': invoice.currency_id.id,
                'partner_id': invoice.partner_id.id,
                'invoice_ids': [(6, 0, [invoice.id])],
                'reference': f"{invoice.name}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}",
            }

            tx = request.env['payment.transaction'].sudo().create(tx_values)

            # معالجة حسب نوع provider
            if provider.code == 'manual':
                # تأكيد الدفع اليدوي
                tx._set_done()
                tx._reconcile_after_done()

                # البحث عن الحجز وتفعيله
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', '=', invoice.id)
                ], limit=1)

                if booking:
                    booking.write({'state': 'approved'})
                    if booking.subscription_id:
                        booking.subscription_id.action_activate()

                return {
                    'success': True,
                    'message': 'تم الدفع بنجاح',
                    'redirect_url': f'/registration/success/ladies/{booking.id}' if booking else '/registration'
                }
            else:
                # الحصول على نموذج الدفع
                rendering_values = tx._get_specific_rendering_values(provider.code)
                redirect_form = provider.sudo()._render_redirect_form(tx.reference, rendering_values)

                return {
                    'success': True,
                    'transaction_id': tx.id,
                    'redirect_form': redirect_form,
                    'provider_code': provider.code
                }

        except Exception as e:
            _logger.error(f"Error processing payment: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/registration/test-payment/process', type='json', auth='public', csrf=False)
    def process_test_payment(self, **kwargs):
        """معالج دفع تجريبي بسيط"""
        try:
            invoice_id = int(kwargs.get('invoice_id'))
            access_token = kwargs.get('access_token')

            # التحقق من الفاتورة
            invoice = request.env['account.move'].sudo().search([
                ('id', '=', invoice_id),
                ('access_token', '=', access_token),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid')
            ], limit=1)

            if not invoice:
                return {'success': False, 'error': 'الفاتورة غير صالحة'}

            # إنشاء journal entry للدفع
            journal = request.env['account.journal'].sudo().search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', invoice.company_id.id)
            ], limit=1)

            if journal:
                # إنشاء payment
                payment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id': invoice.partner_id.id,
                    'amount': invoice.amount_residual,
                    'currency_id': invoice.currency_id.id,
                    'journal_id': journal.id,
                    'date': fields.Date.today(),

                    'payment_method_line_id': journal.inbound_payment_method_line_ids[
                        0].id if journal.inbound_payment_method_line_ids else False,
                }

                payment = request.env['account.payment'].sudo().create(payment_vals)
                payment.action_post()

                # ربط الدفعة بالفاتورة
                (payment.move_id + invoice).line_ids.filtered(
                    lambda line: line.account_id == invoice.line_ids[0].account_id and not line.reconciled
                ).reconcile()

                _logger.info(f"Test payment created for invoice {invoice.name}")

                # البحث عن الحجز
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', '=', invoice.id)
                ], limit=1)

                if booking:
                    booking.write({'state': 'approved'})
                    if booking.subscription_id:
                        booking.subscription_id.action_activate()

                return {
                    'success': True,
                    'message': 'تم الدفع التجريبي بنجاح',
                    'redirect_url': f'/registration/success/ladies/{booking.id}' if booking else '/registration'
                }

            return {'success': False, 'error': 'لا يوجد journal محاسبي'}

        except Exception as e:
            _logger.error(f"Test payment error: {str(e)}")
            return {'success': False, 'error': str(e)}

    @http.route('/registration/process-payment', type='json', auth='public', website=True, csrf=False)
    def process_payment(self, **post):
        """معالجة الدفع (نموذج مبسط)"""
        try:
            _logger.info(f"Process payment called with: {post}")

            invoice_id = post.get('invoice_id')
            payment_method = post.get('payment_method')

            if not invoice_id:
                return {'success': False, 'error': 'رقم الفاتورة مطلوب'}

            invoice = request.env['account.move'].sudo().browse(int(invoice_id))
            if not invoice.exists():
                return {'success': False, 'error': 'الفاتورة غير موجودة'}

            # التحقق من حالة الدفع
            if invoice.payment_state == 'paid':
                booking = request.env['charity.booking.registrations'].sudo().search([
                    ('invoice_id', '=', invoice.id)
                ], limit=1)

                return {
                    'success': True,
                    'message': 'الفاتورة مدفوعة بالفعل',
                    'redirect_url': f'/registration/success/ladies/{booking.id}' if booking else '/registration'
                }

            # للتجربة، سنضع الفاتورة كمدفوعة مباشرة
            if payment_method == 'test':
                try:
                    _logger.info(f"Processing test payment for invoice {invoice.name}")

                    # الطريقة المبسطة - وضع الفاتورة كمدفوعة مباشرة
                    # نتأكد أن الفاتورة مرحلة
                    if invoice.state == 'draft':
                        invoice.action_post()

                    # إنشاء سجل دفعة بسيط (اختياري)
                    journal = request.env['account.journal'].sudo().search([
                        ('type', 'in', ['bank', 'cash']),
                        ('company_id', '=', invoice.company_id.id)
                    ], limit=1)

                    if journal:
                        # محاولة إنشاء دفعة
                        try:
                            payment_method_id = request.env['account.payment.method'].sudo().search([
                                ('payment_type', '=', 'inbound'),
                                ('code', '=', 'manual')
                            ], limit=1)

                            payment_vals = {
                                'payment_type': 'inbound',
                                'partner_type': 'customer',
                                'partner_id': invoice.partner_id.id,
                                'amount': invoice.amount_residual,
                                'currency_id': invoice.currency_id.id,
                                'journal_id': journal.id,

                            }

                            payment = request.env['account.payment'].sudo().create(payment_vals)
                            payment.action_post()

                            # محاولة التسوية
                            try:
                                # البحث عن السطور المحاسبية للتسوية
                                payment_line = payment.move_id.line_ids.filtered(
                                    lambda l: l.account_id.reconcile and l.debit > 0
                                )
                                invoice_line = invoice.line_ids.filtered(
                                    lambda l: l.account_id.reconcile and l.credit > 0 and not l.reconciled
                                )

                                if payment_line and invoice_line:
                                    (payment_line | invoice_line).reconcile()
                                    _logger.info("Payment reconciled successfully")
                                else:
                                    # إذا فشلت التسوية، نضع الفاتورة كمدفوعة يدوياً
                                    invoice._compute_amount()

                            except Exception as e:
                                _logger.warning(f"Reconciliation failed: {e}, marking invoice as paid manually")

                        except Exception as e:
                            _logger.warning(f"Payment creation failed: {e}, will mark invoice as paid directly")

                    # تحديث حالة الفاتورة يدوياً إذا لم تكن مدفوعة بعد
                    if invoice.payment_state != 'paid':
                        # طريقة بديلة - نسجل دفعة في journal entry مباشرة
                        invoice.sudo().write({
                            'payment_state': 'paid',
                            'amount_residual': 0.0,
                            'payment_state_before_switch': False,
                        })

                        # إضافة ملاحظة في الفاتورة
                        invoice.message_post(
                            body="تم الدفع عن طريق الدفع التجريبي",
                            subject="دفعة تجريبية"
                        )

                    _logger.info(f"Invoice {invoice.name} marked as paid")

                    # البحث عن الحجز المرتبط
                    booking = request.env['charity.booking.registrations'].sudo().search([
                        ('invoice_id', '=', invoice.id)
                    ], limit=1)

                    if booking:
                        _logger.info(f"Found booking {booking.id}")

                        # تحديث حالة الحجز
                        booking.write({'state': 'approved'})

                        # تفعيل الاشتراك
                        if booking.subscription_id and booking.subscription_id.state == 'confirmed':
                            try:
                                # التأكد من أن الفاتورة محدثة
                                booking.invoice_id._compute_payment_state()

                                # تفعيل الاشتراك
                                booking.subscription_id.action_activate()
                                _logger.info("Subscription activated successfully")
                            except Exception as e:
                                _logger.error(f"Failed to activate subscription: {e}")
                                # حتى لو فشل تفعيل الاشتراك، نكمل العملية
                                pass

                        return {
                            'success': True,
                            'message': 'تم الدفع بنجاح',
                            'redirect_url': f'/registration/success/ladies/{booking.id}'
                        }
                    else:
                        _logger.warning("No booking found for this invoice")
                        return {
                            'success': True,
                            'message': 'تم الدفع بنجاح',
                            'redirect_url': '/registration'
                        }

                except Exception as e:
                    _logger.error(f"Error in test payment: {str(e)}")
                    import traceback
                    _logger.error(traceback.format_exc())
                    return {'success': False, 'error': f'خطأ في معالجة الدفع: {str(e)}'}

            return {'success': False, 'error': 'طريقة دفع غير مدعومة'}

        except Exception as e:
            _logger.error(f"General error in process_payment: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}

    # في controllers/main.py

    import hashlib
    import json
    from datetime import datetime, timedelta

    def _validate_emirates_id_format(self, id_number):
        """التحقق من صحة تنسيق رقم الهوية الإماراتية"""
        import re

        if not id_number:
            return False

        # إزالة الفراغات والشرطات للتحقق
        clean_id = id_number.replace('-', '').replace(' ', '').strip()

        # التحقق من الطول والبداية
        if len(clean_id) != 15 or not clean_id.startswith('784'):
            return False

        # التحقق من أن كل الأحرف أرقام
        if not clean_id.isdigit():
            return False

        # التحقق من التنسيق الصحيح
        emirates_id_pattern = re.compile(r'^784-\d{4}-\d{7}-\d$')
        if not emirates_id_pattern.match(id_number):
            # محاولة تنسيق الرقم
            formatted = f"{clean_id[0:3]}-{clean_id[3:7]}-{clean_id[7:14]}-{clean_id[14]}"
            if not emirates_id_pattern.match(formatted):
                return False

        return True

    @http.route('/registration/validate/club', type='json', auth='public', website=True, csrf=False)
    def validate_club_registration(self, **post):
        """
        Validation endpoint - يتحقق من كل البيانات بدون حفظ
        """
        try:
            _logger.info(f"Validation request received for club registration")

            errors = {}
            warnings = []

            # 1. التحقق من الحقول المطلوبة الأساسية
            required_fields = [
                'headquarters_id', 'department_id', 'club_id', 'term_id',
                'full_name', 'birth_date', 'gender', 'nationality',
                'id_number', 'student_grade_id', 'mother_name', 'mother_mobile',
                'father_name', 'father_mobile'
            ]

            field_labels = {
                'headquarters_id': 'المقر',
                'department_id': 'القسم',
                'club_id': 'النادي',
                'term_id': 'الترم',
                'full_name': 'الاسم الثلاثي',
                'birth_date': 'تاريخ الميلاد',
                'gender': 'الجنس',
                'nationality': 'الجنسية',
                'id_number': 'رقم الهوية',
                'student_grade_id': 'الصف الدراسي',
                'mother_name': 'اسم الأم',
                'mother_mobile': 'هاتف الأم',
                'father_name': 'اسم الأب',
                'father_mobile': 'هاتف الأب'
            }

            for field in required_fields:
                if not post.get(field):
                    errors[field] = f'{field_labels.get(field, field)} مطلوب'

            # === التحقق الخاص بالمتطلبات الصحية ===
            if post.get('has_health_requirements') == 'true':
                # إذا تم تحديد وجود متطلبات صحية، يجب ملء التفاصيل
                health_details = post.get('health_requirements', '').strip()
                if not health_details:
                    errors['health_requirements'] = 'يجب كتابة تفاصيل المتطلبات الصحية أو الاحتياجات الخاصة'
                    _logger.warning("Health requirements checked but details are empty")

            # 2. التحقق من صيغة رقم الهوية
            if post.get('id_number'):
                id_type = post.get('id_type', 'emirates_id')
                id_number = post.get('id_number')

                if id_type == 'emirates_id':
                    if not self._validate_emirates_id_format(id_number):
                        errors['id_number'] = 'رقم الهوية الإماراتية غير صحيح. يجب أن يكون بالصيغة: 784-YYYY-XXXXXXX-X'
                    else:
                        # تنسيق رقم الهوية
                        clean_id = id_number.replace('-', '').replace(' ', '').strip()
                        formatted_id = f"{clean_id[0:3]}-{clean_id[3:7]}-{clean_id[7:14]}-{clean_id[14]}"
                        post['id_number'] = formatted_id

                        # التحقق من عدم التكرار
                        existing_student = request.env['charity.student.profile'].sudo().search([
                            ('id_number', '=', formatted_id)
                        ], limit=1)

                        if existing_student:
                            if existing_student.full_name.lower().strip() != post.get('full_name', '').lower().strip():
                                errors['id_number'] = f'رقم الهوية مسجل باسم آخر: {existing_student.full_name}'
                                warnings.append('يحتاج مراجعة الإدارة للتحقق من البيانات')

            # 3. التحقق من الملفات المطلوبة
            if not post.get('id_front_file'):
                errors['id_front_file'] = 'يجب رفع صورة الوجه الأول من الهوية'
            if not post.get('id_back_file'):
                errors['id_back_file'] = 'يجب رفع صورة الوجه الثاني من الهوية'

            # التحقق من ملف إسعاد إذا تم طلب الخصم
            if post.get('esaad_discount') == 'true':
                if not post.get('esaad_card_file'):
                    errors['esaad_card_file'] = 'يجب رفع صورة بطاقة إسعاد عند طلب الخصم'
                else:
                    # إضافة تحذير للمراجعة
                    warnings.append('سيتم مراجعة بطاقة إسعاد للتحقق من صحتها')

            # 4. التحقق من العمر والنادي
            if post.get('birth_date') and post.get('club_id'):
                from datetime import datetime
                from dateutil.relativedelta import relativedelta

                try:
                    birth_date = datetime.strptime(post.get('birth_date'), '%Y-%m-%d').date()
                    today = fields.Date.today()
                    age = relativedelta(today, birth_date).years

                    club = request.env['charity.clubs'].sudo().browse(int(post.get('club_id')))
                    if club.exists():
                        if age < club.age_from or age > club.age_to:
                            errors[
                                'birth_date'] = f'عمر الطفل ({age} سنة) خارج النطاق المسموح للنادي ({club.age_from}-{club.age_to} سنة)'

                        # التحقق من الجنس
                        if club.gender_type != 'both' and post.get('gender') != club.gender_type:
                            gender_text = 'ذكور' if club.gender_type == 'male' else 'إناث'
                            errors['gender'] = f'هذا النادي مخصص لـ {gender_text} فقط'
                except ValueError:
                    errors['birth_date'] = 'تاريخ الميلاد غير صحيح'

            # 5. التحقق من توفر المقاعد
            if post.get('term_id'):
                try:
                    term = request.env['charity.club.terms'].sudo().browse(int(post.get('term_id')))
                    if term.exists():
                        if term.available_seats <= 0:
                            errors['term_id'] = 'لا توجد مقاعد متاحة في هذا الترم'
                        elif term.available_seats < 5:
                            warnings.append(f'تبقى {term.available_seats} مقاعد فقط في هذا الترم')
                except:
                    errors['term_id'] = 'الترم المحدد غير صحيح'

            # إذا كان هناك أخطاء، نرجعها
            if errors:
                _logger.warning(f"Validation failed with errors: {errors}")
                return {
                    'success': False,
                    'errors': errors,
                    'warnings': warnings
                }

            # إنشاء token للبيانات المُتحقق منها
            # حساب hash للبيانات
            data_string = json.dumps(post, sort_keys=True)
            data_hash = hashlib.sha256(data_string.encode()).hexdigest()

            # إنشاء token record
            token_vals = {
                'registration_type': 'club',
                'data_hash': data_hash,
                'validated_data': data_string,
                'ip_address': request.httprequest.remote_addr,
            }

            token_record = request.env['registration.validation.token'].sudo().create(token_vals)

            _logger.info(f"Validation successful, token created: {token_record.token}")

            return {
                'success': True,
                'validation_token': token_record.token,
                'expires_at': token_record.expires_at.isoformat(),
                'warnings': warnings if warnings else []
            }

        except Exception as e:
            _logger.error(f"Error in validation: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            return {
                'success': False,
                'errors': {'general': f'خطأ في النظام: {str(e)}'}
            }

    @http.route('/registration/submit/club', type='json', auth='public', website=True, csrf=False)
    def submit_club_registration(self, **post):
        """معالجة تسجيل النوادي - يتطلب validation token"""
        try:
            _logger.info(f"Submit request received with validation token")

            # ✅ فقط التحقق من التوكن
            validation_token = post.get('validation_token')
            if not validation_token:
                return {
                    'success': False,
                    'error': 'يجب التحقق من البيانات أولاً'
                }

            # البحث عن التوكن
            token_record = request.env['registration.validation.token'].sudo().search([
                ('token', '=', validation_token),
                ('registration_type', '=', 'club'),
                ('is_used', '=', False)
            ], limit=1)

            if not token_record:
                return {
                    'success': False,
                    'error': 'رمز التحقق غير صالح أو منتهي الصلاحية'
                }

            # التحقق من صلاحية التوكن
            if token_record.expires_at < fields.Datetime.now():
                return {
                    'success': False,
                    'error': 'انتهت صلاحية رمز التحقق، يرجى إعادة المحاولة'
                }

            # التحقق من تطابق البيانات
            current_data = post.copy()
            current_data.pop('validation_token', None)

            # إعادة حساب الـ hash
            import hashlib
            import json
            current_hash = hashlib.sha256(
                json.dumps(current_data, sort_keys=True).encode()
            ).hexdigest()

            if current_hash != token_record.data_hash:
                _logger.warning(f"Data mismatch detected. Expected: {token_record.data_hash}, Got: {current_hash}")
                return {
                    'success': False,
                    'error': 'تم تعديل البيانات، يرجى إغلاق الصفحة وفتحها من جديد وإعادة إدخال البيانات'
                }

            # استخدام البيانات المُتحقق منها من التوكن
            validated_data = json.loads(token_record.validated_data)

            # ===== التحقق من التسجيل المكرر قبل الإنشاء =====
            term_id = int(validated_data.get('term_id'))
            id_number = validated_data.get('id_number')

            if term_id and id_number:
                # البحث عن تسجيل مكرر
                duplicate = request.env['charity.club.registrations'].sudo().search([
                    ('id_number', '=', id_number),
                    ('term_id', '=', term_id),
                    ('state', 'not in', ['cancelled', 'rejected'])
                ], limit=1)

                if duplicate:
                    # حذف التوكن المستخدم
                    token_record.unlink()

                    student_name = duplicate.full_name or (
                        duplicate.student_profile_id.full_name if duplicate.student_profile_id else 'غير محدد')
                    term_name = duplicate.term_id.name if duplicate.term_id else 'الترم'

                    _logger.warning(f"Duplicate registration found for ID {id_number} in term {term_id}")

                    return {
                        'success': False,
                        'error': f'❌ لا يمكن التسجيل!\n\n'
                                 f'رقم الهوية {id_number} مسجل بالفعل في {term_name}.\n'
                                 f'اسم الطالب: {student_name}\n'
                                 f'رقم التسجيل السابق: {duplicate.registration_number}\n\n'
                                 f'لا يمكن تسجيل نفس الطالب مرتين في نفس الترم.\n'
                                 f'إذا كنت تريد تعديل التسجيل، يرجى التواصل مع الإدارة.',
                        'duplicate_found': True,
                        'existing_registration': {
                            'id': duplicate.id,
                            'number': duplicate.registration_number,
                            'student_name': student_name,
                            'term_name': term_name
                        }
                    }

            # ===== التحقق أيضاً من ملف الطالب إذا كان موجود =====
            existing_student = request.env['charity.student.profile'].sudo().search([
                ('id_number', '=', id_number)
            ], limit=1)

            if existing_student:
                # التحقق من التسجيلات للطالب الموجود
                duplicate_by_profile = request.env['charity.club.registrations'].sudo().search([
                    ('student_profile_id', '=', existing_student.id),
                    ('term_id', '=', term_id),
                    ('state', 'not in', ['cancelled', 'rejected'])
                ], limit=1)

                if duplicate_by_profile:
                    # حذف التوكن
                    token_record.unlink()

                    term_name = duplicate_by_profile.term_id.name if duplicate_by_profile.term_id else 'الترم'

                    return {
                        'success': False,
                        'error': f'❌ لا يمكن التسجيل!\n\n'
                                 f'الطالب {existing_student.full_name} مسجل بالفعل في {term_name}.\n'
                                 f'رقم التسجيل السابق: {duplicate_by_profile.registration_number}\n\n'
                                 f'لا يمكن تسجيل نفس الطالب مرتين في نفس الترم.',
                        'duplicate_found': True,
                        'existing_registration': {
                            'id': duplicate_by_profile.id,
                            'number': duplicate_by_profile.registration_number,
                            'student_name': existing_student.full_name,
                            'term_name': term_name
                        }
                    }

            # وضع علامة استخدام التوكن
            token_record.is_used = True

            # ✅ الآن إنشاء التسجيل مباشرة بدون أي validations
            registration_vals = {
                'headquarters_id': int(validated_data.get('headquarters_id')),
                'department_id': int(validated_data.get('department_id')),
                'club_id': int(validated_data.get('club_id')),
                'term_id': term_id,
                'registration_type': 'new',
                'full_name': validated_data.get('full_name'),
                'birth_date': validated_data.get('birth_date'),
                'gender': validated_data.get('gender'),
                'nationality': int(validated_data.get('nationality')),
                'id_type': validated_data.get('id_type', 'emirates_id'),
                'id_number': id_number,
                'student_grade_id': int(validated_data.get('student_grade_id')),
                'mother_name': validated_data.get('mother_name'),
                'mother_mobile': validated_data.get('mother_mobile'),
                'father_name': validated_data.get('father_name'),
                'father_mobile': validated_data.get('father_mobile'),
                'mother_whatsapp': validated_data.get('mother_whatsapp', ''),
                'email': validated_data.get('email', ''),
                'arabic_education_type': validated_data.get('arabic_education_type'),
                'previous_roayati_member': validated_data.get('previous_roayati_member') == 'true',
                'previous_arabic_club': validated_data.get('previous_arabic_club') == 'true',
                'previous_qaida_noorania': validated_data.get('previous_qaida_noorania') == 'true',
                'quran_memorization': validated_data.get('quran_memorization', ''),
                'has_health_requirements': validated_data.get('has_health_requirements') == 'true',
                'health_requirements': validated_data.get('health_requirements', ''),
                'how_know_us': validated_data.get('how_know_us', ''),
                'photo_consent': validated_data.get('photo_consent') == 'true',
                'esaad_discount': validated_data.get('esaad_discount') == 'true',
                'state': 'draft'
            }

            # معالجة الملفات (تم التحقق منها في validation)
            if validated_data.get('id_front_file'):
                registration_vals['id_front_file'] = validated_data.get('id_front_file')
                registration_vals['id_front_filename'] = validated_data.get('id_front_filename', 'id_front.jpg')

            if validated_data.get('id_back_file'):
                registration_vals['id_back_file'] = validated_data.get('id_back_file')
                registration_vals['id_back_filename'] = validated_data.get('id_back_filename', 'id_back.jpg')

            if registration_vals['esaad_discount'] and validated_data.get('esaad_card_file'):
                registration_vals['esaad_card_file'] = validated_data.get('esaad_card_file')
                registration_vals['esaad_card_filename'] = validated_data.get('esaad_card_filename', 'esaad.jpg')

            # إنشاء التسجيل مباشرة مع تعطيل constrains مؤقتاً
            try:
                # تعطيل constrains مؤقتاً
                with request.env.cr.savepoint():
                    registration = request.env['charity.club.registrations'].sudo().with_context(
                        skip_duplicate_check=True  # إضافة context لتجاوز التحقق
                    ).create(registration_vals)
                    _logger.info(f"Club registration created with ID: {registration.id}")
            except ValidationError as ve:
                # إذا حدث خطأ validation آخر
                _logger.error(f"Validation error during creation: {str(ve)}")
                token_record.unlink()
                return {'success': False, 'error': str(ve)}

            # تأكيد التسجيل
            try:
                registration.action_confirm()
                _logger.info(f"Registration confirmed. State: {registration.state}")

            except ValidationError as e:
                _logger.error(f"Validation error during confirmation: {str(e)}")
                # حذف التسجيل والتوكن
                registration.unlink()
                token_record.unlink()
                return {'success': False, 'error': str(e)}

            except Exception as e:
                _logger.error(f"Error confirming registration: {str(e)}")
                registration.unlink()
                token_record.unlink()
                return {'success': False, 'error': 'حدث خطأ أثناء معالجة التسجيل'}

            # باقي الكود كما هو (إرجاع النتيجة)
            result = {
                'success': True,
                'registration_id': registration.id,
                'registration_number': registration.registration_number,
                'state': registration.state,
                'has_invoice': bool(registration.invoice_id)
            }

            # معالجة الحالات الخاصة
            if registration.esaad_discount and registration.state == 'pending_review':
                result.update({
                    'message': 'تم استلام طلب التسجيل وسيتم مراجعة بطاقة إسعاد',
                    'needs_review': True,
                    'review_reason': 'يحتاج التحقق من بطاقة إسعاد',
                    'esaad_review': True
                })
            elif registration.state == 'pending_review':
                result.update({
                    'message': 'تم استلام التسجيل وسيتم مراجعته من قبل الإدارة',
                    'needs_review': True,
                    'review_reason': registration.review_reason
                })
            elif registration.state == 'confirmed' and registration.invoice_id:
                if registration.invoice_id.state == 'posted':
                    if not registration.invoice_id.access_token:
                        registration.invoice_id._portal_ensure_token()

                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    payment_url = f"{base_url}/my/invoices/{registration.invoice_id.id}?access_token={registration.invoice_id.access_token}"

                    result.update({
                        'message': 'تم التسجيل بنجاح',
                        'invoice_id': registration.invoice_id.id,
                        'invoice_name': registration.invoice_id.name,
                        'amount': registration.invoice_id.amount_total,
                        'payment_url': payment_url
                    })
            else:
                result['message'] = 'تم التسجيل بنجاح'

            return result

        except Exception as e:
            _logger.error(f"Error in club registration: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())

            # حذف التوكن إذا كان موجود
            if 'token_record' in locals() and token_record.exists():
                token_record.unlink()

            return {'success': False, 'error': str(e)}




    @http.route('/registration/pending/club/<int:registration_id>', type='http', auth='public', website=True)
    def registration_pending(self, registration_id, **kwargs):
        """صفحة التسجيل المعلق"""
        registration = request.env['charity.club.registrations'].sudo().browse(registration_id)

        if not registration.exists() or registration.state != 'pending_review':
            return request.redirect('/registration')

        values = {
            'record': registration,
            'page_title': 'التسجيل قيد المراجعة'
        }

        return request.render('charity_clubs.registration_pending', values)

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

    @http.route('/registration/nursery/<int:department_id>', type='http', auth='public', website=True)
    def nursery_registration_form(self, department_id, **kwargs):
        """فورم تسجيل الحضانة"""
        department = request.env['charity.departments'].sudo().browse(department_id)

        # التحقق من أن القسم موجود وأنه قسم حضانة
        if not department.exists() or department.type != 'nursery':
            return request.redirect('/registration')

        # جلب خطط الحضانة النشطة فقط
        nursery_plans = request.env['charity.nursery.plan'].sudo().search([
            ('department_id', '=', department_id),
            ('is_active', '=', True)
        ], order='attendance_type')

        # جلب تكوينات صفوف الحضانة النشطة
        nursery_classes = request.env['nursery.class.config'].sudo().search([
            ('department_id', '=', department_id),
            ('is_active', '=', True)
        ], order='sequence')

        # جلب الدول
        countries = request.env['res.country'].sudo().search([])

        values = {
            'department': department,
            'headquarters': department.headquarters_id,
            'nursery_plans': nursery_plans,
            'nursery_classes': nursery_classes,  # إضافة هذا
            'countries': countries,
            'page_title': f'تسجيل طفل في {department.name}'
        }

        return request.render('charity_clubs.nursery_registration_form', values)

    @http.route('/registration/submit/nursery', type='json', auth='public', website=True, csrf=False)
    def submit_nursery_registration(self, **post):
        """معالجة تسجيل الحضانة"""
        try:
            _logger.info(f"Received nursery registration data: {post}")

            # التحقق من البيانات المطلوبة للطفل
            child_required_fields = [
                'first_name', 'father_name', 'family_name', 'birth_date', 'gender',
                'religion', 'nationality', 'mother_language', 'identity_number', 'child_order'
            ]

            for field in child_required_fields:
                if not post.get(field):
                    return {'success': False, 'error': f'حقل {field} مطلوب'}

            # التحقق من بيانات الوالدين
            parent_required_fields = [
                'mother_name', 'mother_nationality', 'mother_mobile',
                'father_full_name', 'father_nationality', 'father_mobile',
                'home_address', 'father_education_level', 'father_work_status'
            ]

            for field in parent_required_fields:
                if not post.get(field):
                    return {'success': False, 'error': f'حقل {field} مطلوب'}

            # التحقق من معلومات التسجيل
            if not post.get('department_id') or not post.get('nursery_plan_id'):
                return {'success': False, 'error': 'يجب اختيار القسم والخطة'}

            if not post.get('attendance_days'):
                return {'success': False, 'error': 'يجب اختيار عدد أيام الحضور'}

            # التحقق من التأكيد
            if not post.get('confirm_info'):
                return {'success': False, 'error': 'يجب تأكيد صحة المعلومات'}

            # إعداد بيانات التسجيل
            registration_vals = {
                # بيانات الطفل
                'first_name': post.get('first_name'),
                'father_name': post.get('father_name'),
                'family_name': post.get('family_name'),
                'birth_date': post.get('birth_date'),
                'gender': post.get('gender'),
                'child_order': int(post.get('child_order')),
                'religion': post.get('religion'),
                'nationality': int(post.get('nationality')),
                'mother_language': post.get('mother_language'),
                'passport_number': post.get('passport_number', ''),
                'identity_number': post.get('identity_number'),

                # بيانات الأم
                'mother_name': post.get('mother_name'),
                'mother_nationality': int(post.get('mother_nationality')),
                'mother_job': post.get('mother_job', ''),
                'mother_company': post.get('mother_company', ''),
                'mother_mobile': post.get('mother_mobile'),
                'mother_phone': post.get('mother_phone', ''),
                'mother_email': post.get('mother_email', ''),
                'home_address': post.get('home_address'),

                # بيانات الأب
                'father_full_name': post.get('father_full_name'),
                'father_nationality': int(post.get('father_nationality')),
                'father_job': post.get('father_job', ''),
                'father_company': post.get('father_company', ''),
                'father_mobile': post.get('father_mobile'),
                'father_phone': post.get('father_phone', ''),
                'father_email': post.get('father_email', ''),
                'father_education_level': post.get('father_education_level'),
                'father_work_status': post.get('father_work_status'),

                # معلومات التسجيل
                'department_id': int(post.get('department_id')),
                'nursery_plan_id': int(post.get('nursery_plan_id')),
                'attendance_days': post.get('attendance_days'),
                'join_date': post.get('join_date', fields.Date.today()),
                'how_know_us': post.get('how_know_us'),
                'confirm_info': True,
                'registration_type': 'new',
                'state': 'draft'
            }

            # معالجة الأخوة إن وجدوا
            if post.get('has_siblings'):
                # البيانات تأتي كـ lists بالفعل من JavaScript
                sibling_names = post.get('sibling_name[]', [])
                sibling_ages = post.get('sibling_age[]', [])
                sibling_classes = post.get('sibling_class[]', [])

                siblings = []
                for i in range(len(sibling_names)):
                    if sibling_names[i]:
                        siblings.append((0, 0, {
                            'sibling_name': sibling_names[i],
                            'sibling_age': int(sibling_ages[i]) if i < len(sibling_ages) and sibling_ages[i] else 0,
                            'sibling_class': sibling_classes[i] if i < len(sibling_classes) else ''
                        }))

                if siblings:
                    registration_vals['sibling_ids'] = siblings
                    registration_vals['has_siblings'] = True

            # معالجة جهات الطوارئ
            # البيانات تأتي كـ lists بالفعل من JavaScript
            emergency_names = post.get('emergency_name[]', [])
            emergency_mobiles = post.get('emergency_mobile[]', [])
            emergency_relations = post.get('emergency_relationship[]', [])

            emergency_contacts = []
            for i in range(len(emergency_names)):
                if emergency_names[i] and i < len(emergency_mobiles) and emergency_mobiles[i]:
                    emergency_contacts.append((0, 0, {
                        'person_name': emergency_names[i],
                        'mobile': emergency_mobiles[i],
                        'relationship': emergency_relations[i] if i < len(emergency_relations) else ''
                    }))

            if emergency_contacts:
                registration_vals['emergency_contact_ids'] = emergency_contacts

            # التحقق من أهلية العمر
            birth_date = post.get('birth_date')
            department_id = int(post.get('department_id'))

            if birth_date:
                # تحويل التاريخ من نص إلى تاريخ
                birth_date_obj = fields.Date.from_string(birth_date)

                # التحقق من الأهلية
                config_obj = request.env['nursery.class.config'].sudo()
                eligible_configs = config_obj.check_child_eligibility(birth_date_obj, department_id)

                if not eligible_configs:
                    # حساب العمر
                    today = fields.Date.today()
                    age_days = (today - birth_date_obj).days
                    age_years = age_days // 365
                    age_months = (age_days % 365) // 30

                    return {
                        'success': False,
                        'error': f'عمر الطفل ({age_years} سنة و {age_months} شهر) غير مناسب للتسجيل في الحضانة حالياً. '
                                 f'يرجى التأكد من أن عمر الطفل يقع ضمن الفئات العمرية المحددة.'
                    }

            # التحقق من الملفات المطلوبة
            required_files = ['child_id_front', 'child_id_back', 'guardian_id_front', 'guardian_id_back']
            file_names_map = {
                'child_id_front': 'صورة الوجه الأمامي لهوية الطفل',
                'child_id_back': 'صورة الوجه الخلفي لهوية الطفل',
                'guardian_id_front': 'صورة الوجه الأمامي لهوية ولي الأمر',
                'guardian_id_back': 'صورة الوجه الخلفي لهوية ولي الأمر'
            }

            for file_field in required_files:
                if not post.get(file_field):
                    return {'success': False, 'error': f'يجب رفع {file_names_map.get(file_field, file_field)}'}

            # معالجة الملفات المرفوعة بشكل صحيح
            for file_field in required_files:
                if post.get(file_field):
                    try:
                        file_data = post.get(file_field)
                        filename = post.get(f'{file_field}_name', f'{file_field}.pdf')

                        # معالجة البيانات
                        if isinstance(file_data, str):
                            # إزالة البادئة إذا وجدت
                            if ',' in file_data and file_data.startswith('data:'):
                                file_data = file_data.split(',')[1]

                            # فك التشفير من base64 إلى bytes
                            try:
                                decoded_data = base64.b64decode(file_data)
                                registration_vals[file_field] = decoded_data
                            except Exception as decode_error:
                                _logger.error(f"Error decoding {file_field}: {str(decode_error)}")
                                return {'success': False, 'error': f'خطأ في معالجة {file_names_map[file_field]}'}
                        else:
                            # إذا كانت البيانات bytes بالفعل
                            registration_vals[file_field] = file_data

                        registration_vals[f'{file_field}_filename'] = filename
                        _logger.info(f"Processed {file_field}, filename: {filename}")

                    except Exception as e:
                        _logger.error(f"Error processing {file_field}: {str(e)}")
                        return {'success': False, 'error': f'خطأ في معالجة {file_names_map[file_field]}: {str(e)}'}

            # التحقق من وجود الملفات في registration_vals
            _logger.info(
                f"Files in registration_vals: child_id_front: {bool(registration_vals.get('child_id_front'))}, "
                f"child_id_back: {bool(registration_vals.get('child_id_back'))}, "
                f"guardian_id_front: {bool(registration_vals.get('guardian_id_front'))}, "
                f"guardian_id_back: {bool(registration_vals.get('guardian_id_back'))}"
            )

            # إنشاء التسجيل
            registration = request.env['nursery.child.registration'].sudo().create(registration_vals)
            _logger.info(f"Nursery registration created with ID: {registration.id}")

            # محاولة تأكيد التسجيل فقط (بدون اعتماد أو فاتورة)
            try:
                registration.action_confirm()
                _logger.info("Registration confirmed successfully")

                return {
                    'success': True,
                    'message': 'تم التسجيل بنجاح وسيتم مراجعته من قبل الإدارة',
                    'registration_id': registration.id,
                    'has_invoice': False  # لا توجد فاتورة
                }

            except ValidationError as e:
                _logger.error(f"Validation error: {str(e)}")
                registration.unlink()
                return {'success': False, 'error': str(e)}
            except Exception as e:
                _logger.error(f"Error confirming registration: {str(e)}")
                registration.unlink()
                return {'success': False, 'error': 'حدث خطأ أثناء معالجة التسجيل'}

        except Exception as e:
            _logger.error(f"Error in nursery registration: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
            return {'success': False, 'error': str(e)}

    @http.route('/registration/success/nursery/<int:registration_id>', type='http', auth='public', website=True)
    def nursery_registration_success(self, registration_id, **kwargs):
        """صفحة النجاح لتسجيل الحضانة"""
        registration = request.env['nursery.child.registration'].sudo().browse(registration_id)

        if not registration.exists():
            return request.redirect('/registration')

        values = {
            'registration': registration,
            'page_title': 'تم التسجيل بنجاح'
        }

        return request.render('charity_clubs.nursery_registration_success', values)
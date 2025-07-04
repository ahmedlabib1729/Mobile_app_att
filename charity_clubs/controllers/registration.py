# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
import json
import logging
from datetime import datetime
import base64

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

            # إضافة الملفات
            if post.get('id_card_file'):
                booking_vals['id_card_file'] = base64.b64decode(post.get('id_card_file'))
                booking_vals['id_card_filename'] = post.get('id_card_file_name', 'id_card.pdf')

            if post.get('passport_file'):
                booking_vals['passport_file'] = base64.b64decode(post.get('passport_file'))
                booking_vals['passport_filename'] = post.get('passport_file_name', 'passport.pdf')

            if post.get('residence_file'):
                booking_vals['residence_file'] = base64.b64decode(post.get('residence_file'))
                booking_vals['residence_filename'] = post.get('residence_file_name', 'residence.pdf')

            # إضافة البرامج أو الورشة حسب نوع الحجز
            if booking_mode == 'programs' and post.get('program_ids'):
                program_ids = json.loads(post.get('program_ids'))
                booking_vals['program_ids'] = [(6, 0, program_ids)]
            elif booking_mode == 'workshop' and post.get('workshop_id'):
                booking_vals['workshop_id'] = int(post.get('workshop_id'))

                # التحقق من توفر مقاعد في الورشة
                workshop = request.env['charity.ladies.workshop'].sudo().browse(int(post.get('workshop_id')))
                if workshop and workshop.available_seats <= 0:
                    return {'success': False, 'error': 'الورشة ممتلئة، لا يمكن التسجيل'}

            # إنشاء الحجز
            booking = request.env['charity.booking.registrations'].sudo().create(booking_vals)
            _logger.info(f"Booking created with ID: {booking.id}")

            # تأكيد الحجز لإنشاء الفاتورة
            try:
                booking.action_confirm()
                _logger.info(f"Booking confirmed. Invoice created: {bool(booking.invoice_id)}")
            except Exception as e:
                _logger.error(f"Error confirming booking: {str(e)}")
                # إذا فشل التأكيد، نحذف الحجز ونرجع الخطأ
                booking.unlink()
                return {'success': False, 'error': f'خطأ في تأكيد الحجز: {str(e)}'}

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

                return {
                    'success': True,
                    'message': 'تم التسجيل بنجاح',
                    'booking_id': booking.id,
                    'payment_url': payment_url,
                    'invoice_id': booking.invoice_id.id,
                    'invoice_name': booking.invoice_id.name,
                    'amount': final_amount,
                    'booking_mode': booking_mode,
                    'workshop_name': workshop.name if booking_mode == 'workshop' else None
                }
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

    @http.route('/registration/submit/club', type='json', auth='public', website=True, csrf=False)
    def submit_club_registration(self, **post):
        """معالجة تسجيل النوادي مع التأكيد التلقائي أو المراجعة"""
        try:
            _logger.info(f"Received club registration data: {post}")

            # التحقق من البيانات المطلوبة
            required_fields = ['headquarters_id', 'department_id', 'club_id', 'term_id',
                               'full_name', 'birth_date', 'gender', 'nationality',
                               'id_number', 'student_grade_id', 'mother_name', 'mother_mobile',
                               'father_name', 'father_mobile']

            for field in required_fields:
                if not post.get(field):
                    _logger.error(f"Missing required field: {field}")
                    return {'success': False, 'error': f'الحقل {field} مطلوب'}

            # التحقق من الملفات المطلوبة
            if not post.get('id_front_file'):
                return {'success': False, 'error': 'يجب رفع صورة الوجه الأول من الهوية'}

            if not post.get('id_back_file'):
                return {'success': False, 'error': 'يجب رفع صورة الوجه الثاني من الهوية'}

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
                'student_grade_id': int(post.get('student_grade_id')),  # تم التعديل هنا
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

            # إضافة الملفات المرفوعة
            if post.get('id_front_file'):
                registration_vals['id_front_file'] = base64.b64decode(post.get('id_front_file'))
                registration_vals['id_front_filename'] = post.get('id_front_file_name', 'id_front.pdf')

            if post.get('id_back_file'):
                registration_vals['id_back_file'] = base64.b64decode(post.get('id_back_file'))
                registration_vals['id_back_filename'] = post.get('id_back_file_name', 'id_back.pdf')

            # إنشاء التسجيل
            registration = request.env['charity.club.registrations'].sudo().create(registration_vals)
            _logger.info(f"Club registration created with ID: {registration.id}")

            # تأكيد التسجيل تلقائياً
            try:
                registration.action_confirm()
                _logger.info(f"Registration confirmed. State: {registration.state}")

                # إذا فشل التأكيد، نتحقق من السبب
                if registration.state == 'draft':
                    _logger.error("Registration still in draft after confirm attempt")
                    return {
                        'success': False,
                        'error': 'فشل تأكيد التسجيل. يرجى مراجعة البيانات المدخلة.'
                    }

            except ValidationError as e:
                _logger.error(f"Validation error during confirmation: {str(e)}")
                # حذف التسجيل إذا فشل التأكيد
                registration.unlink()
                return {'success': False, 'error': str(e)}
            except Exception as e:
                _logger.error(f"Error confirming registration: {str(e)}")
                import traceback
                _logger.error(traceback.format_exc())
                # حذف التسجيل إذا فشل التأكيد
                registration.unlink()
                return {'success': False, 'error': 'حدث خطأ أثناء معالجة التسجيل'}

            # إرجاع نتيجة مختلفة حسب الحالة
            result = {
                'success': True,
                'registration_id': registration.id,
                'state': registration.state,
                'has_invoice': bool(registration.invoice_id)
            }

            if registration.state == 'pending_review':
                # حالة المراجعة
                result.update({
                    'message': 'تم استلام التسجيل وسيتم مراجعته من قبل الإدارة',
                    'needs_review': True,
                    'review_reason': registration.review_reason
                })
            elif registration.state == 'confirmed' and registration.invoice_id:
                # التأكيد العادي مع فاتورة
                if registration.invoice_id.state == 'posted':  # التأكد أن الفاتورة مرحلة
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
                    # فاتورة موجودة لكن غير مرحلة
                    _logger.warning(f"Invoice exists but not posted for registration {registration.id}")
                    result['message'] = 'تم التسجيل بنجاح'
            else:
                result['message'] = 'تم التسجيل بنجاح'

            return result

        except Exception as e:
            _logger.error(f"Error in club registration: {str(e)}")
            import traceback
            _logger.error(traceback.format_exc())
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
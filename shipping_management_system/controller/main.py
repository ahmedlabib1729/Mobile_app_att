# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class ShipmentWebsite(http.Controller):

    @http.route(['/shipment', '/shipment/request'], type='http', auth='public', website=True)
    def shipment_form(self, **kwargs):
        """عرض صفحة طلب الشحن"""
        # جلب قائمة الدول
        countries = request.env['res.country'].sudo().search([])

        # جلب الفئات للمنتجات
        categories = request.env['product.category'].sudo().search([])

        values = {
            'countries': countries,
            'categories': categories,
            'error': {},
            'success': kwargs.get('success', False)
        }

        return request.render('shipping_management_system.shipment_request_form', values)

    @http.route('/shipment/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def shipment_submit(self, **post):
        """استقبال ومعالجة طلب الشحن"""
        error = {}
        error_message = []

        # التحقق من البيانات المطلوبة
        required_fields = [
            'sender_name', 'sender_phone', 'sender_address', 'sender_city',
            'recipient_name', 'recipient_phone', 'recipient_address', 'recipient_city',
            'product_name', 'weight', 'product_value'
        ]

        for field in required_fields:
            if not post.get(field):
                error[field] = 'missing'
                error_message.append(f'{field.replace("_", " ").title()} is required')

        # إذا كان هناك أخطاء، نرجع للفورم
        if error:
            values = {
                'error': error,
                'error_message': error_message,
                'countries': request.env['res.country'].sudo().search([]),
                'categories': request.env['product.category'].sudo().search([]),
            }
            values.update(post)  # نحتفظ بالبيانات المدخلة
            return request.render('shipping_management_system.shipment_request_form', values)

        try:
            # دالة مساعدة لتحويل القيم للأرقام بأمان
            def safe_float(val, default=0.0):
                try:
                    return float(val) if val else default
                except (ValueError, TypeError):
                    return default

            def safe_int(val, default=0):
                try:
                    return int(val) if val else default
                except (ValueError, TypeError):
                    return default

            # إنشاء أو البحث عن العميل (المرسل)
            sender_partner = self._create_or_get_partner(
                name=post.get('sender_name'),
                phone=post.get('sender_phone'),
                email=post.get('sender_email'),
                street=post.get('sender_address'),
                city=post.get('sender_city'),
                country_id=post.get('sender_country_id')
            )

            # إنشاء أو البحث عن المستلم
            recipient_partner = self._create_or_get_partner(
                name=post.get('recipient_name'),
                phone=post.get('recipient_phone'),
                email=post.get('recipient_email'),
                street=post.get('recipient_address'),
                city=post.get('recipient_city'),
                country_id=post.get('recipient_country_id')
            )

            # تحضير قيم الشحنة
            shipment_vals = {
                'sender_id': sender_partner.id,
                'sender_address': post.get('sender_address'),
                'sender_city': post.get('sender_city'),
                'sender_country_id': safe_int(post.get('sender_country_id')),
                'sender_whatsapp': post.get('sender_whatsapp') or '',
                'sender_pickup_notes': post.get('sender_pickup_notes') or '',

                'recipient_id': recipient_partner.id,
                'recipient_name': post.get('recipient_name'),
                'recipient_phone': post.get('recipient_phone'),
                'recipient_mobile': post.get('recipient_mobile') or '',
                'recipient_email': post.get('recipient_email') or '',
                'recipient_address': post.get('recipient_address'),
                'recipient_city': post.get('recipient_city'),
                'recipient_country_id': safe_int(post.get('recipient_country_id')),
                'recipient_whatsapp': post.get('recipient_whatsapp') or '',
                'recipient_delivery_notes': post.get('recipient_delivery_notes') or '',

                'payment_method': post.get('payment_method', 'prepaid'),
                'shipment_type': post.get('shipment_type', 'package'),
                'notes': post.get('notes') or '',
            }

            # إضافة COD amount إذا كانت طريقة الدفع COD
            if post.get('payment_method') == 'cod':
                shipment_vals['cod_amount'] = safe_float(post.get('cod_amount'))

            # إضافة بيانات المنتج
            shipment_vals['shipment_line_ids'] = [(0, 0, {
                'product_name': post.get('product_name'),
                'category_id': safe_int(post.get('category_id')),
                'quantity': safe_int(post.get('quantity', 1), 1),
                'weight': safe_float(post.get('weight', 0)),
                'length': safe_float(post.get('length')),
                'width': safe_float(post.get('width')),
                'height': safe_float(post.get('height')),
                'product_value': safe_float(post.get('product_value')),
                'fragile': post.get('fragile') == 'on',
            })]

            # إنشاء الشحنة
            shipment = request.env['shipment.order'].sudo().create(shipment_vals)

            # إرسال إيميل تأكيد للعميل
            self._send_confirmation_email(shipment, sender_partner)

            # إرسال إشعار للأوبريشن
            self._notify_operations(shipment)

            # توجيه لصفحة النجاح
            return request.render('shipping_management_system.shipment_success', {
                'shipment': shipment,
                'tracking_number': shipment.order_number
            })

        except Exception as e:
            # في حالة حدوث خطأ
            import traceback
            traceback.print_exc()  # للـ debugging

            values = {
                'error': {'general': str(e)},
                'error_message': [f'An error occurred: {str(e)}'],
                'countries': request.env['res.country'].sudo().search([]),
                'categories': request.env['product.category'].sudo().search([]),
            }
            values.update(post)
            return request.render('shipping_management_system.shipment_request_form', values)

    def _create_or_get_partner(self, name, phone, email=None, street=None, city=None, country_id=None):
        """إنشاء أو البحث عن شريك"""
        Partner = request.env['res.partner'].sudo()

        # البحث بالهاتف أولاً
        domain = [('phone', '=', phone)]
        if email:
            domain = ['|', ('phone', '=', phone), ('email', '=', email)]

        partner = Partner.search(domain, limit=1)

        if not partner:
            # إنشاء شريك جديد
            partner_vals = {
                'name': name,
                'phone': phone,
                'email': email or False,
                'street': street or False,
                'city': city or False,
                'country_id': int(country_id) if country_id and country_id != '' else False,
                'customer_rank': 1,
            }
            partner = Partner.create(partner_vals)

        return partner

    def _send_confirmation_email(self, shipment, customer):
        """إرسال إيميل تأكيد للعميل"""
        if customer.email:
            template = request.env.ref('shipping_management_system.shipment_confirmation_email',
                                       raise_if_not_found=False)
            if template:
                template.sudo().send_mail(shipment.id, force_send=True)

    def _notify_operations(self, shipment):
        """إرسال إشعار لفريق الأوبريشن"""
        # يمكن إضافة إشعار داخلي أو إيميل لفريق الأوبريشن
        operations_group = request.env.ref('base.group_user', raise_if_not_found=False)
        if operations_group:
            shipment.message_post(
                body=f'New shipment request received from website: {shipment.order_number}',
                subject='New Web Shipment Request',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
                partner_ids=operations_group.users.mapped('partner_id').ids
            )

    @http.route('/shipment/track', type='http', auth='public', website=True)
    def track_shipment(self, tracking=None, **kwargs):
        """صفحة تتبع الشحنة"""
        shipment = False
        error = None

        if tracking:
            shipment = request.env['shipment.order'].sudo().search([
                '|',
                ('order_number', '=', tracking),
                ('tracking_number', '=', tracking)
            ], limit=1)

            if not shipment:
                error = 'No shipment found with this tracking number'

        return request.render('shipping_management_system.track_shipment', {
            'shipment': shipment,
            'tracking': tracking,
            'error': error
        })

    @http.route('/shipment/rates', type='json', auth='public', website=True)
    def get_shipping_rates(self, weight=None, from_city=None, to_city=None, **kwargs):
        """API endpoint لحساب أسعار الشحن"""
        if not all([weight, from_city, to_city]):
            return {'error': 'Missing required parameters'}

        try:
            weight = float(weight)

            # البحث عن الخدمات المتاحة
            services = request.env['shipping.company.service'].sudo().search([
                ('active', '=', True),
                '|',
                ('max_weight', '>=', weight),
                ('max_weight', '=', 0)
            ])

            rates = []
            for service in services:
                price = service.calculate_price(weight=weight, value=0, cod=False)
                rates.append({
                    'company': service.company_id.name,
                    'service': service.name,
                    'delivery_time': service.delivery_time,
                    'price': price
                })

            # ترتيب حسب السعر
            rates.sort(key=lambda x: x['price'])

            return {'success': True, 'rates': rates}

        except Exception as e:
            return {'error': str(e)}
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class ShipmentWebsite(http.Controller):

    @http.route(['/shipment', '/shipment/request'], type='http', auth='public', website=True)
    def shipment_form(self, **kwargs):
        """عرض صفحة طلب الشحن"""
        # جلب الفئات للمنتجات
        categories = request.env['product.category'].sudo().search([])

        values = {
            'categories': categories,
            'error': {},
            'success': kwargs.get('success', False)
        }

        # إضافة القيم المحفوظة من POST إذا كان هناك خطأ
        values.update(kwargs)

        return request.render('shipping_management_system.shipment_request_form', values)

    @http.route('/shipment/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def shipment_submit(self, **post):
        """استقبال ومعالجة طلب الشحن مع دعم منتجات متعددة"""
        error = {}
        error_message = []

        # التحقق من البيانات المطلوبة الأساسية
        required_fields = [
            'sender_name', 'sender_phone', 'sender_address', 'sender_city',
            'recipient_name', 'recipient_phone', 'recipient_address', 'recipient_city'
        ]

        for field in required_fields:
            if not post.get(field):
                error[field] = 'missing'
                field_label = field.replace("_", " ").title()
                error_message.append(f'{field_label} is required')

        # التحقق من وجود منتج واحد على الأقل
        products_data = []
        for key in post.keys():
            if key.startswith('products[') and '[name]' in key:
                index = key.split('[')[1].split(']')[0]
                product = {
                    'name': post.get(f'products[{index}][name]'),
                    'category_id': post.get(f'products[{index}][category_id]'),
                    'brand_id': post.get(f'products[{index}][brand_id]'),  # تغيير إلى brand_id
                    'quantity': post.get(f'products[{index}][quantity]'),
                    'weight': post.get(f'products[{index}][weight]'),
                    'value': post.get(f'products[{index}][value]'),
                    'length': post.get(f'products[{index}][length]'),
                    'width': post.get(f'products[{index}][width]'),
                    'height': post.get(f'products[{index}][height]'),
                    'fragile': post.get(f'products[{index}][fragile]') == 'on',
                }

                # التحقق من حقول المنتج المطلوبة
                if not product['name']:
                    error[f'product_{index}_name'] = 'missing'
                    error_message.append(f'Product {int(index) + 1} name is required')
                if not product['weight']:
                    error[f'product_{index}_weight'] = 'missing'
                    error_message.append(f'Product {int(index) + 1} weight is required')
                if not product['value']:
                    error[f'product_{index}_value'] = 'missing'
                    error_message.append(f'Product {int(index) + 1} value is required')

                products_data.append(product)

        if not products_data:
            error['products'] = 'missing'
            error_message.append('At least one product is required')

        # إذا كان هناك أخطاء، نرجع للفورم
        if error:
            values = {
                'error': error,
                'error_message': error_message,
                'categories': request.env['product.category'].sudo().search([]),
                'brands': request.env['product.brand'].sudo().search([('active', '=', True)]),
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

            # الحصول على ID مصر
            egypt = request.env['res.country'].sudo().search([('code', '=', 'EG')], limit=1)
            egypt_id = egypt.id if egypt else False

            # إذا لم يتم العثور على مصر، نحاول بالاسم
            if not egypt_id:
                egypt = request.env['res.country'].sudo().search([
                    '|',
                    ('name', '=', 'Egypt'),
                    ('name', '=', 'مصر')
                ], limit=1)
                egypt_id = egypt.id if egypt else False

            # إنشاء أو البحث عن العميل (المرسل)
            sender_partner = self._create_or_get_partner(
                name=post.get('sender_name'),
                phone=post.get('sender_phone'),
                email=post.get('sender_email'),
                street=post.get('sender_address'),
                street2=post.get('sender_district'),  # إضافة المنطقة
                city=post.get('sender_city'),
                country_id=egypt_id  # استخدام مصر كدولة افتراضية
            )

            # إنشاء أو البحث عن المستلم
            recipient_partner = self._create_or_get_partner(
                name=post.get('recipient_name'),
                phone=post.get('recipient_phone'),
                email=post.get('recipient_email'),
                street=post.get('recipient_address'),
                street2=post.get('recipient_district'),  # إضافة المنطقة
                city=post.get('recipient_city'),
                country_id=egypt_id  # استخدام مصر كدولة افتراضية
            )

            # تحضير قيم الشحنة
            shipment_vals = {
                'sender_id': sender_partner.id,
                'sender_address': post.get('sender_address'),
                'sender_city': post.get('sender_city'),
                'sender_country_id': egypt_id,
                'sender_whatsapp': post.get('sender_whatsapp') or '',
                'sender_pickup_notes': post.get('sender_pickup_notes') or '',

                'recipient_id': recipient_partner.id,
                'recipient_name': post.get('recipient_name'),
                'recipient_phone': post.get('recipient_phone'),
                'recipient_mobile': post.get('recipient_mobile') or '',
                'recipient_email': post.get('recipient_email') or '',
                'recipient_address': post.get('recipient_address'),
                'recipient_city': post.get('recipient_city'),
                'recipient_country_id': egypt_id,
                'recipient_whatsapp': post.get('recipient_whatsapp') or '',
                'recipient_delivery_notes': post.get('recipient_delivery_notes') or '',

                'payment_method': post.get('payment_method', 'prepaid'),
                'shipment_type': post.get('shipment_type', 'package'),
                'package_count': safe_int(post.get('package_count', 1), 1),
                'notes': post.get('notes') or '',
            }

            # إضافة COD amount إذا كانت طريقة الدفع COD
            if post.get('payment_method') == 'cod':
                shipment_vals['cod_amount'] = safe_float(post.get('cod_amount'))

            # تحضير بيانات المنتجات
            shipment_lines = []
            for product in products_data:
                line_vals = {
                    'product_name': product['name'],
                    'category_id': safe_int(product['category_id']) if product['category_id'] else False,
                    'brand_id': safe_int(product['brand_id']) if product['brand_id'] else False,
                    # استخدام brand_id مباشرة
                    'quantity': safe_int(product['quantity'], 1),
                    'weight': safe_float(product['weight'], 0),
                    'length': safe_float(product['length']),
                    'width': safe_float(product['width']),
                    'height': safe_float(product['height']),
                    'product_value': safe_float(product['value']),
                    'fragile': product['fragile'],
                }
                shipment_lines.append((0, 0, line_vals))

            shipment_vals['shipment_line_ids'] = shipment_lines

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
                'categories': request.env['product.category'].sudo().search([]),
                'brands': request.env['product.brand'].sudo().search([('active', '=', True)]),
            }
            values.update(post)
            return request.render('shipping_management_system.shipment_request_form', values)

    def _create_or_get_partner(self, name, phone, email=None, street=None, street2=None, city=None, country_id=None):
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
                'street2': street2 or False,  # إضافة المنطقة/الحي
                'city': city or False,
                'country_id': country_id or False,
                'customer_rank': 1,
            }
            partner = Partner.create(partner_vals)
        else:
            # تحديث بيانات الشريك الموجود إذا لزم الأمر
            update_vals = {}
            if street and not partner.street:
                update_vals['street'] = street
            if street2 and not partner.street2:
                update_vals['street2'] = street2
            if city and not partner.city:
                update_vals['city'] = city
            if country_id and not partner.country_id:
                update_vals['country_id'] = country_id
            if update_vals:
                partner.write(update_vals)

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
        """API endpoint لحساب أسعار الشحن بناء على المحافظات المصرية"""
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
                # يمكن إضافة منطق خاص لحساب السعر بناء على المحافظات
                base_price = service.calculate_price(weight=weight, value=0, cod=False)

                # إضافة رسوم إضافية للمناطق البعيدة
                remote_areas = ['Aswan', 'Red Sea', 'New Valley', 'North Sinai', 'South Sinai', 'Matrouh']
                if from_city in remote_areas or to_city in remote_areas:
                    base_price *= 1.2  # زيادة 20% للمناطق البعيدة

                rates.append({
                    'company': service.company_id.name,
                    'service': service.name,
                    'delivery_time': service.delivery_time,
                    'price': base_price,
                    'from_city': from_city,
                    'to_city': to_city
                })

            # ترتيب حسب السعر
            rates.sort(key=lambda x: x['price'])

            return {'success': True, 'rates': rates}

        except Exception as e:
            return {'error': str(e)}
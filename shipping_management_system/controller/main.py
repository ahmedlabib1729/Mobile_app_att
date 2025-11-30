# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class ShipmentWebsite(http.Controller):

    @http.route('/api/governorates', type='http', auth='public', website=True, csrf=False)
    def api_governorates(self, **kw):
        """جلب كل المحافظات - متاح للجميع بدون تسجيل دخول"""
        governorates = request.env['egypt.governorate'].sudo().search([
            ('active', '=', True)
        ], order='sequence, name')

        data = [{
            'id': gov.id,
            'name': gov.name,
        } for gov in governorates]

        return request.make_response(
            json.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/api/areas/<int:governorate_id>', type='http', auth='public', website=True, csrf=False)
    def api_areas(self, governorate_id, **kw):
        """جلب المناطق لمحافظة معينة - متاح للجميع"""
        areas = request.env['egypt.governorate.area'].sudo().search([
            ('governorate_id', '=', governorate_id),
            ('active', '=', True)
        ], order='sequence, name')

        data = [{
            'id': area.id,
            'name': area.name,
        } for area in areas]

        return request.make_response(
            json.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/api/cities/<int:area_id>', type='http', auth='public', website=True, csrf=False)
    def api_cities(self, area_id, **kw):
        """جلب المدن/الأحياء لمنطقة معينة - متاح للجميع"""
        cities = request.env['egypt.governorate.city'].sudo().search([
            ('area_id', '=', area_id),
            ('active', '=', True)
        ], order='sequence, name')

        data = [{
            'id': city.id,
            'name': city.name,
        } for city in cities]

        return request.make_response(
            json.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/api/categories', type='http', auth='public', website=True, csrf=False)
    def api_categories(self, **kw):
        """جلب التصنيفات"""
        categories = request.env['product.category'].sudo().search([], order='name')
        data = [{'id': cat.id, 'name': cat.name} for cat in categories]
        return request.make_response(
            json.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/api/subcategories/<int:category_id>', type='http', auth='public', website=True, csrf=False)
    def api_subcategories(self, category_id, **kw):
        """جلب التصنيفات الفرعية"""
        subcategories = request.env['product.subcategory'].sudo().search([
            ('category_id', '=', category_id)
        ], order='name')
        data = [{'id': sub.id, 'name': sub.name} for sub in subcategories]
        return request.make_response(
            json.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route('/api/brands', type='http', auth='public', website=True, csrf=False)
    def api_brands(self, **kw):
        """جلب البراندات"""
        brands = request.env['product.brand'].sudo().search([('active', '=', True)], order='name')
        data = [{'id': brand.id, 'name': brand.name} for brand in brands]
        return request.make_response(
            json.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )

    @http.route(['/shipment', '/shipment/request'], type='http', auth='public', website=True)
    def shipment_form(self, **kwargs):
        """عرض صفحة طلب الشحن"""
        # جلب الفئات للمنتجات
        categories = request.env['product.category'].sudo().search([])
        # جلب البراندات
        brands = request.env['product.brand'].sudo().search([('active', '=', True)])

        # جلب محافظات مصر فقط
        egypt = request.env.ref('base.eg')
        governorates = request.env['res.country.state'].sudo().search([
            ('country_id', '=', egypt.id)
        ], order='name')

        values = {
            'categories': categories,
            'brands': brands,
            'governorates': governorates,  # إضافة المحافظات
            'error': {},
            'success': kwargs.get('success', False)
        }

        # إضافة القيم المحفوظة من POST إذا كان هناك خطأ
        values.update(kwargs)

        return request.render('shipping_management_system.shipment_request_form', values)

    @http.route('/shipment/submit', type='http', auth='public', website=True, methods=['POST'])
    def shipment_submit(self, **post):
        """استلام بيانات الفورم المختصر وإنشاء الشحنة"""

        # ===== أدوات أمان =====
        def safe_float(val, default=0.0):
            try:
                return float(val) if val not in (None, '', False) else default
            except (ValueError, TypeError):
                return default

        def safe_int(val, default=0):
            try:
                return int(val) if val not in (None, '', False) else default
            except (ValueError, TypeError):
                return default

        def name_or_false(model, rec_id):
            if not rec_id:
                return False
            rec = request.env[model].sudo().browse(rec_id)
            return rec.name if rec.exists() else False

        # ===== تحقق من الحقول المطلوبة من التمبليت الجديد =====
        required_fields = [
            'sender_name', 'sender_phone', 'sender_address',
            'sender_governorate_new_id', 'sender_area_id', 'sender_city_district_id',
            'recipient_name', 'recipient_phone', 'recipient_address',
            'recipient_governorate_new_id', 'recipient_area_id', 'recipient_city_district_id',
        ]
        error, error_message = {}, []
        for field in required_fields:
            if not post.get(field):
                error[field] = 'missing'
                error_message.append(f"{field.replace('_', ' ').title()} is required")

        # المنتج (اختياري تماماً) — ننشئ سطر فقط إذا وصل category_id لأنه REQUIRED في الموديل
        category_id = safe_int(post.get('category_id'))
        product_subcategory_id = safe_int(post.get('product_subcategory_id'))
        product_brand_id = safe_int(post.get('product_brand_id'))

        single_product = {
            'name': post.get('product_name'),
            'quantity': post.get('quantity'),
            'weight': post.get('weight'),
            'value': post.get('product_value'),
            # الأبعاد
            'length': post.get('length'),
            'width': post.get('width'),
            'height': post.get('height'),
            # الخصائص
            'fragile': post.get('fragile'),
            'dangerous_goods': post.get('dangerous_goods'),
        }
        allow_create_line = bool(category_id)  # شرط إنشاء سطر المنتج

        if error:
            return request.render('shipping_management_system.shipment_request_form', {
                'error': error,
                'error_message': '\n'.join(error_message),
                'form': post,
            })

        # ===== IDs من موديل مصر =====
        sg_new = safe_int(post.get('sender_governorate_new_id'))
        sa_id = safe_int(post.get('sender_area_id'))
        sc_id = safe_int(post.get('sender_city_district_id'))

        rg_new = safe_int(post.get('recipient_governorate_new_id'))
        ra_id = safe_int(post.get('recipient_area_id'))
        rc_id = safe_int(post.get('recipient_city_district_id'))

        # أسماء لملء الحقول Char الإلزامية (sender_city / recipient_city)
        sender_area_name = name_or_false('egypt.governorate.area', sa_id)
        sender_city_name = name_or_false('egypt.governorate.city', sc_id)
        recipient_area_name = name_or_false('egypt.governorate.area', ra_id)
        recipient_city_name = name_or_false('egypt.governorate.city', rc_id)

        sender_city_text = (
            f"{sender_area_name}, {sender_city_name}" if sender_area_name and sender_city_name
            else (sender_city_name or sender_area_name or 'N/A')
        )
        recipient_city_text = (
            f"{recipient_area_name}, {recipient_city_name}" if recipient_area_name and recipient_city_name
            else (recipient_city_name or recipient_area_name or 'N/A')
        )

        # ===== إنشاء/جلب الشركاء =====
        sender_partner = self._create_or_get_partner(
            name=post.get('sender_name'),
            phone=post.get('sender_phone'),
            email=post.get('sender_email'),
            street=post.get('sender_address'),
        )
        recipient_partner = self._create_or_get_partner(
            name=post.get('recipient_name'),
            phone=post.get('recipient_phone'),
            email=post.get('recipient_email'),
            street=post.get('recipient_address'),
        )

        # دولة مصر (لو متاحة)
        try:
            egypt_id = request.env.ref('base.eg').id
        except Exception:
            egypt_id = False

        # ===== pickup_type: تحويل آمن للقيم =====
        pt = (post.get('pickup_type') or '').strip()
        # mapping للقيم القديمة للقيم الجديدة الصحيحة
        pickup_type_map = {
            'courier_pickup': 'customer',      # نستلم من المُرسل
            'customer_dropoff': 'sender',      # العميل يسلم بنفسه
        }
        pickup_type = pickup_type_map.get(pt, pt or 'customer')

        # ===== shipment_type: تحويل آمن للقيم القديمة =====
        st = (post.get('shipment_type') or '').strip()
        type_map = {'package': 'normal', 'other': 'normal'}
        shipment_type = type_map.get(st, st or 'normal')

        # ===== تكوين قيم الشحنة =====
        shipment_vals = {
            'sender_id': sender_partner.id,
            'recipient_id': recipient_partner.id,

            'sender_address': post.get('sender_address'),
            'sender_country_id': egypt_id or False,
            'recipient_address': post.get('recipient_address'),
            'recipient_country_id': egypt_id or False,

            # حقول Char الإلزامية في الموديل
            'sender_city': sender_city_text,
            'recipient_city': recipient_city_text,

            # تفضيلات وملاحظات
            'sender_preferred_pickup_time': post.get('sender_preferred_pickup_time', 'anytime'),
            'recipient_preferred_delivery_time': post.get('recipient_preferred_delivery_time', 'anytime'),
            'pickup_type': pickup_type,  # استخدام القيمة المحولة
            'sender_pickup_notes': post.get('sender_pickup_notes') or '',

            'sender_whatsapp': post.get('sender_whatsapp') or '',
            'sender_pickup_notes': post.get('sender_pickup_notes') or '',
            'recipient_name': post.get('recipient_name'),
            'recipient_phone': post.get('recipient_phone'),
            'recipient_mobile': post.get('recipient_mobile') or '',
            'recipient_email': post.get('recipient_email') or '',
            'recipient_whatsapp': post.get('recipient_whatsapp') or '',
            'recipient_delivery_notes': post.get('recipient_delivery_notes') or '',

            'payment_method': post.get('payment_method', 'prepaid'),
            'shipment_type': shipment_type,
            'package_count': safe_int(post.get('package_count', 1), 1),
            'notes': post.get('notes') or '',

            # روابط مصر الجديدة (IDs)
            'sender_governorate_new_id': sg_new or False,
            'sender_area_id': sa_id or False,
            'sender_city_district_id': sc_id or False,
            'recipient_governorate_new_id': rg_new or False,
            'recipient_area_id': ra_id or False,
            'recipient_city_district_id': rc_id or False,
            'source': 'website',
        }

        if post.get('payment_method') == 'cod':
            shipment_vals['cod_amount'] = safe_float(post.get('cod_amount'))

        # ===== سطر المنتج (اختياري تماماً) =====
        if allow_create_line:
            line_vals = {
                'category_id': category_id,
                'product_name': (single_product['name'] or 'Misc'),
                'quantity': safe_int(single_product['quantity'], 1),
                'weight': safe_float(single_product['weight'], 0.0),
                'product_value': safe_float(single_product['value'], 0.0),
                'length': safe_float(single_product.get('length'), 0.0),
                'width': safe_float(single_product.get('width'), 0.0),
                'height': safe_float(single_product.get('height'), 0.0),
                'fragile': bool(single_product.get('fragile')),
                'dangerous_goods': bool(single_product.get('dangerous_goods')),
            }

            # إضافة الحقول الاختيارية فقط لو موجودة في الموديل
            ShipmentLine = request.env['shipment.order.line']
            if 'product_subcategory_id' in ShipmentLine._fields and product_subcategory_id:
                line_vals['product_subcategory_id'] = product_subcategory_id
            if 'product_brand_id' in ShipmentLine._fields and product_brand_id:
                line_vals['product_brand_id'] = product_brand_id

            shipment_vals['shipment_line_ids'] = [(0, 0, line_vals)]

        # ===== إنشاء الشحنة =====
        shipment = request.env['shipment.order'].sudo().create(shipment_vals)

        # عرض صفحة النجاح (التمبلت بتاعك shipment_success)
        return request.render('shipping_management_system.shipment_success', {
            'shipment': shipment,
            'order_number': shipment.order_number or '',
            'tracking_number': shipment.tracking_number or '',  # لو عايز رقم التتبع لاحقاً
        })

    # مساعد: إنشاء/جلب شريك
    def _create_or_get_partner(self, name, phone=None, email=None, street=None):
        Partner = request.env['res.partner'].sudo()
        domain = []
        if phone:
            domain = ['|', ('phone', '=ilike', phone), ('mobile', '=ilike', phone)]
        if email:
            domain = (['|'] + domain + [('email', '=ilike', email)]) if domain else [('email', '=ilike', email)]
        partner = Partner.search(domain, limit=1) if domain else False
        if partner:
            vals_update = {}
            if name and not partner.name:
                vals_update['name'] = name
            if street and not partner.street:
                vals_update['street'] = street
            if vals_update:
                partner.write(vals_update)
            return partner
        return Partner.create({
            'name': name or 'Customer',
            'phone': phone or '',
            'mobile': phone or '',
            'email': email or '',
            'street': street or '',
            'type': 'contact',
        })

    def _create_or_get_partner(self, name, phone, email=None, street=None, street2=None, city=None, state_id=None,
                               country_id=None):
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
                'street2': street2 or False,
                'city': city or False,
                'state_id': state_id or False,
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
            if state_id and not partner.state_id:
                update_vals['state_id'] = state_id
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
    def get_shipping_rates(self, weight=None, from_governorate=None, to_governorate=None, **kwargs):
        """API endpoint لحساب أسعار الشحن بناء على المحافظات المصرية"""
        if not all([weight, from_governorate, to_governorate]):
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
                remote_governorates = ['أسوان', 'البحر الأحمر', 'الوادي الجديد', 'شمال سيناء', 'جنوب سيناء', 'مطروح']
                if from_governorate in remote_governorates or to_governorate in remote_governorates:
                    base_price *= 1.2  # زيادة 20% للمناطق البعيدة

                rates.append({
                    'company': service.company_id.name,
                    'service': service.name,
                    'delivery_time': service.delivery_time,
                    'price': base_price,
                    'from_governorate': from_governorate,
                    'to_governorate': to_governorate
                })

            # ترتيب حسب السعر
            rates.sort(key=lambda x: x['price'])

            return {'success': True, 'rates': rates}

        except Exception as e:
            return {'error': str(e)}
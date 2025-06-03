# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
import json
import re
import logging

_logger = logging.getLogger(__name__)


class SubscriptionRequestController(http.Controller):

    @http.route(['/subscription/request', '/subscription/new'], type='http', auth='public', website=True)
    def subscription_request_form(self, **kw):
        """عرض نموذج طلب الاشتراك"""
        # جلب البيانات المطلوبة للنموذج
        sports = request.env['club.sport'].sudo().search([('active', '=', True)])

        # جلب قائمة الدول
        countries = request.env['res.country'].sudo().search([], order='name')

        # رموز الدول
        country_codes = [
            ('+966', 'السعودية (+966)'),
            ('+971', 'الإمارات (+971)'),
            ('+965', 'الكويت (+965)'),
            ('+968', 'عمان (+968)'),
            ('+974', 'قطر (+974)'),
            ('+973', 'البحرين (+973)'),
            ('+20', 'مصر (+20)'),
            ('+962', 'الأردن (+962)'),
        ]

        values = {
            'sports': sports,
            'countries': countries,
            'country_codes': country_codes,
            'error': {},
            'success': kw.get('success', False),
        }

        # إذا كان هناك خطأ، احتفظ بالبيانات المدخلة
        if kw.get('error'):
            values.update(kw)

        return request.render('club.subscription_request_form', values)

    @http.route('/subscription/check_mobile', type='json', auth='public', methods=['POST'])
    def check_mobile_exists(self, country_code, mobile, **kw):
        """التحقق من وجود رقم الموبايل عبر Ajax"""
        if not mobile or not country_code:
            return {'exists': False}

        # تنظيف الرقم
        clean_mobile = re.sub(r'[^0-9]', '', mobile)
        if clean_mobile.startswith('0'):
            clean_mobile = clean_mobile[1:]

        # البحث بالرقم الكامل
        full_mobile = country_code + clean_mobile
        parent = request.env['club.parent'].sudo().search([
            ('full_mobile', '=', full_mobile),
            ('active', '=', True)
        ], limit=1)

        if parent:
            # جلب بيانات الأبناء مع الألعاب المشتركين فيها
            children_data = []
            for child in parent.player_ids:
                # جلب الاشتراكات النشطة
                active_subscriptions = request.env['player.subscription'].sudo().search([
                    ('player_id', '=', child.id),
                    ('state', '=', 'active')
                ])

                sports_names = active_subscriptions.mapped('sport_id.name')

                children_data.append({
                    'id': child.id,
                    'name': child.name,
                    'birth_date': child.birth_date.strftime('%Y-%m-%d') if child.birth_date else '',
                    'gender': '',  # إزالة مؤقتاً حتى نتأكد من الحقل الصحيح
                    'sports': ', '.join(sports_names) if sports_names else 'لا يوجد اشتراكات نشطة'
                })

            return {
                'exists': True,
                'parent_id': parent.id,
                'parent_name': parent.name,
                'parent_email': parent.email or '',
                'parent_address': parent.address or '',
                'children': children_data
            }

        return {'exists': False}

    @http.route('/subscription/get_sport_fee', type='json', auth='public', methods=['POST'])
    def get_sport_fee(self, sport_id, period, **kw):
        """جلب رسوم الرياضة حسب المدة"""
        try:
            sport = request.env['club.sport'].sudo().browse(int(sport_id))
            if sport.exists():
                monthly_fee = sport.monthly_fee
                months = int(period)

                # حساب الرسوم مع الخصومات
                if months == 1:
                    total = monthly_fee
                    discount = 0
                elif months == 3:
                    total = monthly_fee * 3 * 0.95
                    discount = 5
                elif months == 6:
                    total = monthly_fee * 6 * 0.9
                    discount = 10
                elif months == 12:
                    total = monthly_fee * 12 * 0.85
                    discount = 15
                else:
                    total = monthly_fee * months
                    discount = 0

                return {
                    'success': True,
                    'monthly_fee': monthly_fee,
                    'total': round(total, 2),
                    'discount': discount,
                    'currency': sport.currency_id.symbol or 'ر.س'
                }
        except:
            pass

        return {'success': False, 'total': 0}

    @http.route('/subscription/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def submit_subscription_request(self, **post):
        """معالجة وحفظ طلب الاشتراك"""
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Submit subscription request called with data: %s", post)

        try:
            # التحقق من البيانات الأساسية
            errors = {}

            # التحقق من بيانات ولي الأمر
            if not post.get('parent_exists'):
                required_parent_fields = ['parent_name', 'parent_mobile']
                for field in required_parent_fields:
                    if not post.get(field):
                        errors[field] = 'هذا الحقل مطلوب'

                # التحقق من صحة رقم الموبايل
                if post.get('parent_mobile') and not errors.get('parent_mobile'):
                    mobile = re.sub(r'[^0-9]', '', post.get('parent_mobile'))
                    if mobile.startswith('0'):
                        mobile = mobile[1:]

                    country_code = post.get('parent_country_code', '+966')

                    # التحقق من الطول حسب الدولة
                    if country_code == '+966' and not (len(mobile) == 9 and mobile.startswith('5')):
                        errors['parent_mobile'] = 'رقم الموبايل السعودي يجب أن يكون 9 أرقام ويبدأ بـ 5'

            # التحقق من وجود لاعب واحد على الأقل
            player_count = int(post.get('player_count', 0))
            if player_count == 0:
                errors['general'] = 'يجب إضافة لاعب واحد على الأقل'

            # التحقق من بيانات اللاعبين
            for i in range(1, player_count + 1):
                if not post.get(f'player_exists_{i}'):
                    # لاعب جديد
                    if not post.get(f'player_name_{i}'):
                        errors[f'player_name_{i}'] = 'اسم اللاعب مطلوب'
                    if not post.get(f'player_birth_date_{i}'):
                        errors[f'player_birth_date_{i}'] = 'تاريخ الميلاد مطلوب'
                    if not post.get(f'player_gender_{i}'):
                        errors[f'player_gender_{i}'] = 'الجنس مطلوب'

                if not post.get(f'sport_id_{i}'):
                    errors[f'sport_id_{i}'] = 'يجب اختيار اللعبة'
                if not post.get(f'subscription_period_{i}'):
                    errors[f'subscription_period_{i}'] = 'يجب اختيار مدة الاشتراك'

            # إذا كان هناك أخطاء، أعد عرض النموذج مع الأخطاء
            if errors:
                values = post.copy()
                values['error'] = errors
                values['sports'] = request.env['club.sport'].sudo().search([('active', '=', True)])
                values['country_codes'] = [
                    ('+966', 'السعودية (+966)'),
                    ('+971', 'الإمارات (+971)'),
                    ('+965', 'الكويت (+965)'),
                    ('+968', 'عمان (+968)'),
                    ('+974', 'قطر (+974)'),
                    ('+973', 'البحرين (+973)'),
                    ('+20', 'مصر (+20)'),
                    ('+962', 'الأردن (+962)'),
                ]
                return request.render('club.subscription_request_form', values)

            # إنشاء طلب الاشتراك
            request_vals = {
                'request_type': post.get('request_type', 'new'),
                'parent_exists': post.get('parent_exists') == 'true',
            }

            # بيانات ولي الأمر
            if post.get('parent_exists') == 'true':
                request_vals['parent_id'] = int(post.get('parent_id'))
            else:
                mobile = re.sub(r'[^0-9]', '', post.get('parent_mobile'))
                if mobile.startswith('0'):
                    mobile = mobile[1:]

                request_vals.update({
                    'new_parent_name': post.get('parent_name'),
                    'new_parent_country_code': post.get('parent_country_code', '+966'),
                    'new_parent_mobile': mobile,
                    'new_parent_email': post.get('parent_email'),
                    'new_parent_address': post.get('parent_address'),
                })

            # إنشاء الطلب
            subscription_request = request.env['subscription.request'].sudo().create(request_vals)

            # إضافة تفاصيل اللاعبين
            for i in range(1, player_count + 1):
                line_vals = {
                    'request_id': subscription_request.id,
                    'player_exists': post.get(f'player_exists_{i}') == 'true',
                    'sport_id': int(post.get(f'sport_id_{i}')),
                    'subscription_period': post.get(f'subscription_period_{i}'),
                    'note': post.get(f'player_note_{i}', ''),
                }

                if post.get(f'player_exists_{i}') == 'true':
                    line_vals['player_id'] = int(post.get(f'player_id_{i}'))
                else:
                    line_vals.update({
                        'new_player_name': post.get(f'player_name_{i}'),
                        'new_player_birth_date': post.get(f'player_birth_date_{i}'),
                        'new_player_gender': post.get(f'player_gender_{i}'),
                        'new_player_medical_conditions': post.get(f'player_medical_{i}', ''),
                        'new_player_nationality_id': int(post.get(f'player_nationality_{i}')) if post.get(
                            f'player_nationality_{i}') else False,
                        'new_player_id_number': post.get(f'player_id_number_{i}', ''),
                    })

                request.env['subscription.request.line'].sudo().create(line_vals)

            # إرسال الطلب مباشرة
            subscription_request.action_send()

            # إعادة التوجيه لصفحة النجاح
            return request.redirect('/subscription/success?request_id=%s' % subscription_request.id)

        except Exception as e:
            # في حالة حدوث خطأ، أعد عرض النموذج مع رسالة خطأ عامة
            _logger.error("Error in submit_subscription_request: %s", str(e), exc_info=True)

            values = post.copy()
            values['error'] = {'general': f'حدث خطأ أثناء معالجة الطلب: {str(e)}'}
            values['sports'] = request.env['club.sport'].sudo().search([('active', '=', True)])
            values['countries'] = request.env['res.country'].sudo().search([], order='name')
            values['country_codes'] = [
                ('+966', 'السعودية (+966)'),
                ('+971', 'الإمارات (+971)'),
                ('+965', 'الكويت (+965)'),
                ('+968', 'عمان (+968)'),
                ('+974', 'قطر (+974)'),
                ('+973', 'البحرين (+973)'),
                ('+20', 'مصر (+20)'),
                ('+962', 'الأردن (+962)'),
            ]
            return request.render('club.subscription_request_form', values)

    @http.route('/subscription/success', type='http', auth='public', website=True)
    def subscription_success(self, request_id=None, **kw):
        """صفحة نجاح إرسال الطلب"""
        values = {}

        if request_id:
            subscription_request = request.env['subscription.request'].sudo().browse(int(request_id))
            if subscription_request.exists():
                values['subscription_request'] = subscription_request

        return request.render('club.subscription_success', values)
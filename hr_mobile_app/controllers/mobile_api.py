# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
import werkzeug.exceptions
import json
import logging

_logger = logging.getLogger(__name__)


class MobileAPI(http.Controller):
    """واجهة برمجة تطبيقات للتطبيق المحمول"""

    @http.route('/api/mobile/version', type='http', auth='none', methods=['GET'], csrf=False)
    def get_api_version(self):
        """الحصول على إصدار API"""
        _logger.info("====== API Version Request ======")
        return json.dumps({
            'jsonrpc': '2.0',
            'result': {
                'version': '1.0',
                'name': 'Odoo Mobile API',
            }
        })

    @http.route('/api/mobile/simple_login', type='http', auth='none', methods=['POST'], csrf=False)
    def simple_login(self, **kw):
        """تسجيل دخول مبسط للتطبيق المحمول"""
        try:
            # استخراج البيانات من الطلب
            _logger.info("====== بداية طلب تسجيل الدخول المبسط ======")

            # التحقق من البيانات المستلمة
            if not request.httprequest.data:
                _logger.error("لم يتم استلام بيانات في الطلب")
                return json.dumps({
                    'success': False,
                    'error': 'لم يتم استلام بيانات في الطلب'
                })

            # تحليل بيانات الطلب
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
                _logger.info("البيانات المستلمة: %s", data)
            except Exception as e:
                _logger.error("خطأ في تحليل بيانات JSON: %s", str(e))
                return json.dumps({
                    'success': False,
                    'error': f'خطأ في تحليل بيانات JSON: {str(e)}'
                })

            # استخراج معلومات تسجيل الدخول
            params = data.get('params', {})
            username = params.get('username')
            password = params.get('password')
            db = params.get('db', request.db)

            if not username or not password:
                _logger.error("معلومات تسجيل الدخول غير مكتملة")
                return json.dumps({
                    'success': False,
                    'error': 'معلومات تسجيل الدخول غير مكتملة'
                })

            _logger.info("محاولة تسجيل دخول للمستخدم: %s في قاعدة البيانات: %s", username, db)

            # تسجيل دخول المستخدم المشترك
            try:
                uid = request.session.authenticate(db, 'mobile_app_service', 'Secure_P@ssword123')
                if not uid:
                    _logger.error("فشل تسجيل دخول المستخدم المشترك")
                    return json.dumps({
                        'success': False,
                        'error': 'فشل تسجيل دخول المستخدم المشترك'
                    })
                _logger.info("تم تسجيل دخول المستخدم المشترك بنجاح، معرف المستخدم: %s", uid)
            except Exception as e:
                _logger.error("خطأ في تسجيل دخول المستخدم المشترك: %s", str(e))
                return json.dumps({
                    'success': False,
                    'error': f'خطأ في تسجيل دخول المستخدم المشترك: {str(e)}'
                })

            # البحث عن الموظف بطريقتين (دعم أكبر)
            # 1. بحث مباشر
            employee = request.env['hr.employee'].sudo().search([
                ('mobile_username', '=', username),
                ('allow_mobile_access', '=', True),
            ], limit=1)

            # 2. إذا لم يتم العثور، جرب بحث غير حساس لحالة الأحرف
            if not employee:
                employee = request.env['hr.employee'].sudo().search([
                    ('mobile_username', 'ilike', username),
                    ('allow_mobile_access', '=', True),
                ], limit=1)

            # 3. إذا لم يتم العثور بعد، جرب البحث بالاسم
            if not employee:
                employee = request.env['hr.employee'].sudo().search([
                    ('name', 'ilike', username),
                    ('allow_mobile_access', '=', True),
                ], limit=1)

            _logger.info("نتيجة البحث عن الموظف: %s", "تم العثور" if employee else "لم يتم العثور")

            if not employee:
                # للتجربة فقط: إنشاء موظف تجريبي إذا لم يتم العثور
                try:
                    # التحقق مما إذا كان الموظف الاختباري موجوداً بالفعل
                    test_employee = request.env['hr.employee'].sudo().search([
                        ('name', '=', 'موظف تجريبي')
                    ], limit=1)

                    if test_employee:
                        _logger.info("استخدام موظف تجريبي موجود بالفعل")
                        employee = test_employee
                    else:
                        _logger.info("إنشاء موظف تجريبي للاختبار")
                        # إنشاء قسم تجريبي إذا لم يوجد
                        test_dept = request.env['hr.department'].sudo().search([
                            ('name', '=', 'قسم تجريبي')
                        ], limit=1)

                        if not test_dept:
                            test_dept = request.env['hr.department'].sudo().create({
                                'name': 'قسم تجريبي'
                            })

                        # إنشاء موظف تجريبي
                        employee = request.env['hr.employee'].sudo().create({
                            'name': 'موظف تجريبي',
                            'job_title': 'مسمى وظيفي تجريبي',
                            'department_id': test_dept.id,
                            'mobile_username': username,
                            'allow_mobile_access': True
                        })
                        _logger.info("تم إنشاء موظف تجريبي بنجاح: %s", employee.id)
                except Exception as e:
                    _logger.error("خطأ في إنشاء موظف تجريبي: %s", str(e))
                    # استمر على أي حال

            if not employee:
                _logger.warning("لم يتم العثور على موظف بهذا الاسم: %s", username)
                return json.dumps({
                    'success': False,
                    'error': 'لم يتم العثور على موظف بهذا الاسم'
                })

            # للاختبار فقط: السماح بالوصول دائمًا بغض النظر عن كلمة المرور
            # في البيئة الإنتاجية، يجب تعديل هذا ليستخدم تشفير حقيقي للـ PIN
            _logger.info("التحقق من كلمة المرور (مبسط للاختبار)")
            password_check = (password == '123456' or True)  # دائماً صح للاختبار

            if password_check:
                _logger.info("تم التحقق من كلمة المرور بنجاح")

                # جلب بيانات القسم إذا كان متاحاً
                department_name = employee.department_id.name if employee.department_id else 'غير محدد'

                # تحضير بيانات الموظف للإرجاع
                employee_data = {
                    'id': employee.id,
                    'name': employee.name,
                    'job_title': employee.job_title or 'غير محدد',
                    'department': department_name,
                    'work_email': employee.work_email or '',
                    'work_phone': employee.work_phone or '',
                    'mobile_phone': employee.mobile_phone or '',
                }

                _logger.info("إرجاع بيانات الموظف: %s", employee_data)
                return json.dumps({
                    'success': True,
                    'employee': employee_data
                })
            else:
                _logger.warning("كلمة المرور غير صحيحة")
                return json.dumps({
                    'success': False,
                    'error': 'كلمة المرور غير صحيحة'
                })

        except Exception as e:
            _logger.error("خطأ عام في تسجيل الدخول المبسط: %s", str(e))
            return json.dumps({
                'success': False,
                'error': str(e)
            })

    @http.route('/api/mobile/authenticate', type='json', auth='user', csrf=False)
    def authenticate_employee(self, username=None, pin=None):
        """المصادقة على الموظف عبر اسم المستخدم و PIN"""
        _logger.info("====== طلب مصادقة الموظف ======")
        if not username or not pin:
            return {'success': False, 'error': _('معلومات غير كافية')}

        try:
            # العثور على الموظف بواسطة اسم المستخدم
            employee = request.env['hr.employee'].sudo().search([
                ('mobile_username', '=', username),
                ('allow_mobile_access', '=', True),
            ], limit=1)

            # التحقق من وجود الموظف
            if not employee:
                _logger.warning("المستخدم غير موجود أو غير مفعل: %s", username)
                return {'success': False, 'error': _('المستخدم غير موجود أو غير مفعل')}

            # للاختبار: قبول أي PIN
            verification_result = True
            _logger.info("تم التحقق من PIN (مبسط للاختبار)")

            # إرجاع معلومات الموظف
            return {
                'success': True,
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'job_title': employee.job_title or False,
                    'department': employee.department_id.name if employee.department_id else False,
                    'work_email': employee.work_email or False,
                    'work_phone': employee.work_phone or False,
                    'mobile_phone': employee.mobile_phone or False,
                }
            }

        except Exception as e:
            _logger.error("خطأ في المصادقة: %s", str(e))
            return {'success': False, 'error': _('حدث خطأ في المصادقة')}

    @http.route('/api/mobile/employee/info', type='json', auth='user', csrf=False)
    def get_employee_info(self, employee_id=None):
        """الحصول على معلومات الموظف بناءً على المعرف"""
        _logger.info("====== طلب معلومات الموظف ======")
        if not employee_id:
            return {'success': False, 'error': _('معلومات غير كافية')}

        try:
            # العثور على الموظف بواسطة المعرف
            employee = request.env['hr.employee'].sudo().browse(int(employee_id))

            # التحقق من وجود الموظف
            if not employee.exists():
                _logger.warning("الموظف غير موجود: %s", employee_id)
                return {'success': False, 'error': _('الموظف غير موجود')}

            # للتجربة: تجاهل فحص allow_mobile_access
            # if not employee.allow_mobile_access:
            #     return {'success': False, 'error': _('الموظف غير مصرح له')}

            # إرجاع معلومات الموظف
            return {
                'success': True,
                'employee': {
                    'id': employee.id,
                    'name': employee.name,
                    'job_title': employee.job_title or False,
                    'department': employee.department_id.name if employee.department_id else False,
                    'company': employee.company_id.name if employee.company_id else False,
                    'work_email': employee.work_email or False,
                    'work_phone': employee.work_phone or False,
                    'mobile_phone': employee.mobile_phone or False,
                    'work_location': employee.work_location or False,
                }
            }

        except Exception as e:
            _logger.error("خطأ في استرجاع معلومات الموظف: %s", str(e))
            return {'success': False, 'error': _('حدث خطأ في استرجاع المعلومات')}

    # في ملف mobile_api.py
    @http.route('/api/mobile/test', type='http', auth='none', methods=['GET'], csrf=False)
    def test_api(self):
        """اختبار بسيط لواجهة API"""
        _logger.info("====== طلب اختبار API ======")
        return json.dumps({
            'status': 'success',
            'message': 'API تعمل بشكل صحيح',
            'version': '1.0',
            'timestamp': fields.Datetime.now(),
        })

    @http.route('/api/mobile/leave/types', type='json', auth='user', csrf=False)
    def get_leave_types(self):
        """الحصول على أنواع الإجازات المتاحة"""
        try:
            _logger.info("====== طلب أنواع الإجازات ======")

            # جلب أنواع الإجازات النشطة
            leave_types = request.env['hr.leave.type'].sudo().search([
                ('active', '=', True),
                ('requires_allocation', '=', 'no')  # الإجازات التي لا تحتاج تخصيص
            ])

            types_data = []
            for leave_type in leave_types:
                types_data.append({
                    'id': leave_type.id,
                    'name': leave_type.name,
                    'max_days': leave_type.max_leaves or 30,
                    'color': leave_type.color_name or '#2196F3',
                    'requires_approval': leave_type.leave_validation_type != 'no_validation',
                    'description': leave_type.name,
                })

            return {
                'success': True,
                'leave_types': types_data
            }

        except Exception as e:
            _logger.error("خطأ في جلب أنواع الإجازات: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/leave/requests', type='json', auth='user', csrf=False)
    def get_leave_requests(self, employee_id=None, limit=50):
        """الحصول على طلبات الإجازة للموظف"""
        try:
            _logger.info("====== طلب جلب طلبات الإجازة للموظف %s ======", employee_id)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # جلب طلبات الإجازة للموظف
            domain = [('employee_id', '=', int(employee_id))]

            leave_requests = request.env['hr.leave'].sudo().search(
                domain,
                order='create_date desc',
                limit=int(limit)
            )

            requests_data = []
            for leave_request in leave_requests:
                # تحديد حالة الطلب
                state_mapping = {
                    'draft': {'text': 'مسودة', 'icon': '📝', 'color': '#9E9E9E'},
                    'confirm': {'text': 'قيد المراجعة', 'icon': '⏳', 'color': '#FFA500'},
                    'validate1': {'text': 'مراجعة أولى', 'icon': '👁️', 'color': '#2196F3'},
                    'validate': {'text': 'مقبولة', 'icon': '✅', 'color': '#4CAF50'},
                    'refuse': {'text': 'مرفوضة', 'icon': '❌', 'color': '#F44336'},
                    'cancel': {'text': 'ملغاة', 'icon': '🚫', 'color': '#9E9E9E'},
                }

                state_info = state_mapping.get(leave_request.state, state_mapping['draft'])

                # معلومات المعتمد
                approver_name = None
                approval_date = None
                if leave_request.first_approver_id:
                    approver_name = leave_request.first_approver_id.name
                if leave_request.date_approve:
                    approval_date = leave_request.date_approve.isoformat()

                requests_data.append({
                    'id': leave_request.id,
                    'employee_id': leave_request.employee_id.id,
                    'employee_name': leave_request.employee_id.name,
                    'leave_type_id': leave_request.holiday_status_id.id,
                    'leave_type_name': leave_request.holiday_status_id.name,
                    'date_from': leave_request.date_from.isoformat() if leave_request.date_from else None,
                    'date_to': leave_request.date_to.isoformat() if leave_request.date_to else None,
                    'number_of_days': leave_request.number_of_days,
                    'reason': leave_request.name or '',
                    'state': leave_request.state,
                    'state_text': state_info['text'],
                    'state_icon': state_info['icon'],
                    'state_color': state_info['color'],
                    'created_date': leave_request.create_date.isoformat() if leave_request.create_date else None,
                    'approver_name': approver_name,
                    'approval_date': approval_date,
                    'manager_comment': leave_request.notes or '',
                })

            return {
                'success': True,
                'leave_requests': requests_data,
                'total_count': len(requests_data)
            }

        except Exception as e:
            _logger.error("خطأ في جلب طلبات الإجازة: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/leave/create', type='json', auth='user', csrf=False)
    def create_leave_request(self, employee_id=None, holiday_status_id=None,
                             date_from=None, date_to=None, name=None):
        """إنشاء طلب إجازة جديد"""
        try:
            _logger.info("====== إنشاء طلب إجازة جديد ======")
            _logger.info("البيانات المستلمة: employee_id=%s, holiday_status_id=%s, date_from=%s, date_to=%s",
                         employee_id, holiday_status_id, date_from, date_to)

            # التحقق من البيانات المطلوبة
            if not all([employee_id, holiday_status_id, date_from, date_to]):
                return {
                    'success': False,
                    'error': 'جميع البيانات مطلوبة (معرف الموظف، نوع الإجازة، تاريخ البداية، تاريخ النهاية)'
                }

            # التحقق من وجود الموظف
            employee = request.env['hr.employee'].sudo().browse(int(employee_id))
            if not employee.exists():
                return {'success': False, 'error': 'الموظف غير موجود'}

            # التحقق من وجود نوع الإجازة
            leave_type = request.env['hr.leave.type'].sudo().browse(int(holiday_status_id))
            if not leave_type.exists():
                return {'success': False, 'error': 'نوع الإجازة غير موجود'}

            # تحويل التواريخ
            try:
                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except ValueError as e:
                return {'success': False, 'error': f'تنسيق التاريخ غير صحيح: {str(e)}'}

            # التحقق من صحة التواريخ
            if date_from_dt >= date_to_dt:
                return {'success': False, 'error': 'تاريخ البداية يجب أن يكون قبل تاريخ النهاية'}

            # التحقق من عدم التداخل مع طلبات موجودة
            overlapping_requests = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', int(employee_id)),
                ('state', 'in', ['confirm', 'validate1', 'validate']),
                '|',
                '&', ('date_from', '<=', date_from_dt), ('date_to', '>=', date_from_dt),
                '&', ('date_from', '<=', date_to_dt), ('date_to', '>=', date_to_dt),
            ])

            if overlapping_requests:
                return {
                    'success': False,
                    'error': 'يتداخل مع طلب إجازة آخر موجود بالفعل'
                }

            # إنشاء طلب الإجازة
            leave_vals = {
                'employee_id': int(employee_id),
                'holiday_status_id': int(holiday_status_id),
                'date_from': date_from_dt,
                'date_to': date_to_dt,
                'name': name or f'طلب إجازة - {leave_type.name}',
                'state': 'draft',
            }

            new_leave = request.env['hr.leave'].sudo().create(leave_vals)

            # إرسال للمراجعة تلقائياً إذا كان مطلوباً
            if leave_type.leave_validation_type != 'no_validation':
                try:
                    new_leave.action_confirm()
                    _logger.info("تم إرسال طلب الإجازة للمراجعة تلقائياً")
                except Exception as e:
                    _logger.warning("لم يتم إرسال الطلب للمراجعة تلقائياً: %s", str(e))

            return {
                'success': True,
                'leave_request_id': new_leave.id,
                'message': 'تم إنشاء طلب الإجازة بنجاح'
            }

        except Exception as e:
            _logger.error("خطأ في إنشاء طلب الإجازة: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/leave/cancel', type='json', auth='user', csrf=False)
    def cancel_leave_request(self, request_id=None):
        """إلغاء طلب إجازة"""
        try:
            _logger.info("====== إلغاء طلب الإجازة %s ======", request_id)

            if not request_id:
                return {'success': False, 'error': 'معرف طلب الإجازة مطلوب'}

            # البحث عن طلب الإجازة
            leave_request = request.env['hr.leave'].sudo().browse(int(request_id))

            if not leave_request.exists():
                return {'success': False, 'error': 'طلب الإجازة غير موجود'}

            # التحقق من إمكانية الإلغاء
            if leave_request.state not in ['draft', 'confirm']:
                return {
                    'success': False,
                    'error': 'لا يمكن إلغاء هذا الطلب في حالته الحالية'
                }

            # إلغاء الطلب
            leave_request.action_refuse()
            leave_request.write({'state': 'cancel'})

            return {
                'success': True,
                'message': 'تم إلغاء طلب الإجازة بنجاح'
            }

        except Exception as e:
            _logger.error("خطأ في إلغاء طلب الإجازة: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/leave/availability', type='json', auth='user', csrf=False)
    def check_leave_availability(self, employee_id=None, holiday_status_id=None,
                                 date_from=None, date_to=None):
        """التحقق من توفر الإجازة"""
        try:
            _logger.info("====== فحص توفر الإجازة ======")

            if not all([employee_id, holiday_status_id, date_from, date_to]):
                return {'success': False, 'error': 'جميع البيانات مطلوبة'}

            # تحويل التواريخ
            try:
                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            except ValueError:
                return {'success': False, 'error': 'تنسيق التاريخ غير صحيح'}

            # حساب عدد الأيام
            number_of_days = (date_to_dt - date_from_dt).days + 1

            # التحقق من التداخل
            overlapping_requests = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', int(employee_id)),
                ('state', 'in', ['confirm', 'validate1', 'validate']),
                '|',
                '&', ('date_from', '<=', date_from_dt), ('date_to', '>=', date_from_dt),
                '&', ('date_from', '<=', date_to_dt), ('date_to', '>=', date_to_dt),
            ])

            if overlapping_requests:
                return {
                    'available': False,
                    'message': 'يتداخل مع طلب إجازة آخر موجود'
                }

            # فحص الرصيد المتاح (إذا كان نوع الإجازة يتطلب تخصيص)
            leave_type = request.env['hr.leave.type'].sudo().browse(int(holiday_status_id))

            if leave_type.requires_allocation == 'yes':
                # فحص التخصيص المتاح
                allocation = request.env['hr.leave.allocation'].sudo().search([
                    ('employee_id', '=', int(employee_id)),
                    ('holiday_status_id', '=', int(holiday_status_id)),
                    ('state', '=', 'validate'),
                ], limit=1)

                if not allocation:
                    return {
                        'available': False,
                        'message': 'لا يوجد رصيد متاح لهذا النوع من الإجازات'
                    }

                remaining_days = allocation.number_of_days - allocation.leaves_taken

                if remaining_days < number_of_days:
                    return {
                        'available': False,
                        'message': f'الرصيد المتاح ({remaining_days} يوم) أقل من المطلوب ({number_of_days} يوم)'
                    }

            return {
                'available': True,
                'message': 'الإجازة متاحة',
                'requested_days': number_of_days
            }

        except Exception as e:
            _logger.error("خطأ في فحص توفر الإجازة: %s", str(e))
            return {
                'available': False,
                'message': str(e)
            }

    @http.route('/api/mobile/leave/stats', type='json', auth='user', csrf=False)
    def get_leave_stats(self, employee_id=None):
        """الحصول على إحصائيات الإجازات للموظف"""
        try:
            _logger.info("====== طلب إحصائيات الإجازات للموظف %s ======", employee_id)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # جلب جميع طلبات الإجازة للموظف
            all_requests = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', int(employee_id))
            ])

            # تصنيف الطلبات
            pending_requests = all_requests.filtered(lambda r: r.state in ['draft', 'confirm'])
            approved_requests = all_requests.filtered(lambda r: r.state == 'validate')
            rejected_requests = all_requests.filtered(lambda r: r.state == 'refuse')
            cancelled_requests = all_requests.filtered(lambda r: r.state == 'cancel')

            # حساب الأيام المستخدمة
            total_days_used = sum(approved_requests.mapped('number_of_days'))

            # حساب الأيام المتبقية (افتراضي 30 يوم سنوياً)
            total_days_allowed = 30
            total_days_remaining = max(0, total_days_allowed - total_days_used)

            # إحصائيات حسب النوع
            leaves_by_type = {}
            days_by_type = {}

            for request in all_requests:
                type_name = request.holiday_status_id.name
                leaves_by_type[type_name] = leaves_by_type.get(type_name, 0) + 1

                if request.state == 'validate':
                    days_by_type[type_name] = days_by_type.get(type_name, 0) + request.number_of_days

            return {
                'success': True,
                'stats': {
                    'total_requests': len(all_requests),
                    'pending_requests': len(pending_requests),
                    'approved_requests': len(approved_requests),
                    'rejected_requests': len(rejected_requests),
                    'cancelled_requests': len(cancelled_requests),
                    'total_days_used': total_days_used,
                    'total_days_remaining': total_days_remaining,
                    'total_days_allowed': total_days_allowed,
                    'leaves_by_type': leaves_by_type,
                    'days_by_type': days_by_type,
                    'approval_rate': (len(approved_requests) / len(all_requests) * 100) if all_requests else 0,
                    'usage_rate': (total_days_used / total_days_allowed * 100) if total_days_allowed > 0 else 0,
                }
            }

        except Exception as e:
            _logger.error("خطأ في جلب إحصائيات الإجازات: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/leave/request/<int:request_id>', type='json', auth='user', csrf=False)
    def get_leave_request_details(self, request_id):
        """الحصول على تفاصيل طلب إجازة محدد"""
        try:
            _logger.info("====== طلب تفاصيل طلب الإجازة %s ======", request_id)

            leave_request = request.env['hr.leave'].sudo().browse(request_id)

            if not leave_request.exists():
                return {'success': False, 'error': 'طلب الإجازة غير موجود'}

            # تحديد حالة الطلب
            state_mapping = {
                'draft': {'text': 'مسودة', 'icon': '📝', 'color': '#9E9E9E'},
                'confirm': {'text': 'قيد المراجعة', 'icon': '⏳', 'color': '#FFA500'},
                'validate1': {'text': 'مراجعة أولى', 'icon': '👁️', 'color': '#2196F3'},
                'validate': {'text': 'مقبولة', 'icon': '✅', 'color': '#4CAF50'},
                'refuse': {'text': 'مرفوضة', 'icon': '❌', 'color': '#F44336'},
                'cancel': {'text': 'ملغاة', 'icon': '🚫', 'color': '#9E9E9E'},
            }

            state_info = state_mapping.get(leave_request.state, state_mapping['draft'])

            request_details = {
                'id': leave_request.id,
                'employee_id': leave_request.employee_id.id,
                'employee_name': leave_request.employee_id.name,
                'leave_type_id': leave_request.holiday_status_id.id,
                'leave_type_name': leave_request.holiday_status_id.name,
                'date_from': leave_request.date_from.isoformat() if leave_request.date_from else None,
                'date_to': leave_request.date_to.isoformat() if leave_request.date_to else None,
                'number_of_days': leave_request.number_of_days,
                'reason': leave_request.name or '',
                'state': leave_request.state,
                'state_text': state_info['text'],
                'state_icon': state_info['icon'],
                'state_color': state_info['color'],
                'created_date': leave_request.create_date.isoformat() if leave_request.create_date else None,
                'manager_comment': leave_request.notes or '',
                'approver_name': leave_request.first_approver_id.name if leave_request.first_approver_id else None,
                'approval_date': leave_request.date_approve.isoformat() if leave_request.date_approve else None,
                'can_cancel': leave_request.state in ['draft', 'confirm'],
                'can_edit': leave_request.state == 'draft',
            }

            return {
                'success': True,
                'leave_request': request_details
            }

        except Exception as e:
            _logger.error("خطأ في جلب تفاصيل طلب الإجازة: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }
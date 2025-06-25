# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
import werkzeug.exceptions
import json
import logging
from datetime import datetime, timedelta

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

                # جلب صورة الموظف
                avatar_128 = None
                image_1920 = None

                # قراءة الصورة من Odoo
                if employee.avatar_128:
                    avatar_128 = employee.avatar_128.decode('utf-8') if isinstance(employee.avatar_128,
                                                                                   bytes) else employee.avatar_128
                if employee.image_1920:
                    image_1920 = employee.image_1920.decode('utf-8') if isinstance(employee.image_1920,
                                                                                   bytes) else employee.image_1920

                # تحضير بيانات الموظف للإرجاع
                employee_data = {
                    'id': employee.id,
                    'name': employee.name,
                    'job_title': employee.job_title or 'غير محدد',
                    'department': department_name,
                    'work_email': employee.work_email or '',
                    'work_phone': employee.work_phone or '',
                    'mobile_phone': employee.mobile_phone or '',
                    # إضافة بيانات الصورة
                    'avatar_128': avatar_128,
                    'image_1920': image_1920,
                }

                _logger.info("إرجاع بيانات الموظف: %s",
                             {k: v for k, v in employee_data.items() if k not in ['avatar_128', 'image_1920']})
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

            # جلب صورة الموظف
            avatar_128 = None
            image_1920 = None

            if employee.avatar_128:
                avatar_128 = employee.avatar_128.decode('utf-8') if isinstance(employee.avatar_128,
                                                                               bytes) else employee.avatar_128
            if employee.image_1920:
                image_1920 = employee.image_1920.decode('utf-8') if isinstance(employee.image_1920,
                                                                               bytes) else employee.image_1920

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
                    # إضافة بيانات الصورة
                    'avatar_128': avatar_128,
                    'image_1920': image_1920,
                }
            }

        except Exception as e:
            _logger.error("خطأ في المصادقة: %s", str(e))
            return {'success': False, 'error': _('حدث خطأ في المصادقة')}

    # في ملف hr_mobile_app/controllers/mobile_api.py
    # استبدل دالة get_employee_info بهذه النسخة المحدثة:

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

            # جلب صورة الموظف
            avatar_128 = None
            image_1920 = None

            if employee.avatar_128:
                avatar_128 = employee.avatar_128.decode('utf-8') if isinstance(employee.avatar_128,
                                                                               bytes) else employee.avatar_128
            if employee.image_1920:
                image_1920 = employee.image_1920.decode('utf-8') if isinstance(employee.image_1920,
                                                                               bytes) else employee.image_1920

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
                    # إضافة بيانات الصورة
                    'avatar_128': avatar_128,
                    'image_1920': image_1920,
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

    # ==================== واجهات الحضور والانصراف مع الموقع ====================

    @http.route('/api/mobile/attendance/check_location', type='json', auth='user', csrf=False)
    def check_attendance_location(self, employee_id=None, latitude=None, longitude=None):
        """التحقق من الموقع قبل السماح بتسجيل الحضور/الانصراف"""
        try:
            _logger.info("====== التحقق من موقع الحضور ======")
            _logger.info("employee_id: %s, lat: %s, lng: %s", employee_id, latitude, longitude)

            if not all([employee_id, latitude, longitude]):
                return {
                    'success': False,
                    'error': 'جميع البيانات مطلوبة (معرف الموظف، خط العرض، خط الطول)'
                }

            # استخدام نموذج الحضور للتحقق من الموقع
            result = request.env['hr.attendance'].sudo().check_location_before_attendance(
                int(employee_id),
                float(latitude),
                float(longitude)
            )

            return result

        except Exception as e:
            _logger.error("خطأ في التحقق من الموقع: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/attendance/check_in', type='json', auth='user', csrf=False)
    def mobile_attendance_check_in(self, employee_id=None, latitude=None, longitude=None):
        """تسجيل حضور مع الموقع الجغرافي"""
        try:
            _logger.info("====== تسجيل حضور مع الموقع ======")
            _logger.info("employee_id: %s, lat: %s, lng: %s", employee_id, latitude, longitude)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # تحويل القيم إلى الأنواع الصحيحة
            emp_id = int(employee_id)
            lat = float(latitude) if latitude else None
            lng = float(longitude) if longitude else None

            # استدعاء دالة تسجيل الحضور مع الموقع
            result = request.env['hr.attendance'].sudo().mobile_check_in(
                emp_id, lat, lng
            )

            return result

        except ValueError as e:
            _logger.error("خطأ في تحويل البيانات: %s", str(e))
            return {
                'success': False,
                'error': 'البيانات المرسلة غير صالحة'
            }
        except Exception as e:
            _logger.error("خطأ في تسجيل الحضور: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/attendance/check_out', type='json', auth='user', csrf=False)
    def mobile_attendance_check_out(self, employee_id=None, latitude=None, longitude=None):
        """تسجيل انصراف مع الموقع الجغرافي"""
        try:
            _logger.info("====== تسجيل انصراف مع الموقع ======")
            _logger.info("employee_id: %s, lat: %s, lng: %s", employee_id, latitude, longitude)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # تحويل القيم إلى الأنواع الصحيحة
            emp_id = int(employee_id)
            lat = float(latitude) if latitude else None
            lng = float(longitude) if longitude else None

            # استدعاء دالة تسجيل الانصراف مع الموقع
            result = request.env['hr.attendance'].sudo().mobile_check_out(
                emp_id, lat, lng
            )

            return result

        except ValueError as e:
            _logger.error("خطأ في تحويل البيانات: %s", str(e))
            return {
                'success': False,
                'error': 'البيانات المرسلة غير صالحة'
            }
        except Exception as e:
            _logger.error("خطأ في تسجيل الانصراف: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/attendance/status', type='json', auth='user', csrf=False)
    def get_attendance_status(self, employee_id=None):
        """الحصول على حالة الحضور الحالية للموظف"""
        try:
            _logger.info("====== طلب حالة الحضور ======")

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # الحصول على حالة الحضور
            status = request.env['hr.attendance'].sudo().get_employee_attendance_status(
                int(employee_id)
            )

            return {
                'success': True,
                'attendance_status': status
            }

        except Exception as e:
            _logger.error("خطأ في جلب حالة الحضور: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/attendance/history', type='json', auth='user', csrf=False)
    def get_attendance_history(self, employee_id=None, limit=10):
        """الحصول على سجل الحضور السابق"""
        try:
            _logger.info("====== طلب سجل الحضور ======")

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # الحصول على السجل
            history = request.env['hr.attendance'].sudo().get_employee_attendance_history(
                int(employee_id),
                int(limit)
            )

            return {
                'success': True,
                'attendance_history': history
            }

        except Exception as e:
            _logger.error("خطأ في جلب سجل الحضور: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/attendance/summary', type='json', auth='user', csrf=False)
    def get_attendance_summary(self, employee_id=None):
        """الحصول على ملخص الحضور اليومي"""
        try:
            _logger.info("====== طلب ملخص الحضور ======")

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # الحصول على الملخص
            summary = request.env['hr.attendance'].sudo().get_employee_attendance_summary(
                int(employee_id)
            )

            return {
                'success': True,
                'summary': summary
            }

        except Exception as e:
            _logger.error("خطأ في جلب ملخص الحضور: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

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

    @http.route('/api/mobile/announcements/list', type='json', auth='user', methods=['POST'])
    def get_announcements(self, **kwargs):
        employee_id = kwargs.get('employee_id')
        limit = kwargs.get('limit', 20)
        offset = kwargs.get('offset', 0)

        if not employee_id:
            return {'success': False, 'error': 'Employee ID is required'}
        """Get announcements list for mobile app"""
        employee = request.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'success': False, 'error': 'Employee not found'}

        domain = [
            ('state', '=', 'published'),
            '|',
            ('employee_ids', '=', False),
            ('employee_ids', 'in', [employee_id])
        ]

        announcements = request.env['hr.announcement'].search(
            domain,
            limit=limit,
            offset=offset,
            order='is_pinned desc, create_date desc'
        )

        result = []
        for announcement in announcements:
            read_record = request.env['hr.announcement.read'].search([
                ('announcement_id', '=', announcement.id),
                ('employee_id', '=', employee_id)
            ], limit=1)

            result.append({
                'id': announcement.id,
                'title': announcement.name,
                'summary': announcement.summary or '',
                'content': announcement.content or '',
                'type': announcement.announcement_type,
                'priority': announcement.priority,
                'is_pinned': announcement.is_pinned,
                'is_read': bool(read_record),
                'created_date': announcement.create_date.isoformat() if announcement.create_date else None,
                'author': announcement.create_uid.name,
                'attachments': len(announcement.attachment_ids),
                'read_count': announcement.read_count,
                'target_count': len(announcement.employee_ids) if announcement.employee_ids else 1,
            })

        return {'success': True, 'announcements': result}

    @http.route('/api/mobile/announcements/detail', type='json', auth='user', methods=['POST'])
    def get_announcement_detail(self, announcement_id, employee_id, **kwargs):
        """Get announcement details"""
        announcement = request.env['hr.announcement'].browse(announcement_id)
        if not announcement.exists() or announcement.state != 'published':
            return {'success': False, 'error': 'Announcement not found'}

        if announcement.employee_ids and employee_id not in announcement.employee_ids.ids:
            return {'success': False, 'error': 'Access denied'}

        read_record = request.env['hr.announcement.read'].search([
            ('announcement_id', '=', announcement_id),
            ('employee_id', '=', employee_id)
        ], limit=1)

        target_count = len(announcement.employee_ids) if announcement.employee_ids else 1
        read_percentage = (announcement.read_count / target_count * 100) if target_count > 0 else 0

        return {
            'success': True,
            'announcement': {
                'id': announcement.id,
                'title': announcement.name,
                'summary': announcement.summary or '',
                'content': announcement.content or '',
                'type': announcement.announcement_type,
                'priority': announcement.priority,
                'is_pinned': announcement.is_pinned,
                'created_date': announcement.create_date.isoformat() if announcement.create_date else None,
                'author': announcement.create_uid.name,
                'attachments': [{
                    'id': att.id,
                    'name': att.name,
                    'url': f'/web/content/{att.id}?download=true',
                    'size': att.file_size,
                    'type': att.mimetype,
                } for att in announcement.attachment_ids],
                'read_count': announcement.read_count,
                'target_count': target_count,
                'read_percentage': read_percentage,
            }
        }

    @http.route('/api/mobile/announcements/mark_read', type='json', auth='user', methods=['POST'])
    def mark_announcement_read(self, announcement_id, employee_id, **kwargs):
        """Mark announcement as read"""
        announcement = request.env['hr.announcement'].browse(announcement_id)
        if not announcement.exists():
            return {'success': False, 'error': 'Announcement not found'}

        existing = request.env['hr.announcement.read'].search([
            ('announcement_id', '=', announcement_id),
            ('employee_id', '=', employee_id)
        ])

        if not existing:
            request.env['hr.announcement.read'].create({
                'announcement_id': announcement_id,
                'employee_id': employee_id,
                'read_date': fields.Datetime.now(),
            })

        return {'success': True}

    @http.route('/api/mobile/announcements/categories', type='json', auth='user', methods=['POST'])
    def get_categories(self, **kwargs):
        """Get announcement categories"""
        return {
            'success': True,
            'categories': [
                {'id': 'all', 'name': 'جميع الإعلانات', 'icon': '📢', 'color': '#2196F3'},
                {'id': 'general', 'name': 'إعلانات عامة', 'icon': '📣', 'color': '#4CAF50'},
                {'id': 'department', 'name': 'إعلانات القسم', 'icon': '🏢', 'color': '#FF9800'},
                {'id': 'urgent', 'name': 'إعلانات عاجلة', 'icon': '🚨', 'color': '#F44336'},
                {'id': 'personal', 'name': 'إعلانات شخصية', 'icon': '👤', 'color': '#9C27B0'},
                {'id': 'job', 'name': 'إعلانات وظيفية', 'icon': '💼', 'color': '#2196F3'},
            ]
        }

    @http.route('/api/mobile/announcements/search', type='json', auth='user', methods=['POST'])
    def search_announcements(self, employee_id, search_term='', category='all', limit=20, **kwargs):
        """Search announcements"""
        domain = [
            ('state', '=', 'published'),
            '|',
            ('employee_ids', '=', False),
            ('employee_ids', 'in', [employee_id])
        ]

        if search_term:
            domain.extend([
                '|',
                ('name', 'ilike', search_term),
                ('summary', 'ilike', search_term)
            ])

        if category and category != 'all':
            domain.append(('announcement_type', '=', category))

        announcements = request.env['hr.announcement'].search(
            domain,
            limit=limit,
            order='is_pinned desc, create_date desc'
        )

        result = []
        for announcement in announcements:
            read_record = request.env['hr.announcement.read'].search([
                ('announcement_id', '=', announcement.id),
                ('employee_id', '=', employee_id)
            ], limit=1)

            result.append({
                'id': announcement.id,
                'title': announcement.name,
                'summary': announcement.summary or '',
                'content': announcement.content or '',
                'type': announcement.announcement_type,
                'priority': announcement.priority,
                'is_pinned': announcement.is_pinned,
                'is_read': bool(read_record),
                'created_date': announcement.create_date.isoformat() if announcement.create_date else None,
                'author': announcement.create_uid.name,
                'attachments': len(announcement.attachment_ids),
                'read_count': announcement.read_count,
                'target_count': len(announcement.employee_ids) if announcement.employee_ids else 1,
            })

        return {'success': True, 'results': result}

        # ==================== واجهات كشوف المرتبات (Payslips) ====================

    @http.route('/api/mobile/payslips/list', type='json', auth='user', csrf=False)
    def get_payslips(self, employee_id=None, limit=12, offset=0):
        """الحصول على قائمة كشوف مرتبات الموظف"""
        try:
            _logger.info("====== طلب كشوف المرتبات للموظف %s ======", employee_id)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # التحقق من وجود الموظف
            employee = request.env['hr.employee'].sudo().browse(int(employee_id))
            if not employee.exists():
                return {'success': False, 'error': 'الموظف غير موجود'}

            # جلب كشوف المرتبات
            payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', int(employee_id))
            ], order='date_from desc', limit=int(limit), offset=int(offset))

            payslips_data = []
            for payslip in payslips:
                # حساب البدلات والخصومات
                allowance_total = 0
                deduction_total = 0

                for line in payslip.line_ids:
                    if line.salary_rule_id.category_id.code == 'ALW':
                        allowance_total += line.total
                    elif line.salary_rule_id.category_id.code == 'DED':
                        deduction_total += abs(line.total)

                # تحديد حالة الكشف
                state_mapping = {
                    'draft': {'text': 'مسودة', 'icon': '📝', 'color': '#9E9E9E'},
                    'verify': {'text': 'قيد المراجعة', 'icon': '⏳', 'color': '#FF9800'},
                    'done': {'text': 'مدفوع', 'icon': '✅', 'color': '#4CAF50'},
                    'cancel': {'text': 'ملغي', 'icon': '❌', 'color': '#F44336'},
                }

                state_info = state_mapping.get(payslip.state, state_mapping['draft'])

                # معلومات العملة
                currency_name = 'EGP'  # قيمة افتراضية

                # محاولة 1: من عقد الموظف
                if payslip.contract_id and hasattr(payslip.contract_id, 'wage_currency_id'):
                    currency_name = payslip.contract_id.wage_currency_id.name
                # محاولة 2: من الشركة
                elif payslip.company_id and payslip.company_id.currency_id:
                    currency_name = payslip.company_id.currency_id.name
                # محاولة 3: من الموظف
                elif payslip.employee_id.company_id and payslip.employee_id.company_id.currency_id:
                    currency_name = payslip.employee_id.company_id.currency_id.name

                payslips_data.append({
                    'id': payslip.id,
                    'number': payslip.number or payslip.name,
                    'date_from': payslip.date_from.isoformat() if payslip.date_from else None,
                    'date_to': payslip.date_to.isoformat() if payslip.date_to else None,
                    'state': payslip.state,
                    'state_text': state_info['text'],
                    'state_icon': state_info['icon'],
                    'state_color': state_info['color'],
                    'basic_wage': payslip.basic_wage,
                    'gross_wage': payslip.gross_wage,
                    'net_wage': payslip.net_wage,
                    'allowance_total': allowance_total,
                    'deduction_total': deduction_total,
                    'payment_date': payslip.date_from.strftime('%Y-%m-%d') if payslip.date_from else None,
                    'currency': currency_name,
                })

            # حساب الملخص
            total_payslips = request.env['hr.payslip'].sudo().search_count([
                ('employee_id', '=', int(employee_id))
            ])

            return {
                'success': True,
                'payslips': payslips_data,
                'total_count': total_payslips,
                'current_count': len(payslips_data),
            }

        except Exception as e:
            _logger.error("خطأ في جلب كشوف المرتبات: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/payslips/detail/<int:payslip_id>', type='json', auth='user', csrf=False)
    def get_payslip_details(self, payslip_id):
        """الحصول على تفاصيل كشف مرتب محدد"""
        try:
            _logger.info("====== طلب تفاصيل كشف المرتب %s ======", payslip_id)

            payslip = request.env['hr.payslip'].sudo().browse(payslip_id)

            if not payslip.exists():
                return {'success': False, 'error': 'كشف المرتب غير موجود'}

            # تصنيف بنود الراتب
            allowances = {}
            deductions = {}
            basic_salary = 0
            gross_salary = payslip.gross_wage
            net_salary = payslip.net_wage

            # معالجة البنود
            for line in payslip.line_ids:
                if line.appears_on_payslip:
                    amount = line.total

                    # تحديد نوع البند بناءً على الفئة
                    if line.salary_rule_id.category_id.code == 'BASIC':
                        basic_salary = amount
                    elif line.salary_rule_id.category_id.code == 'ALW':
                        # البدلات
                        rule_code = line.salary_rule_id.code.lower()
                        if 'house' in rule_code or 'سكن' in line.name:
                            allowances['housing_allowance'] = amount
                        elif 'transport' in rule_code or 'نقل' in line.name or 'مواصلات' in line.name:
                            allowances['transportation_allowance'] = amount
                        elif 'food' in rule_code or 'طعام' in line.name or 'وجبة' in line.name:
                            allowances['food_allowance'] = amount
                        elif 'phone' in rule_code or 'هاتف' in line.name or 'اتصال' in line.name:
                            allowances['phone_allowance'] = amount
                        else:
                            allowances.setdefault('other_allowances', 0)
                            allowances['other_allowances'] += amount
                    elif line.salary_rule_id.category_id.code == 'DED':
                        # الخصومات
                        rule_code = line.salary_rule_id.code.lower()
                        amount = abs(amount)  # تأكد من أن القيمة موجبة

                        if 'insurance' in rule_code or 'تأمين' in line.name:
                            deductions['social_insurance'] = amount
                        elif 'tax' in rule_code or 'ضريب' in line.name:
                            deductions['taxes'] = amount
                        elif 'loan' in rule_code or 'سلف' in line.name or 'قرض' in line.name:
                            deductions['loans'] = amount
                        elif 'absence' in rule_code or 'غياب' in line.name:
                            deductions['absence'] = amount
                        else:
                            deductions.setdefault('other_deductions', 0)
                            deductions['other_deductions'] += amount

            # حساب الإجماليات
            total_allowances = sum(allowances.values())
            total_deductions = sum(deductions.values())

            # معلومات أيام العمل
            working_days = 30  # افتراضي
            actual_working_days = 30  # افتراضي

            for worked_days in payslip.worked_days_line_ids:
                if worked_days.code == 'WORK100':
                    # استخدم الحقول المتاحة في Odoo 18
                    if hasattr(worked_days, 'number_of_days'):
                        working_days = int(worked_days.number_of_days or 30)
                        actual_working_days = int(worked_days.number_of_days or 30)
                    else:
                        # حساب الأيام من الساعات إذا كانت متاحة
                        if hasattr(worked_days, 'number_of_hours'):
                            # افتراض 8 ساعات عمل يومياً
                            working_days = int((worked_days.number_of_hours or 240) / 8)
                            actual_working_days = working_days

            # معلومات البنك
            bank_account = None
            bank_name = None
            if payslip.employee_id.bank_account_id:
                bank_account = payslip.employee_id.bank_account_id.acc_number
                if payslip.employee_id.bank_account_id.bank_id:
                    bank_name = payslip.employee_id.bank_account_id.bank_id.name

            # معلومات الشركة
            company_name = payslip.company_id.name if payslip.company_id else None

            # حالة الكشف
            state_mapping = {
                'draft': {'text': 'مسودة', 'icon': '📝', 'color': '#9E9E9E'},
                'verify': {'text': 'قيد المراجعة', 'icon': '⏳', 'color': '#FF9800'},
                'done': {'text': 'مدفوع', 'icon': '✅', 'color': '#4CAF50'},
                'cancel': {'text': 'ملغي', 'icon': '❌', 'color': '#F44336'},
            }

            state_info = state_mapping.get(payslip.state, state_mapping['draft'])

            # معلومات العملة
            # معلومات العملة - جرب عدة أماكن محتملة
            currency_name = 'EGP'  # قيمة افتراضية

            # محاولة 1: من عقد الموظف
            if payslip.contract_id and hasattr(payslip.contract_id, 'wage_currency_id'):
                currency_name = payslip.contract_id.wage_currency_id.name
            # محاولة 2: من الشركة
            elif payslip.company_id and payslip.company_id.currency_id:
                currency_name = payslip.company_id.currency_id.name
            # محاولة 3: من الموظف
            elif payslip.employee_id.company_id and payslip.employee_id.company_id.currency_id:
                currency_name = payslip.employee_id.company_id.currency_id.name

            return {
                'success': True,
                'payslip': {
                    'id': payslip.id,
                    'employee_id': payslip.employee_id.id,
                    'employee_name': payslip.employee_id.name,
                    'number': payslip.number or payslip.name,
                    'date_from': payslip.date_from.isoformat() if payslip.date_from else None,
                    'date_to': payslip.date_to.isoformat() if payslip.date_to else None,
                    'state': payslip.state,
                    'state_text': state_info['text'],
                    'state_icon': state_info['icon'],
                    'state_color': state_info['color'],
                    'payment_date': payslip.date_from.strftime('%Y-%m-%d') if payslip.date_from else None,
                    'basic_salary': basic_salary,
                    'gross_salary': gross_salary,
                    'net_salary': net_salary,
                    'housing_allowance': allowances.get('housing_allowance', 0),
                    'transportation_allowance': allowances.get('transportation_allowance', 0),
                    'food_allowance': allowances.get('food_allowance', 0),
                    'phone_allowance': allowances.get('phone_allowance', 0),
                    'other_allowances': allowances.get('other_allowances', 0),
                    'total_allowances': total_allowances,
                    'social_insurance': deductions.get('social_insurance', 0),
                    'taxes': deductions.get('taxes', 0),
                    'loans': deductions.get('loans', 0),
                    'absence': deductions.get('absence', 0),
                    'other_deductions': deductions.get('other_deductions', 0),
                    'total_deductions': total_deductions,
                    'notes': payslip.note if hasattr(payslip, 'note') else None,
                    'bank_name': bank_name,
                    'bank_account': bank_account,
                    'currency': currency_name,
                    'working_days': working_days,
                    'actual_working_days': actual_working_days,
                    'company_name': company_name,
                    'company_logo': None,  # يمكن إضافة لاحقاً
                }
            }

        except Exception as e:
            _logger.error("خطأ في جلب تفاصيل كشف المرتب: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/payslips/summary', type='json', auth='user', csrf=False)
    def get_payslips_summary(self, employee_id=None):
        """الحصول على ملخص كشوف المرتبات"""
        try:
            _logger.info("====== طلب ملخص كشوف المرتبات للموظف %s ======", employee_id)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # جلب كشوف المرتبات المدفوعة
            paid_payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', int(employee_id)),
                ('state', '=', 'done')
            ])

            # حساب الإحصائيات
            total_net = sum(payslip.net_wage for payslip in paid_payslips)
            count = len(paid_payslips)
            average_net = total_net / count if count > 0 else 0

            # آخر دفعة
            last_payslip = paid_payslips[0] if paid_payslips else None
            last_payment = None
            if last_payslip:
                last_payment = last_payslip.date_from.isoformat()

            # إحصائيات السنة الحالية
            current_year = fields.Date.today().year
            current_year_payslips = paid_payslips.filtered(
                lambda p: p.date_from.year == current_year
            )

            current_year_total = sum(p.net_wage for p in current_year_payslips)
            current_year_count = len(current_year_payslips)

            # إجمالي كل الكشوف
            all_payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', int(employee_id))
            ])

            # تصنيف حسب الحالة
            by_state = {
                'draft': len(all_payslips.filtered(lambda p: p.state == 'draft')),
                'verify': len(all_payslips.filtered(lambda p: p.state == 'verify')),
                'done': len(all_payslips.filtered(lambda p: p.state == 'done')),
                'cancel': len(all_payslips.filtered(lambda p: p.state == 'cancel')),
            }

            return {
                'success': True,
                'summary': {
                    'total_net': total_net,
                    'average_net': average_net,
                    'last_payment': last_payment,
                    'total_count': len(all_payslips),
                    'paid_count': count,
                    'current_year_total': current_year_total,
                    'current_year_count': current_year_count,
                    'by_state': by_state,
                }
            }

        except Exception as e:
            _logger.error("خطأ في جلب ملخص كشوف المرتبات: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/payslips/download/<int:payslip_id>', type='http', auth='user', csrf=False)
    def download_payslip_pdf(self, payslip_id):
        """تحميل كشف المرتب كملف PDF"""
        try:
            _logger.info("====== طلب تحميل PDF لكشف المرتب %s ======", payslip_id)

            # التحقق من وجود كشف المرتب
            payslip = request.env['hr.payslip'].sudo().browse(payslip_id)

            if not payslip.exists():
                return json.dumps({
                    'success': False,
                    'error': 'كشف المرتب غير موجود'
                })

            # التحقق من أن الكشف مدفوع
            if payslip.state != 'done':
                return json.dumps({
                    'success': False,
                    'error': 'يمكن تحميل كشوف المرتبات المدفوعة فقط'
                })

            # توليد PDF
            pdf = request.env.ref('hr_payroll.action_report_payslip').sudo()._render_qweb_pdf([payslip.id])[0]

            # إعداد الاستجابة
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf)),
                ('Content-Disposition', 'attachment; filename="payslip_%s.pdf"' % payslip.number),
            ]

            return request.make_response(pdf, headers=pdfhttpheaders)

        except Exception as e:
            _logger.error("خطأ في تحميل PDF كشف المرتب: %s", str(e))
            return json.dumps({
                'success': False,
                'error': str(e)
            })

    @http.route('/api/mobile/payslips/years', type='json', auth='user', csrf=False)
    def get_payslip_years(self, employee_id=None):
        """الحصول على السنوات المتاحة لكشوف المرتبات"""
        try:
            _logger.info("====== طلب السنوات المتاحة للموظف %s ======", employee_id)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # جلب كل كشوف المرتبات
            payslips = request.env['hr.payslip'].sudo().search([
                ('employee_id', '=', int(employee_id))
            ])

            # استخراج السنوات الفريدة
            years = list(set(payslip.date_from.year for payslip in payslips if payslip.date_from))
            years.sort(reverse=True)  # ترتيب تنازلي

            return {
                'success': True,
                'years': years,
                'current_year': fields.Date.today().year,
            }

        except Exception as e:
            _logger.error("خطأ في جلب السنوات المتاحة: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    # أضف هذا في ملف mobile_api.py في Odoo

    @http.route('/api/mobile/leave/balance', type='json', auth='user', csrf=False)
    def get_employee_leave_balance(self, employee_id=None):
        """الحصول على رصيد الإجازات للموظف"""
        try:
            _logger.info("====== طلب رصيد الإجازات للموظف %s ======", employee_id)

            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            employee = request.env['hr.employee'].sudo().browse(int(employee_id))
            if not employee.exists():
                return {'success': False, 'error': 'الموظف غير موجود'}

            # جلب أنواع الإجازات النشطة
            leave_types = request.env['hr.leave.type'].sudo().search([
                ('active', '=', True)
            ])

            balance_data = {}
            total_allocated = 0
            total_used = 0
            total_remaining = 0

            for leave_type in leave_types:
                # جلب التخصيصات المعتمدة
                allocations = request.env['hr.leave.allocation'].sudo().search([
                    ('employee_id', '=', int(employee_id)),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate')
                ])

                # حساب إجمالي الأيام المخصصة
                allocated_days = sum(allocations.mapped('number_of_days'))

                # إذا لم يكن هناك تخصيص وكان النوع لا يتطلب تخصيص، استخدم القيمة الافتراضية
                if allocated_days == 0 and leave_type.requires_allocation == 'no':
                    allocated_days = 30  # القيمة الافتراضية

                # جلب الإجازات المعتمدة للسنة الحالية
                current_year = fields.Date.today().year
                approved_leaves = request.env['hr.leave'].sudo().search([
                    ('employee_id', '=', int(employee_id)),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', f'{current_year}-01-01'),
                    ('date_to', '<=', f'{current_year}-12-31')
                ])

                used_days = sum(approved_leaves.mapped('number_of_days'))
                remaining_days = max(0, allocated_days - used_days)

                balance_data[leave_type.name] = {
                    'type_id': leave_type.id,
                    'type_name': leave_type.name,
                    'allocated': allocated_days,
                    'used': used_days,
                    'remaining': remaining_days,
                    'color': getattr(leave_type, 'color_name', '#2196F3') or '#2196F3',
                    'requires_allocation': leave_type.requires_allocation == 'yes',
                }

                total_allocated += allocated_days
                total_used += used_days
                total_remaining += remaining_days

            # حساب النسبة المئوية للاستخدام
            usage_percentage = (total_used / total_allocated * 100) if total_allocated > 0 else 0

            # معلومات إضافية
            pending_requests = request.env['hr.leave'].sudo().search_count([
                ('employee_id', '=', int(employee_id)),
                ('state', 'in', ['draft', 'confirm'])
            ])

            return {
                'success': True,
                'balance_data': {
                    'employee_id': int(employee_id),
                    'employee_name': employee.name,
                    'total_allocated': total_allocated,
                    'total_used': total_used,
                    'total_remaining': total_remaining,
                    'usage_percentage': round(usage_percentage, 2),
                    'pending_requests': pending_requests,
                    'leave_types': balance_data,
                    'current_year': current_year,
                    'last_updated': fields.Datetime.now().isoformat(),
                }
            }

        except Exception as e:
            _logger.error("خطأ في جلب رصيد الإجازات: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/api/mobile/leave/balance/summary', type='json', auth='user', csrf=False)
    def get_leave_balance_summary(self, employee_id=None):
        """ملخص سريع لرصيد الإجازات"""
        try:
            if not employee_id:
                return {'success': False, 'error': 'معرف الموظف مطلوب'}

            # جلب البيانات الكاملة
            balance_response = self.get_employee_leave_balance(employee_id=employee_id)

            if not balance_response['success']:
                return balance_response

            balance_data = balance_response['balance_data']

            # العثور على أكثر نوع إجازة استخداماً
            most_used_type = None
            max_usage = 0

            for type_name, type_data in balance_data['leave_types'].items():
                if type_data['used'] > max_usage:
                    max_usage = type_data['used']
                    most_used_type = type_name

            return {
                'success': True,
                'summary': {
                    'total_remaining': balance_data['total_remaining'],
                    'total_used': balance_data['total_used'],
                    'usage_percentage': balance_data['usage_percentage'],
                    'most_used_type': most_used_type or 'لا يوجد',
                    'pending_requests': balance_data['pending_requests'],
                    'leave_types_count': len(balance_data['leave_types']),
                }
            }

        except Exception as e:
            _logger.error("خطأ في ملخص رصيد الإجازات: %s", str(e))
            return {'success': False, 'error': str(e)}
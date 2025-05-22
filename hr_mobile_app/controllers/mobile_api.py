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
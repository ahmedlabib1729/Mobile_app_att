# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from collections import OrderedDict
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class StudentPortal(CustomerPortal):

    def _get_current_student(self):
        """Helper method to get current student"""
        # البحث أولاً بـ user_id
        student = request.env['quran.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        # إذا لم يجد، ابحث بـ partner_id
        if not student and request.env.user.partner_id:
            student = request.env['quran.student'].sudo().search([
                ('partner_id', '=', request.env.user.partner_id.id)
            ], limit=1)

        return student

    def _prepare_home_portal_values(self, counters):
        """إضافة عدادات خاصة بالطالب للصفحة الرئيسية للبورتال"""
        values = super()._prepare_home_portal_values(counters)

        if 'student_info' in counters:
            current_student = self._get_current_student()
            if current_student:
                values['student_info'] = current_student

        if 'class_count' in counters:
            current_student = self._get_current_student()
            if current_student:
                values['class_count'] = len(current_student.class_ids)

        if 'session_count' in counters:
            current_student = self._get_current_student()
            if current_student:
                # عد الجلسات القادمة فقط
                today = datetime.now().date()
                future_sessions = request.env['quran.session.attendance'].sudo().search_count([
                    ('student_id', '=', current_student.id),
                    ('session_id.session_date', '>=', today),
                    ('session_id.state', 'in', ['scheduled', 'ongoing'])
                ])
                values['session_count'] = future_sessions

        return values

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        """تخصيص الصفحة الرئيسية للبورتال للطلاب"""
        # التحقق من وجود طالب مرتبط بالمستخدم
        student = self._get_current_student()

        if student:
            # إعادة توجيه الطالب لصفحة Dashboard الخاصة به
            return request.redirect('/my/dashboard')

        # إذا لم يكن طالباً، عرض الصفحة الافتراضية
        return super().home(**kw)

    @http.route(['/my/dashboard'], type='http', auth='user', website=True)
    def student_dashboard(self, **kwargs):
        """لوحة معلومات الطالب الرئيسية"""
        student = self._get_current_student()

        if not student:
            return request.redirect('/my')

        # جمع البيانات للـ Dashboard
        today = datetime.now()

        # الجلسات القادمة (أقرب 5 جلسات)
        upcoming_sessions = request.env['quran.session.attendance'].sudo().search([
            ('student_id', '=', student.id),
            ('session_id.session_date', '>=', today.date()),
            ('session_id.state', 'in', ['scheduled', 'ongoing'])
        ], limit=5)

        # ترتيب الجلسات يدوياً حسب التاريخ
        upcoming_sessions = upcoming_sessions.sorted(key=lambda x: (x.session_id.session_date, x.session_id.id))

        # الجلسات النشطة حالياً (الأونلاين)
        active_online_sessions = request.env['quran.session.attendance'].sudo().search([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'ongoing'),
            ('session_id.is_meeting_active', '=', True),
            ('session_id.class_session_type', '=', 'Online')
        ])

        # حساب إحصائيات الحضور
        total_sessions = request.env['quran.session.attendance'].sudo().search_count([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'completed')
        ])

        present_sessions = request.env['quran.session.attendance'].sudo().search_count([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'completed'),
            ('status', '=', 'present')
        ])

        attendance_rate = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0

        # إحصائيات الحفظ
        memorization_progress = {
            'current_pages': student.current_memorized_pages,
            'total_pages': 604,  # إجمالي صفحات المصحف
            'percentage': (student.current_memorized_pages / 604 * 100) if student.current_memorized_pages else 0
        }

        # عدد المواثيق المسجل بها (إن وجدت)
        covenant_count = len(student.covenant_ids) if hasattr(student, 'covenant_ids') else 0

        values = {
            'student': student,
            'upcoming_sessions': upcoming_sessions,
            'active_online_sessions': active_online_sessions,
            'attendance_rate': round(attendance_rate, 1),
            'total_sessions': total_sessions,
            'present_sessions': present_sessions,
            'memorization_progress': memorization_progress,
            'covenant_count': covenant_count,
            'page_name': 'student_dashboard',
        }

        # استخدم template نظيف بدون مشاكل
        return request.render('quran_center.portal_student_dashboard', values)

    @http.route(['/my/classes', '/my/classes/page/<int:page>'], type='http', auth='user', website=True)
    def student_classes(self, page=1, **kwargs):
        """عرض صفوف الطالب"""
        student = self._get_current_student()

        if not student:
            return request.redirect('/my')

        # إعداد الـ pager
        classes_count = len(student.class_ids)
        pager = portal_pager(
            url="/my/classes",
            total=classes_count,
            page=page,
            step=10
        )

        # جلب الصفوف مع الـ pagination
        classes = student.class_ids.sorted('create_date', reverse=True)

        values = {
            'student': student,
            'classes': classes,
            'pager': pager,
            'page_name': 'student_classes',
        }

        return request.render('quran_center.portal_student_classes', values)

    @http.route([
        '/my/sessions',
        '/my/sessions/page/<int:page>',
        '/my/sessions/<string:filter_type>'
    ], type='http', auth='user', website=True)
    def student_sessions(self, page=1, filter_type='upcoming', **kwargs):
        """عرض جلسات الطالب مع إمكانية الفلترة"""
        student = self._get_current_student()

        if not student:
            return request.redirect('/my')

        today = datetime.now()
        domain = [('student_id', '=', student.id)]

        # تطبيق الفلتر حسب النوع
        if filter_type == 'today':
            domain.extend([
                ('session_id.session_date', '=', today.date()),
                ('session_id.state', 'in', ['scheduled', 'ongoing'])
            ])
        elif filter_type == 'upcoming':
            domain.extend([
                ('session_id.session_date', '>', today.date()),
                ('session_id.state', 'in', ['scheduled'])
            ])
        elif filter_type == 'past':
            domain.extend([
                ('session_id.state', '=', 'completed')
            ])
        elif filter_type == 'active':
            domain.extend([
                ('session_id.state', '=', 'ongoing'),
                ('session_id.is_meeting_active', '=', True)
            ])

        # إعداد الـ pager
        sessions_count = request.env['quran.session.attendance'].sudo().search_count(domain)
        pager = portal_pager(
            url=f"/my/sessions/{filter_type}",
            total=sessions_count,
            page=page,
            step=10
        )

        # جلب الجلسات
        sessions = request.env['quran.session.attendance'].sudo().search(
            domain,
            limit=10,
            offset=(page - 1) * 10
        )

        # ترتيب الجلسات يدوياً حسب التاريخ
        sessions = sessions.sorted(key=lambda x: (x.session_id.session_date, x.session_id.id), reverse=True)

        values = {
            'student': student,
            'sessions': sessions,
            'pager': pager,
            'filter_type': filter_type,
            'page_name': 'student_sessions',
        }

        return request.render('quran_center.portal_student_sessions', values)

    @http.route(['/my/session/<int:session_attendance_id>/join'], type='http', auth='user', website=True)
    def join_online_session(self, session_attendance_id, **kwargs):
        """الانضمام للجلسة الأونلاين"""
        student = self._get_current_student()

        if not student:
            return request.redirect('/my')

        # التحقق من صحة الجلسة
        attendance = request.env['quran.session.attendance'].sudo().search([
            ('id', '=', session_attendance_id),
            ('student_id', '=', student.id)
        ], limit=1)

        if not attendance:
            return request.redirect('/my/sessions')

        session = attendance.session_id

        # التحقق من إمكانية الدخول
        if not session.can_join_meeting:
            values = {
                'error_title': _('لا يمكن الدخول للجلسة'),
                'error_message': _('الجلسة غير متاحة حالياً. يرجى الانتظار حتى يبدأ المعلم الجلسة.'),
                'return_url': '/my/sessions'
            }
            return request.render('quran_center.portal_error_page', values)

        # تسجيل دخول الطالب
        try:
            attendance.action_join_online()

            # إعادة التوجيه لرابط الاجتماع
            return request.redirect(session.meeting_url)

        except Exception as e:
            _logger.error(f"Error joining session: {str(e)}")
            values = {
                'error_title': _('خطأ في الدخول'),
                'error_message': _('حدث خطأ أثناء محاولة الدخول للجلسة. يرجى المحاولة مرة أخرى.'),
                'return_url': '/my/sessions'
            }
            return request.render('quran_center.portal_error_page', values)

    @http.route(['/my/profile'], type='http', auth='user', website=True)
    def student_profile(self, **kwargs):
        """عرض وتعديل الملف الشخصي للطالب"""
        student = self._get_current_student()

        if not student:
            return request.redirect('/my')

        values = {
            'student': student,
            'page_name': 'student_profile',
        }

        return request.render('quran_center.portal_student_profile', values)

    # AJAX Routes
    @http.route(['/my/sessions/check-active'], type='json', auth='user', website=True)
    def check_active_sessions(self, **kwargs):
        """التحقق من الجلسات النشطة عبر AJAX"""
        student = self._get_current_student()

        if not student:
            return {'has_active_session': False}

        # البحث عن جلسات أونلاين نشطة
        active_session = request.env['quran.session.attendance'].sudo().search([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'ongoing'),
            ('session_id.is_meeting_active', '=', True),
            ('session_id.class_session_type', '=', 'Online'),
            ('is_online_now', '=', False)  # لم يدخل بعد
        ], limit=1)

        if active_session:
            return {
                'has_active_session': True,
                'session_info': {
                    'name': active_session.session_id.name,
                    'class_name': active_session.session_id.class_id.name,
                    'teacher': active_session.session_id.teacher_id.name,
                    'join_url': f'/my/session/{active_session.id}/join'
                }
            }

        return {'has_active_session': False}

    @http.route(['/my/session/<int:session_id>/leave'], type='json', auth='user', website=True)
    def leave_online_session(self, session_id, **kwargs):
        """تسجيل خروج الطالب من الجلسة"""
        student = self._get_current_student()

        if not student:
            return {'success': False, 'error': 'Student not found'}

        attendance = request.env['quran.session.attendance'].sudo().search([
            ('id', '=', session_id),
            ('student_id', '=', student.id),
            ('is_online_now', '=', True)
        ], limit=1)

        if attendance:
            try:
                attendance.action_leave_online()
                return {
                    'success': True,
                    'duration': attendance.online_duration,
                    'attendance_percentage': attendance.attendance_percentage
                }
            except Exception as e:
                _logger.error(f"Error leaving session: {str(e)}")
                return {'success': False, 'error': str(e)}

        return {'success': False, 'error': 'Session not found'}

    @http.route(['/my/stats/refresh'], type='json', auth='user', website=True)
    def refresh_stats(self, **kwargs):
        """تحديث الإحصائيات عبر AJAX"""
        student = self._get_current_student()

        if not student:
            return {}

        # حساب الإحصائيات المحدثة
        total_sessions = request.env['quran.session.attendance'].sudo().search_count([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'completed')
        ])

        present_sessions = request.env['quran.session.attendance'].sudo().search_count([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'completed'),
            ('status', '=', 'present')
        ])

        attendance_rate = (present_sessions / total_sessions * 100) if total_sessions > 0 else 0

        return {
            'attendance_rate': round(attendance_rate, 1),
            'total_sessions': total_sessions,
            'present_sessions': present_sessions,
            'memorization_pages': student.current_memorized_pages,
            'class_count': len(student.class_ids)
        }
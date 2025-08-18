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

        absent_sessions = request.env['quran.session.attendance'].sudo().search_count([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'completed'),
            ('status', '=', 'absent')
        ])

        late_sessions = request.env['quran.session.attendance'].sudo().search_count([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'completed'),
            ('status', '=', 'late')
        ])

        excused_sessions = request.env['quran.session.attendance'].sudo().search_count([
            ('student_id', '=', student.id),
            ('session_id.state', '=', 'completed'),
            ('status', '=', 'excused')
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
            'absent_sessions': absent_sessions,
            'late_sessions': late_sessions,
            'excused_sessions': excused_sessions,
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

        # تقسيم الصفوف حسب الحالة
        all_classes = student.class_ids

        # الصفوف الجارية
        ongoing_classes = all_classes.filtered(lambda c: c.state == 'in_progress')

        # الصفوف القادمة
        upcoming_classes = all_classes.filtered(lambda c: c.state in ['draft', 'confirmed'])

        # الصفوف المنتهية
        completed_classes = all_classes.filtered(lambda c: c.state == 'completed')

        values = {
            'student': student,
            'ongoing_classes': ongoing_classes,
            'upcoming_classes': upcoming_classes,
            'completed_classes': completed_classes,
            'page_name': 'student_classes',
        }

        return request.render('quran_center.portal_student_classes', values)

    @http.route([
        '/my/sessions',
        '/my/sessions/page/<int:page>',
        '/my/sessions/<string:filter_type>'
    ], type='http', auth='user', website=True)
    def student_sessions(self, page=1, filter_type='active', **kwargs):
        """عرض جلسات الطالب مع إمكانية الفلترة"""
        student = self._get_current_student()

        if not student:
            return request.redirect('/my')

        today = datetime.now()
        domain = [('student_id', '=', student.id)]

        # تطبيق الفلتر حسب النوع
        if filter_type == 'active':
            # الجلسات النشطة حالياً (يمكن الدخول إليها)
            domain.extend([
                ('session_id.state', '=', 'ongoing'),
                ('session_id.is_meeting_active', '=', True),
                ('session_id.class_session_type', '=', 'Online')
            ])
        elif filter_type == 'today':
            # جلسات اليوم (مجدولة أو جارية)
            domain.extend([
                ('session_id.session_date', '=', today.date()),
                ('session_id.state', 'in', ['scheduled', 'ongoing'])
            ])
        elif filter_type == 'upcoming':
            # الجلسات القادمة
            domain.extend([
                ('session_id.session_date', '>', today.date()),
                ('session_id.state', '=', 'scheduled')
            ])
        elif filter_type == 'completed':
            # الجلسات المنتهية
            domain.extend([
                ('session_id.state', '=', 'completed')
            ])

        # إعداد الـ pager
        sessions_count = request.env['quran.session.attendance'].sudo().search_count(domain)
        pager = portal_pager(
            url=f"/my/sessions/{filter_type}",
            total=sessions_count,
            page=page,
            step=10
        )

        # جلب الجلسات مع كل الحقول المطلوبة
        sessions = request.env['quran.session.attendance'].sudo().search(
            domain,
            limit=10,
            offset=(page - 1) * 10
        )

        # ترتيب الجلسات
        if filter_type == 'completed':
            # الجلسات المنتهية - الأحدث أولاً
            sessions = sessions.sorted(key=lambda x: (x.session_id.session_date, x.session_id.id), reverse=True)
        else:
            # باقي الجلسات - الأقرب أولاً
            sessions = sessions.sorted(key=lambda x: (x.session_id.session_date, x.session_id.id))

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
            # استخدام template بسيط بدون portal layout
            html = """
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>خطأ</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            background-color: #f5f5f5;
                        }
                        .error-container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            text-align: center;
                            max-width: 500px;
                        }
                        .error-icon {
                            font-size: 60px;
                            color: #dc3545;
                            margin-bottom: 20px;
                        }
                        h2 {
                            color: #dc3545;
                            margin-bottom: 10px;
                        }
                        p {
                            color: #666;
                            margin-bottom: 30px;
                        }
                        .btn {
                            display: inline-block;
                            padding: 12px 30px;
                            background-color: #007bff;
                            color: white;
                            text-decoration: none;
                            border-radius: 5px;
                            transition: background-color 0.3s;
                        }
                        .btn:hover {
                            background-color: #0056b3;
                        }
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <div class="error-icon">⚠️</div>
                        <h2>لا يمكن الدخول للجلسة</h2>
                        <p>الجلسة غير متاحة حالياً. يرجى الانتظار حتى يبدأ المعلم الجلسة.</p>
                        <a href="/my/sessions" class="btn">العودة للجلسات</a>
                    </div>
                </body>
            </html>
            """
            return request.make_response(html)

        # تسجيل دخول الطالب
        try:
            # تحديث نوع الحضور للأونلاين إذا لزم الأمر
            if attendance.attendance_type != 'online':
                attendance.attendance_type = 'online'

            attendance.action_join_online()

            # إعادة التوجيه لرابط الاجتماع مباشرة
            if session.meeting_url:
                return request.redirect(session.meeting_url)
            else:
                # إذا لم يكن هناك رابط، استخدم صفحة خطأ بسيطة
                html = """
                <!DOCTYPE html>
                <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>خطأ</title>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                min-height: 100vh;
                                margin: 0;
                                background-color: #f5f5f5;
                            }
                            .error-container {
                                background: white;
                                padding: 40px;
                                border-radius: 10px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                                text-align: center;
                            }
                            .btn {
                                display: inline-block;
                                margin-top: 20px;
                                padding: 12px 30px;
                                background-color: #007bff;
                                color: white;
                                text-decoration: none;
                                border-radius: 5px;
                            }
                        </style>
                    </head>
                    <body>
                        <div class="error-container">
                            <h2>لا يوجد رابط للاجتماع</h2>
                            <p>يرجى التواصل مع المعلم.</p>
                            <a href="/my/sessions" class="btn">العودة للجلسات</a>
                        </div>
                    </body>
                </html>
                """
                return request.make_response(html)

        except Exception as e:
            _logger.error(f"Error joining session: {str(e)}")
            # صفحة خطأ بسيطة
            html = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="UTF-8">
                    <title>خطأ</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            background-color: #f5f5f5;
                        }}
                        .error-container {{
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            text-align: center;
                            max-width: 500px;
                        }}
                        .error-icon {{
                            font-size: 60px;
                            color: #dc3545;
                            margin-bottom: 20px;
                        }}
                        h2 {{
                            color: #dc3545;
                            margin-bottom: 10px;
                        }}
                        p {{
                            color: #666;
                            margin-bottom: 30px;
                        }}
                        .error-details {{
                            background: #f8f9fa;
                            padding: 15px;
                            border-radius: 5px;
                            margin-bottom: 20px;
                            font-size: 14px;
                            color: #666;
                            text-align: left;
                            direction: ltr;
                        }}
                        .btn {{
                            display: inline-block;
                            padding: 12px 30px;
                            background-color: #007bff;
                            color: white;
                            text-decoration: none;
                            border-radius: 5px;
                            transition: background-color 0.3s;
                        }}
                        .btn:hover {{
                            background-color: #0056b3;
                        }}
                    </style>
                </head>
                <body>
                    <div class="error-container">
                        <div class="error-icon">❌</div>
                        <h2>خطأ في الدخول</h2>
                        <p>حدث خطأ أثناء محاولة الدخول للجلسة. يرجى المحاولة مرة أخرى.</p>
                        <div class="error-details">{str(e)}</div>
                        <a href="/my/sessions" class="btn">العودة للجلسات</a>
                    </div>
                </body>
            </html>
            """
            return request.make_response(html)

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
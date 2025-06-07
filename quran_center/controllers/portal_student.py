# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime, timedelta


class StudentPortal(CustomerPortal):

    @http.route(['/my/account/dashboard'], type='http', auth="user", website=True)
    def student_dashboard(self, **kw):
        """صفحة Dashboard الرئيسية للطالب"""

        # التحقق من أن المستخدم طالب
        student = request.env['quran.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        # حساب الإحصائيات الأساسية
        total_classes = len(student.class_ids.filtered(lambda c: c.state == 'active'))

        # حساب نسبة الحضور
        attendance_records = request.env['quran.session.attendance'].sudo().search([
            ('student_id', '=', student.id)
        ])
        attendance_percentage = 0
        if attendance_records:
            present_count = len(attendance_records.filtered(lambda r: r.status == 'present'))
            attendance_percentage = (present_count / len(attendance_records)) * 100

        # الجلسات القادمة (أقرب 3 جلسات)
        upcoming_sessions = request.env['quran.session'].sudo().search([
            ('class_id', 'in', student.class_ids.ids),
            ('date', '>=', datetime.today()),
            ('state', 'in', ['draft', 'confirmed'])
        ], order='date asc', limit=3)

        # آخر جلسة حضرها
        last_attendance = request.env['quran.session.attendance'].sudo().search([
            ('student_id', '=', student.id),
            ('status', '=', 'present')
        ], order='session_id.date desc', limit=1)

        # نسبة الحفظ
        memorization_percentage = 0
        if student.current_memorized_pages:
            memorization_percentage = (student.current_memorized_pages / 604) * 100

        values = {
            'student': student,
            'total_classes': total_classes,
            'attendance_percentage': round(attendance_percentage, 1),
            'upcoming_sessions': upcoming_sessions,
            'last_attendance': last_attendance,
            'memorization_percentage': round(memorization_percentage, 1),
            'total_memorized': student.current_memorized_pages,
            'page_name': 'dashboard',
        }

        return request.render("quran_center.portal_student_dashboard_main", values)
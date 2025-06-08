# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime, timedelta


class QuranPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'session_count' in counters:
            student = request.env['quran.student'].sudo().search([
                ('user_ids', 'in', request.env.user.id)
            ], limit=1)

            if student:
                session_count = request.env['quran.session'].sudo().search_count([
                    ('class_id.student_ids', 'in', student.id),
                    ('state', 'in', ['scheduled', 'ongoing']),
                    ('session_date', '>=', fields.Date.today())
                ])
                values['session_count'] = session_count

        return values

    @http.route(['/my/sessions', '/my/sessions/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_my_sessions(self, page=1, **kw):
        student = request.env['quran.student'].sudo().search([
            ('user_ids', 'in', request.env.user.id)
        ], limit=1)

        if not student:
            return request.render("your_module.portal_no_student_access")

        Session = request.env['quran.session'].sudo()

        # الجلسات القادمة والجارية
        domain = [
            ('class_id.student_ids', 'in', student.id),
            ('state', 'in', ['scheduled', 'ongoing']),
            ('session_date', '>=', fields.Date.today())
        ]

        # عدد الجلسات
        session_count = Session.search_count(domain)

        # إعدادات الصفحات
        pager = request.website.pager(
            url="/my/sessions",
            total=session_count,
            page=page,
            step=10
        )

        # جلب الجلسات
        sessions = Session.search(
            domain,
            order='start_datetime asc',
            limit=10,
            offset=pager['offset']
        )

        # إضافة معلومات إضافية لكل جلسة
        sessions_data = []
        for session in sessions:
            # حساب الوقت المتبقي
            now = datetime.now()
            time_until_start = session.start_datetime - now if session.start_datetime > now else timedelta(0)

            # يمكن الانضمام قبل 15 دقيقة
            can_join_time = session.start_datetime - timedelta(minutes=15)
            can_join_now = now >= can_join_time and session.class_session_type == 'Online'

            sessions_data.append({
                'session': session,
                'time_until_start': time_until_start,
                'can_join_now': can_join_now and session.meeting_id,
                'is_today': session.session_date == fields.Date.today(),
                'is_ongoing': session.state == 'ongoing',
            })

        values = {
            'sessions': sessions_data,
            'page_name': 'sessions',
            'pager': pager,
            'default_url': '/my/sessions',
            'student': student,
        }

        return request.render("your_module.portal_my_sessions", values)

    @http.route(['/my/session/<int:session_id>/join'],
                type='http', auth="user", website=True)
    def portal_session_join(self, session_id, **kw):
        """الانضمام للجلسة الأونلاين"""
        student = request.env['quran.student'].sudo().search([
            ('user_ids', 'in', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        session = request.env['quran.session'].sudo().browse(session_id)

        # التحقق من الصلاحيات
        if student.id not in session.class_id.student_ids.ids:
            return request.render("your_module.portal_access_denied")

        # التحقق من إمكانية الانضمام
        if not session.can_join_meeting:
            return request.redirect('/my/sessions')

        # الانضمام للقناة
        if session.meeting_channel_id:
            # إضافة الطالب للقناة إذا لم يكن عضواً
            partner = request.env.user.partner_id
            if partner.id not in session.meeting_channel_id.channel_partner_ids.ids:
                session.meeting_channel_id.sudo().write({
                    'channel_partner_ids': [(4, partner.id)]
                })

            # توجيه لصفحة الاجتماع
            return request.redirect(f'/discuss/channel/{session.meeting_channel_id.id}')

        return request.redirect('/my/sessions')

    @http.route(['/my/session/<int:session_id>'],
                type='http', auth="user", website=True)
    def portal_session_details(self, session_id, **kw):
        """عرض تفاصيل الجلسة"""
        student = request.env['quran.student'].sudo().search([
            ('user_ids', 'in', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        session = request.env['quran.session'].sudo().browse(session_id)

        # التحقق من الصلاحيات
        if student.id not in session.class_id.student_ids.ids:
            return request.render("your_module.portal_access_denied")

        # جلب سجل حضور الطالب
        attendance = request.env['quran.session.attendance'].sudo().search([
            ('session_id', '=', session_id),
            ('student_id', '=', student.id)
        ], limit=1)

        values = {
            'session': session,
            'attendance': attendance,
            'student': student,
            'page_name': 'session_details',
        }

        return request.render("your_module.portal_session_details", values)
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime, date, timedelta


class StudentPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        student = request.env['hallway.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if student:
            if 'enrollment_count' in counters:
                values['enrollment_count'] = request.env['hallway.enrollment'].sudo().search_count([
                    ('student_id', '=', student.id),
                    ('state', 'in', ['enrolled', 'in_progress'])
                ])

            if 'session_count' in counters:
                today = date.today()
                active_enrollments = request.env['hallway.enrollment'].sudo().search([
                    ('student_id', '=', student.id),
                    ('state', 'in', ['enrolled', 'in_progress'])
                ])

                if active_enrollments:
                    values['session_count'] = request.env['hallway.course.session'].sudo().search_count([
                        ('course_id', 'in', active_enrollments.mapped('course_id').ids),
                        ('date', '>=', today),
                        ('date', '<=', today + timedelta(days=30)),
                        ('state', '!=', 'cancelled')
                    ])
                else:
                    values['session_count'] = 0

            if 'payment_count' in counters:
                values['payment_count'] = request.env['hallway.payment.line'].sudo().search_count([
                    ('student_id', '=', student.id),
                    ('state', 'in', ['pending', 'overdue'])
                ])

        return values

    @http.route(['/my/profile'], type='http', auth='user')
    def portal_my_profile(self, **kw):
        student = request.env['hallway.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()
        values.update({
            'student': student,
            'page_name': 'profile',
        })

        return request.render('HallWay_System.portal_my_profile', values)

    @http.route(['/my/enrollments', '/my/enrollments/page/<int:page>'], type='http', auth='user')
    def portal_my_enrollments(self, page=1, **kw):
        student = request.env['hallway.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()

        Enrollment = request.env['hallway.enrollment'].sudo()
        domain = [('student_id', '=', student.id)]

        enrollment_count = Enrollment.search_count(domain)

        pager = portal_pager(
            url="/my/enrollments",
            total=enrollment_count,
            page=page,
            step=self._items_per_page
        )

        enrollments = Enrollment.search(
            domain,
            limit=self._items_per_page,
            offset=pager['offset'],
            order='enrollment_date desc'
        )

        values.update({
            'enrollments': enrollments,
            'page_name': 'enrollment',
            'pager': pager,
            'default_url': '/my/enrollments',
        })

        return request.render('HallWay_System.portal_my_enrollments', values)

    @http.route(['/my/enrollment/<int:enrollment_id>'], type='http', auth='user')
    def portal_enrollment_detail(self, enrollment_id, **kw):
        enrollment = request.env['hallway.enrollment'].sudo().browse(enrollment_id)
        if not enrollment.exists() or enrollment.student_id.user_id != request.env.user:
            return request.redirect('/my/enrollments')

        values = self._prepare_portal_layout_values()
        values.update({
            'enrollment': enrollment,
            'page_name': 'enrollment',
        })

        return request.render('HallWay_System.portal_enrollment_page', values)

    @http.route(['/my/schedule'], type='http', auth='user')
    def portal_my_schedule(self, **kw):
        student = request.env['hallway.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()

        active_enrollments = request.env['hallway.enrollment'].sudo().search([
            ('student_id', '=', student.id),
            ('state', 'in', ['enrolled', 'in_progress'])
        ])

        today = date.today()
        end_date = today + timedelta(days=30)

        sessions = []
        if active_enrollments:
            sessions = request.env['hallway.course.session'].sudo().search([
                ('course_id', 'in', active_enrollments.mapped('course_id').ids),
                ('date', '>=', today),
                ('date', '<=', end_date),
                ('state', '!=', 'cancelled')
            ], order='date asc, start_time asc')

        sessions_by_date = {}
        for session in sessions:
            date_str = session.date.strftime('%Y-%m-%d')
            if date_str not in sessions_by_date:
                sessions_by_date[date_str] = []
            sessions_by_date[date_str].append(session)

        values.update({
            'sessions': sessions,
            'sessions_by_date': sessions_by_date,
            'page_name': 'schedule',
            'today': today,
            'datetime': datetime,
        })

        return request.render('HallWay_System.portal_my_schedule', values)

    @http.route(['/my/payments', '/my/payments/page/<int:page>'], type='http', auth='user')
    def portal_my_payments(self, page=1, **kw):
        student = request.env['hallway.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()

        PaymentLine = request.env['hallway.payment.line'].sudo()
        domain = [('student_id', '=', student.id)]

        payment_count = PaymentLine.search_count(domain)

        pager = portal_pager(
            url="/my/payments",
            total=payment_count,
            page=page,
            step=self._items_per_page
        )

        payments = PaymentLine.search(
            domain,
            order='due_date desc',
            limit=self._items_per_page,
            offset=pager['offset']
        )

        all_payments = PaymentLine.search([('student_id', '=', student.id)])
        overdue_payments = all_payments.filtered(lambda p: p.state == 'overdue')
        pending_payments = all_payments.filtered(lambda p: p.state == 'pending')
        paid_payments = all_payments.filtered(lambda p: p.state == 'paid')

        values.update({
            'payments': payments,
            'payment_lines': payments,  # alias
            'page_name': 'payment',
            'pager': pager,
            'default_url': '/my/payments',
            'overdue_total': sum(overdue_payments.mapped('final_amount')),
            'pending_total': sum(pending_payments.mapped('final_amount')),
            'paid_total': sum(paid_payments.mapped('final_amount')),
            'overdue_count': len(overdue_payments),
            'pending_count': len(pending_payments),
            'paid_count': len(paid_payments),
            'overdue_payments': overdue_payments,
            'pending_payments': pending_payments,
            'paid_payments': paid_payments,
        })

        return request.render('HallWay_System.portal_my_payments', values)

    @http.route(['/my/attendance'], type='http', auth='user')
    def portal_my_attendance(self, **kw):
        student = request.env['hallway.student'].sudo().search([
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not student:
            return request.redirect('/my')

        values = self._prepare_portal_layout_values()

        enrollments = request.env['hallway.enrollment'].sudo().search([
            ('student_id', '=', student.id),
            ('state', 'in', ['enrolled', 'in_progress', 'completed'])
        ])

        values.update({
            'enrollments': enrollments,
            'page_name': 'attendance',
        })

        return request.render('HallWay_System.portal_my_attendance', values)
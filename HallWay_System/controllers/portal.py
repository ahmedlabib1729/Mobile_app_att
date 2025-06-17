# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from datetime import datetime, date, timedelta
import json


class StudentPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        student = request.env['hallway.student'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)

        if student:
            if 'enrollment_count' in counters:
                enrollments = request.env['hallway.enrollment'].sudo().search([
                    ('student_id', '=', student.id),
                    ('state', 'in', ['enrolled', 'in_progress'])
                ])
                values['enrollment_count'] = len(enrollments)

            if 'session_count' in counters:
                today = date.today()
                sessions = request.env['hallway.course.session'].sudo().search([
                    ('course_id.enrollment_ids.student_id', '=', student.id),
                    ('date', '>=', today)
                ])
                values['session_count'] = len(sessions)

            if 'payment_count' in counters:
                payments = request.env['hallway.payment.line'].sudo().search([
                    ('student_id', '=', student.id),
                    ('state', 'in', ['pending', 'overdue'])
                ])
                values['payment_count'] = len(payments)

        return values

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        values = self._prepare_home_portal_values(counters={
            'enrollment_count': True,
            'session_count': True,
            'payment_count': True,
        })
        return request.render("portal.portal_my_home", values)

    @http.route(['/my/profile'], type='http', auth='user', website=True)
    def portal_my_profile(self, **kw):
        student = request.env['hallway.student'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not student:
            return request.redirect('/my')

        values = {
            'student': student,
            'page_name': 'profile',
        }
        return request.render('HallWay_System.portal_my_profile', values)

    @http.route(['/my/enrollments', '/my/enrollments/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_enrollments(self, page=1, **kw):
        student = request.env['hallway.student'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not student:
            return request.redirect('/my')

        Enrollment = request.env['hallway.enrollment'].sudo()

        # Count enrollments
        enrollment_count = Enrollment.search_count([('student_id', '=', student.id)])

        # Pager
        pager = request.website.pager(
            url="/my/enrollments",
            total=enrollment_count,
            page=page,
            step=10
        )

        # Get enrollments
        enrollments = Enrollment.search([
            ('student_id', '=', student.id)
        ], limit=10, offset=pager['offset'], order='enrollment_date desc')

        values = {
            'enrollments': enrollments,
            'page_name': 'enrollment',
            'pager': pager,
            'default_url': '/my/enrollments',
        }
        return request.render('HallWay_System.portal_my_enrollments', values)

    @http.route(['/my/enrollment/<int:enrollment_id>'], type='http', auth='user', website=True)
    def portal_enrollment_detail(self, enrollment_id, **kw):
        student = request.env['hallway.student'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not student:
            return request.redirect('/my')

        enrollment = request.env['hallway.enrollment'].sudo().browse(enrollment_id)
        if not enrollment or enrollment.student_id.id != student.id:
            return request.redirect('/my/enrollments')

        values = {
            'enrollment': enrollment,
            'page_name': 'enrollment',
        }
        return request.render('HallWay_System.portal_enrollment_page', values)

    @http.route(['/my/schedule'], type='http', auth='user', website=True)
    def portal_my_schedule(self, **kw):
        student = request.env['hallway.student'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not student:
            return request.redirect('/my')

        # Get active enrollments
        enrollments = request.env['hallway.enrollment'].sudo().search([
            ('student_id', '=', student.id),
            ('state', 'in', ['enrolled', 'in_progress'])
        ])

        # Get sessions for next 30 days
        today = date.today()
        end_date = today + timedelta(days=30)

        sessions = request.env['hallway.course.session'].sudo().search([
            ('course_id', 'in', enrollments.mapped('course_id').ids),
            ('date', '>=', today),
            ('date', '<=', end_date),
            ('state', '!=', 'cancelled')
        ], order='date, start_time')

        # Group sessions by date
        sessions_by_date = {}
        for session in sessions:
            date_str = session.date.strftime('%Y-%m-%d')
            if date_str not in sessions_by_date:
                sessions_by_date[date_str] = []
            sessions_by_date[date_str].append(session)

        values = {
            'sessions': sessions,
            'sessions_by_date': sessions_by_date,
            'page_name': 'schedule',
            'today': today,
        }
        return request.render('HallWay_System.portal_my_schedule', values)

    @http.route(['/my/payments'], type='http', auth='user', website=True)
    def portal_my_payments(self, **kw):
        student = request.env['hallway.student'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not student:
            return request.redirect('/my')

        # Get all payment lines
        payment_lines = request.env['hallway.payment.line'].sudo().search([
            ('student_id', '=', student.id)
        ], order='due_date')

        # Separate by status
        overdue_payments = payment_lines.filtered(lambda p: p.state == 'overdue')
        pending_payments = payment_lines.filtered(lambda p: p.state == 'pending')
        paid_payments = payment_lines.filtered(lambda p: p.state == 'paid')

        values = {
            'payment_lines': payment_lines,
            'overdue_payments': overdue_payments,
            'pending_payments': pending_payments,
            'paid_payments': paid_payments,
            'page_name': 'payment',
        }
        return request.render('HallWay_System.portal_my_payments', values)

    @http.route(['/my/attendance'], type='http', auth='user', website=True)
    def portal_my_attendance(self, **kw):
        student = request.env['hallway.student'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not student:
            return request.redirect('/my')

        # Get active enrollments
        enrollments = request.env['hallway.enrollment'].sudo().search([
            ('student_id', '=', student.id),
            ('state', 'in', ['enrolled', 'in_progress', 'completed'])
        ])

        values = {
            'enrollments': enrollments,
            'page_name': 'attendance',
        }
        return request.render('HallWay_System.portal_my_attendance', values)
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime, date
import json


class GameBookingController(http.Controller):

    @http.route(['/'], type='http', auth='public', website=True)
    def homepage(self, **kw):
        """عرض الصفحة الرئيسية"""
        return request.render('game_booking_management.game_booking_homepage')

    @http.route(['/game-booking'], type='http', auth='public', website=True, sitemap=True)
    def game_booking_page(self, **kw):
        """عرض صفحة حجز الألعاب"""
        games = request.env['game.game'].sudo().search([('active', '=', True)])

        values = {
            'games': games,
            'success': kw.get('success', False),
            'error': kw.get('error', False),
        }
        return request.render('game_booking_management.game_booking_page', values)

    @http.route(['/game-booking/get-schedules/<int:game_id>'], type='json', auth='public', website=True, csrf=False)
    def get_game_schedules(self, game_id, **kw):
        """الحصول على مواعيد اللعبة المتاحة"""
        today = date.today()
        schedules = request.env['game.schedule'].sudo().search([
            ('game_id', '=', game_id),
            ('date', '>=', today),
            ('available_slots', '>', 0)
        ], order='date asc, time asc')

        schedule_data = []
        for schedule in schedules:
            time_str = '{:02d}:{:02d}'.format(int(schedule.time), int((schedule.time % 1) * 60))
            schedule_data.append({
                'id': schedule.id,
                'date': schedule.date.strftime('%Y-%m-%d'),
                'date_display': schedule.date.strftime('%d/%m/%Y'),
                'time': time_str,
                'available_slots': schedule.available_slots,
                'max_players': schedule.max_players,
                'current_players': schedule.current_players,
            })

        return {'schedules': schedule_data}

    @http.route(['/game-booking/submit'], type='json', auth='public', website=True, csrf=False)
    def submit_booking(self, **post):
        """معالجة حجز جديد"""
        try:
            # التحقق من البيانات المطلوبة
            required_fields = ['player_name', 'mobile', 'schedule_id']
            for field in required_fields:
                if not post.get(field):
                    return {'success': False, 'error': f'حقل {field} مطلوب'}

            # إنشاء الحجز
            booking_vals = {
                'player_name': post.get('player_name'),
                'mobile': post.get('mobile'),
                'schedule_id': int(post.get('schedule_id')),
                'state': 'confirmed',
            }

            booking = request.env['game.booking'].sudo().create(booking_vals)

            # إرسال رسالة تأكيد (يمكن إضافة إرسال بريد إلكتروني أو رسالة SMS هنا)

            return {
                'success': True,
                'message': 'تم الحجز بنجاح!',
                'booking_id': booking.id,
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    @http.route(['/game-booking/check-availability/<int:schedule_id>'], type='json', auth='public', website=True)
    def check_availability(self, schedule_id, **kw):
        """التحقق من توفر الأماكن في موعد معين"""
        schedule = request.env['game.schedule'].sudo().browse(schedule_id)
        if schedule.exists():
            return {
                'available': schedule.available_slots > 0,
                'available_slots': schedule.available_slots,
                'message': f'متاح {schedule.available_slots} أماكن' if schedule.available_slots > 0 else 'عذراً، لا توجد أماكن متاحة'
            }
        return {'available': False, 'message': 'الموعد غير موجود'}
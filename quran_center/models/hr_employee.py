# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_quran_teacher = fields.Boolean(
        string='معلم قرآن',
        default=False,
        help='حدد هذا الخيار إذا كان الموظف معلم قرآن'
    )

    # حقول محسوبة لعرض الإحصائيات
    quran_class_count = fields.Integer(
        string='عدد الصفوف',
        compute='_compute_quran_stats'
    )

    quran_session_count = fields.Integer(
        string='عدد الجلسات',
        compute='_compute_quran_stats'
    )

    @api.depends('is_quran_teacher')
    def _compute_quran_stats(self):
        for employee in self:
            if employee.is_quran_teacher:
                # عد الصفوف
                classes = self.env['quran.class'].search([
                    '|',
                    ('teacher_id', '=', employee.id),
                    ('teacher_id2', '=', employee.id)
                ])
                employee.quran_class_count = len(classes)

                # عد الجلسات
                sessions = self.env['quran.session'].search([
                    '|',
                    ('teacher_id', '=', employee.id),
                    ('teacher_id2', '=', employee.id)
                ])
                employee.quran_session_count = len(sessions)
            else:
                employee.quran_class_count = 0
                employee.quran_session_count = 0

    def action_view_quran_classes(self):
        """عرض الصفوف الخاصة بالمعلم"""
        self.ensure_one()
        return {
            'name': 'صفوف المعلم',
            'view_mode': 'list,form',
            'res_model': 'quran.class',
            'type': 'ir.actions.act_window',
            'domain': [
                '|',
                ('teacher_id', '=', self.id),
                ('teacher_id2', '=', self.id)
            ],
        }

    def action_view_quran_sessions(self):
        """عرض الجلسات الخاصة بالمعلم"""
        self.ensure_one()
        return {
            'name': 'جلسات المعلم',
            'view_mode': 'list,form',
            'res_model': 'quran.session',
            'type': 'ir.actions.act_window',
            'domain': [
                '|',
                ('teacher_id', '=', self.id),
                ('teacher_id2', '=', self.id)
            ],
        }
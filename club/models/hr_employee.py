# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_coach = fields.Boolean(
        string='مدرب رياضي',
        default=False,
        help='حدد إذا كان هذا الموظف يعمل كمدرب رياضي'
    )

    # الألعاب التي يدربها كمدرب رئيسي
    main_sport_ids = fields.One2many(
        'club.sport',
        'coach_id',
        string='الألعاب (مدرب رئيسي)'
    )

    # الألعاب التي يدربها كمدرب مساعد
    assistant_sport_ids = fields.Many2many(
        'club.sport',
        'sport_assistant_coach_rel',
        'employee_id',
        'sport_id',
        string='الألعاب (مدرب مساعد)'
    )
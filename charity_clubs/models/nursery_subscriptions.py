from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CharityNurseryPlan(models.Model):
    _name = 'charity.nursery.plan'
    _description = 'خطط الحضانة'
    _rec_name = 'attendance_type'
    _order = 'attendance_type'

    department_id = fields.Many2one(
        'charity.departments',
        string='القسم',
        required=True,
        ondelete='cascade'
    )

    attendance_type = fields.Selection([
        ('1_monthly', 'شهري'),
        ('2_term1', 'الفصل الأول'),
        ('3_term2', 'الفصل الثاني'),
        ('4_term3', 'الفصل الثالث'),
        ('5_annual', 'سنوي')
    ], string='نظام الدوام', required=True)

    price_5_days = fields.Float(string='الرسوم لـ 5 أيام', digits=(10, 2))
    price_4_days = fields.Float(string='الرسوم لـ 4 أيام', digits=(10, 2))
    price_3_days = fields.Float(string='الرسوم لـ 3 أيام', digits=(10, 2))

    @api.constrains('department_id', 'attendance_type')
    def _check_unique_plan(self):
        for record in self:
            existing = self.search([
                ('department_id', '=', record.department_id.id),
                ('attendance_type', '=', record.attendance_type),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError('يوجد خطة بنفس نظام الدوام في هذا القسم!')
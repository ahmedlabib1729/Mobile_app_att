from odoo import models, fields

class WeekDays(models.Model):
    _name = 'week.days'
    _description = 'Week Days'

    name = fields.Char(string='Day', required=True)

    def _create_week_days(self):
        days = [
            'الاثنين',
            'الثلاثاء',
            'الأربعاء',
            'الخميس',
            'الجمعة',
            'السبت',
            'الأحد'
        ]

        # تحقق إذا كانت السجلات موجودة بالفعل
        existing_days = self.env['week.days'].search([])
        if not existing_days:
            for day in days:
                self.env['week.days'].create({'name': day})
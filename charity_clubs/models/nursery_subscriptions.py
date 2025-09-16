# تحديث ملف nursery_subscriptions.py
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

    # الحقول الجديدة للتحكم في إظهار خيارات الأيام
    show_5_days = fields.Boolean(
        string='إظهار خيار 5 أيام',
        default=True,
        help='حدد إذا كان خيار 5 أيام متاح للاختيار'
    )
    show_4_days = fields.Boolean(
        string='إظهار خيار 4 أيام',
        default=True,
        help='حدد إذا كان خيار 4 أيام متاح للاختيار'
    )
    show_3_days = fields.Boolean(
        string='إظهار خيار 3 أيام',
        default=True,
        help='حدد إذا كان خيار 3 أيام متاح للاختيار'
    )

    is_active = fields.Boolean(
        string='نشط',
        default=True,
        help='حدد إذا كانت هذه الخطة متاحة للتسجيل'
    )

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

    def get_display_name(self):
        """للحصول على اسم مقروء للخطة"""
        selection_dict = dict(self._fields['attendance_type'].selection)
        return selection_dict.get(self.attendance_type, '')

    def get_available_days_options(self):
        """إرجاع الخيارات المتاحة لعدد الأيام"""
        options = []
        if self.show_5_days and self.price_5_days > 0:
            options.append({'value': '5', 'label': '5 أيام', 'price': self.price_5_days})
        if self.show_4_days and self.price_4_days > 0:
            options.append({'value': '4', 'label': '4 أيام', 'price': self.price_4_days})
        if self.show_3_days and self.price_3_days > 0:
            options.append({'value': '3', 'label': '3 أيام', 'price': self.price_3_days})
        return options
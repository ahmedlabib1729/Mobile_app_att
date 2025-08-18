# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ClassSchedule(models.Model):
    _name = 'quran.class.schedule'
    _description = 'Class Schedule'
    _order = 'weekday, start_time'

    class_id = fields.Many2one(
        'quran.class',
        string='الصف',
        required=True,
        ondelete='cascade'
    )

    weekday = fields.Selection([
        ('0', 'الأحد'),
        ('1', 'الإثنين'),
        ('2', 'الثلاثاء'),
        ('3', 'الأربعاء'),
        ('4', 'الخميس'),
        ('5', 'الجمعة'),
        ('6', 'السبت')
    ], string='اليوم', required=True)

    start_time = fields.Float(
        string='وقت البداية',
        required=True,
        help='وقت البداية (24 ساعة)'
    )

    end_time = fields.Float(
        string='وقت النهاية',
        required=True,
        help='وقت النهاية (24 ساعة)'
    )

    active = fields.Boolean(
        string='نشط',
        default=True
    )

    @api.constrains('start_time', 'end_time')
    def _check_time_validity(self):
        for record in self:
            if record.start_time < 0 or record.start_time >= 24:
                raise ValidationError(_('وقت البداية يجب أن يكون بين 0 و 24'))
            if record.end_time < 0 or record.end_time >= 24:
                raise ValidationError(_('وقت النهاية يجب أن يكون بين 0 و 24'))
            if record.end_time <= record.start_time:
                raise ValidationError(_('وقت النهاية يجب أن يكون بعد وقت البداية'))

    @api.constrains('weekday', 'start_time', 'end_time', 'class_id')
    def _check_schedule_overlap(self):
        for record in self:
            domain = [
                ('class_id', '=', record.class_id.id),
                ('weekday', '=', record.weekday),
                ('id', '!=', record.id),
                ('active', '=', True)
            ]
            overlapping = self.search(domain)
            for schedule in overlapping:
                if (record.start_time < schedule.end_time and
                        record.end_time > schedule.start_time):
                    raise ValidationError(
                        _('يوجد تعارض في الجدول مع حصة أخرى في نفس اليوم والوقت')
                    )

    def name_get(self):
        result = []
        weekdays = dict(self._fields['weekday'].selection)
        for record in self:
            name = f"{weekdays.get(record.weekday, '')} ({record.start_time:.2f} - {record.end_time:.2f})"
            result.append((record.id, name))
        return result
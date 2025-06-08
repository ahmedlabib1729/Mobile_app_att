# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class GenerateSessionsWizard(models.TransientModel):
    _name = 'quran.class.generate.sessions.wizard'
    _description = 'Generate Sessions Wizard'

    class_id = fields.Many2one(
        'quran.class',
        string='الصف',
        required=True
    )

    existing_sessions_count = fields.Integer(
        string='عدد الجلسات الموجودة'
    )

    action = fields.Selection([
        ('keep', 'الاحتفاظ بالجلسات الموجودة وإضافة الجديدة'),
        ('regenerate', 'حذف الجلسات غير المكتملة وإعادة التوليد')
    ], string='الإجراء', default='keep', required=True)

    def action_confirm(self):
        self.ensure_one()

        if self.action == 'regenerate':
            self.class_id._generate_sessions(regenerate=True)
        else:
            # Generate only for dates without sessions
            self.class_id._generate_sessions(regenerate=False)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('نجح'),
                'message': _('تم توليد الجلسات بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }
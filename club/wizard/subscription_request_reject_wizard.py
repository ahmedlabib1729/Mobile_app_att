# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SubscriptionRequestRejectWizard(models.TransientModel):
    _name = 'subscription.request.reject.wizard'
    _description = 'معالج رفض طلب الاشتراك'

    request_id = fields.Many2one(
        'subscription.request',
        string='الطلب',
        required=True
    )

    rejection_reason = fields.Text(
        string='سبب الرفض',
        required=True
    )

    def action_confirm_reject(self):
        self.ensure_one()

        if not self.rejection_reason:
            raise UserError(_('يجب إدخال سبب الرفض.'))

        self.request_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason
        })

        # إرسال إشعار لولي الأمر (يمكن إضافته لاحقاً)

        return {'type': 'ir.actions.act_window_close'}
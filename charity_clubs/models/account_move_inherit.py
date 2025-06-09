# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    registration_id = fields.Many2one(
        'program.registration',
        string='تسجيل البرنامج',
        readonly=True,
        ondelete='restrict'
    )

    program_id = fields.Many2one(
        'club.program',
        string='البرنامج',
        related='registration_id.program_id',
        store=True
    )

    club_id = fields.Many2one(
        'charity.club',
        string='النادي',
        related='registration_id.club_id',
        store=True
    )

    def _compute_amount(self):
        """Override to trigger registration recomputation"""
        res = super()._compute_amount()
        # تحديث التسجيلات المرتبطة
        registrations = self.mapped('registration_id')
        if registrations:
            registrations._compute_payment_amounts()
            registrations._compute_payment_state()
        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        """عند ترحيل الدفعة، تحديث التسجيل"""
        res = super().action_post()

        # البحث عن التسجيلات المرتبطة
        for payment in self:
            invoices = payment.reconciled_invoice_ids
            registrations = invoices.mapped('registration_id')
            if registrations:
                registrations._compute_payment_amounts()
                registrations._compute_payment_state()

        return res
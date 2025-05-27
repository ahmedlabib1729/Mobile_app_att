# -*- coding: utf-8 -*-
from odoo import api, fields, models


class real_estate_setings(models.TransientModel):
    _inherit = 'res.config.settings'

    npv = fields.Float(string='NPV',config_parameter='itsys_real_estate.npv')

    reservation_hours = fields.Integer(string='Hours to release units reservation',config_parameter='itsys_real_estate.reservation_hours')
    penalty_percent = fields.Integer('Penalty Percentage', config_parameter='itsys_real_estate.penalty_percent')
    penalty_account = fields.Many2one('account.account','Late Payments Penalty Account',config_parameter='itsys_real_estate.penalty_account')
    discount_account = fields.Many2one('account.account','Discount Account',config_parameter='itsys_real_estate.discount_account')
    income_account = fields.Many2one('account.account','Income Account',config_parameter='itsys_real_estate.income_account')
    me_account = fields.Many2one('account.account','Managerial Expenses Account',config_parameter='itsys_real_estate.me_account')
    analytic_account = fields.Many2one('account.analytic.account','Analytic Account',config_parameter='itsys_real_estate.analytic_account')
    security_deposit_account = fields.Many2one('account.account','Security Deposit Account',config_parameter='itsys_real_estate.security_deposit_account')
    debit_penalty_account = fields.Many2one('account.account','Debit Penalty Account',config_parameter='itsys_real_estate.debit_penalty_account')
    credit_penalty_account = fields.Many2one('account.account','Credit Penalty Account',config_parameter='itsys_real_estate.credit_penalty_account')
    penalty_journal = fields.Many2one('account.journal','Penalty Journal',config_parameter='itsys_real_estate.penalty_journal')
    # x_handover_inst = fields.Boolean(string='Handover installment',config_parameter='itsys_real_estate.x_handover_inst')


class Config(models.TransientModel):
    _name = 'gmap.config'

    @api.model
    def get_key_api(self):
        return self.env['ir.config_parameter'].sudo().get_param('google_maps_api_key')

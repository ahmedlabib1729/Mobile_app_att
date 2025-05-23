# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta


class SaleOrderStatament(models.TransientModel):
    _name = 'sale.order.statement.wizard'
    _description = "SO customer statement wizard"

    report_period = fields.Selection(selection=[
        ("all", "All Time"),
        ("this_fin_year", "This Financial Year"),
        ("last_six_months", "Last Six Months"),
        ("last_year", "Last Year"),
        ("custom", "Custom"),

    ], required=True,)
    date_from = fields.Datetime(string="From Date")
    date_to = fields.Datetime(string="To Date")
    partner_ids = fields.Many2many('res.partner')
    other_invoices = fields.Boolean(default=True)
    unreconciled_payments = fields.Boolean(default=True)
    # إضافة حقل جديد للتصفية
    filter_by = fields.Selection([
        ('sale_order', 'Sale Order Date'),
        ('invoice', 'Invoice Date')
    ], string="Filter By", required=True, default='sale_order')

    def action_download_so_statement_report(self):

        data = {
            'partners': self.partner_ids.ids,
            'other_invoices': self.other_invoices,
            'unreconciled_payments': self.unreconciled_payments,
            'filter_by': self.filter_by,  # إضافة معلومات الفلتر الجديد
        }

        if self.report_period != 'all':
            if self.report_period == 'last_six_months':
                date_to = datetime.combine(
                    datetime.today(), datetime.max.time())
                date_from = date_to - relativedelta(months=6)

            elif self.report_period == 'this_fin_year':
                close_datetime = datetime(datetime.today().year, int(
                    self.env.company.fiscalyear_last_month), self.env.company.fiscalyear_last_day)
                date_to = datetime.combine(close_datetime, datetime.max.time())
                date_from = datetime.combine(
                    datetime(datetime.today().year, 1, 1), datetime.min.time())

            elif self.report_period == 'last_year':
                this_year = datetime.today().year
                date_from = datetime.combine(
                    datetime(this_year-1, 1, 1), datetime.min.time())
                date_to = datetime.combine(
                    datetime(this_year-1, 12, 31), datetime.max.time())

            else:  # report period = custom
                if self.date_from > self.date_to:
                    raise ValidationError(
                        _("From date must be before to date"))
                date_from = self.date_from
                date_to = self.date_to

            data['date_from'] = date_from
            data['date_to'] = date_to

        action = self.env.ref('customer_statement_sale_orders.action_so_customer_statement').report_action(self, data)
        action.update({'close_on_report_download': True})
        return action
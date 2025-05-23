# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    unreconciled_line_ids = fields.One2many(
        'account.move.line', compute='_compute_unreconciled_line_ids', readonly=False)

    def _get_unreconciled_domain(self):
        return [
            ('reconciled', '=', False),
            ('account_id.deprecated', '=', False),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('partner_id', 'in', self.ids),
            ('company_id', '=', self.env.company.id),
        ]

    @api.depends('invoice_ids')
    def _compute_unreconciled_line_ids(self):
        values = {
            line['partner_id'][0]: line['line_ids']
            for line in self.env['account.move.line'].read_group(
                domain=self._get_unreconciled_domain(),
                fields=['line_ids:array_agg(id)'],
                groupby=['partner_id']
            )
        }
        for partner in self:
            partner.unreconciled_line_ids = values.get(partner.id, False)

    def action_generate_so_invoice_report(self):
        return {
            'name': _("Generate SO Statement Report"),
            'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order.statement.wizard',
                    'target': 'new',
                    'context': {
                        'default_partner_ids': self.ids,
                        'default_report_period': 'all',
            },
        }

    def get_unreconciled_payments(self, dates=False):
        if dates:
            unreconciled_line_ids = self.unreconciled_line_ids.filtered(
                lambda aml: aml.move_type == 'entry' and dates[0] <= aml.date <= dates[1])
        else:
            unreconciled_line_ids = self.unreconciled_line_ids.filtered(
                lambda aml: aml.move_type == 'entry')
        return unreconciled_line_ids

    def get_invoices_not_sale(self, dates=False):
        if dates:
            invoices = self.invoice_ids.filtered(
                lambda inv: inv.state not in ('cancel', 'draft') and dates[0] <= inv.date <= dates[1] and inv.sale_order_count == 0 and inv.amount_residual_signed != 0)
        else:
            invoices = self.invoice_ids.filtered(
                lambda inv: inv.state not in ('cancel', 'draft') and inv.sale_order_count == 0 and inv.amount_residual_signed != 0)
        return invoices

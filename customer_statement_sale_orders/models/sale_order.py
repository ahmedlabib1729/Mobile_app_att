# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def calc_so_statement_amounts(self, sales, currency):
        total_invoiced_amount = 0
        invoice_paid_amount = 0
        remaining = 0
        sales_total_amount = 0
        for sale in sales:
            total_invoiced_amount += sum(sale.invoice_ids.filtered(lambda l: l.state not in ('cancel', 'draft')).mapped('amount_total_signed'))

            for invoice in sale.invoice_ids.filtered(lambda l: l.state not in ('cancel', 'draft')):
                payments = invoice.sudo().invoice_payments_widget and invoice.sudo(
                ).invoice_payments_widget['content'] or []
                for line in payments:
                    move_id = self.env['account.move'].browse(line['move_id'])
                    if move_id.payment_id or move_id.statement_line_id:
                        if invoice.move_type == 'out_refund':
                            invoice_paid_amount -= line['amount'] if sale.currency_id == currency else sale.convert_currency(line['amount'])
                        else:
                            invoice_paid_amount += line['amount'] if sale.currency_id == currency else sale.convert_currency(line['amount'])
            remaining += sum(sale.invoice_ids.filtered(
                lambda l: l.state not in ('cancel', 'draft')).mapped('amount_residual_signed'))

            if sale.currency_id == currency:
                sales_total_amount += sale.amount_total
            else:
                sales_total_amount += sale.convert_currency(sale.amount_total)
        amounts = {
            'total_invoiced_amount': total_invoiced_amount,
            'invoice_paid_amount': invoice_paid_amount,
            'remaining': remaining,
            'sales_total_amount': sales_total_amount,
        }
        return amounts

    def get_entry_payments(self, invoice):
        payments = invoice.sudo().invoice_payments_widget and invoice.sudo(
        ).invoice_payments_widget['content'] or []
        for line in payments:
            move_id = self.env['account.move'].browse(line['move_id'])
            if not (move_id.payment_id or move_id.statement_line_id):
                payments.remove(line)
        return payments

    def convert_currency(self, amount):
        date = self.date_order
        amount_converted = self.currency_id._convert(
            amount, self.env.company.currency_id, self.company_id, date)
        return amount_converted

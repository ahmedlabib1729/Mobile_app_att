# -*- coding: utf-8 -*-

from odoo import models, fields, api
from num2words import num2words


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_amount_in_words(self, amount):
        """Convert amount to words in English"""
        try:
            currency = self.currency_id
            if currency.name == 'BHD':
                # Bahraini Dinar
                dinars = int(amount)
                fils = int((amount - dinars) * 1000)

                if dinars > 0:
                    dinar_words = num2words(dinars, lang='en').title()
                else:
                    dinar_words = "Zero"

                if fils > 0:
                    fils_words = num2words(fils, lang='en').title()
                else:
                    fils_words = "Zero"

                return f"Bahraini Dinar {dinar_words} And {fils_words} Fils Only(BD {amount:.3f})"
            else:
                # Default currency handling
                return f"{currency.name} {num2words(amount, lang='en').title()} Only"
        except:
            return f"{amount:.2f}"

    def get_amount_total_words(self):
        """Get total amount in words"""
        return self._get_amount_in_words(self.amount_total)

    def get_vat_amount_words(self):
        """Get VAT amount in words"""
        return self._get_amount_in_words(self.amount_tax)

    def get_vat_summary(self):
        """Get VAT summary grouped by tax rate"""
        vat_summary = {}
        for line in self.invoice_line_ids:
            for tax in line.tax_ids:
                tax_key = f"VAT {tax.amount:.0f}%" if tax.amount > 0 else "VAT"
                if tax_key not in vat_summary:
                    vat_summary[tax_key] = {
                        'rate': f"VAT {tax.amount:.0f}%",
                        'assessable_value': 0.0,
                        'tax_amount': 0.0
                    }

                # Calculate tax amount for this line
                price_subtotal = line.price_subtotal
                tax_amount = price_subtotal * (tax.amount / 100)

                vat_summary[tax_key]['assessable_value'] += price_subtotal
                vat_summary[tax_key]['tax_amount'] += tax_amount

        return list(vat_summary.values())


class ReportInvoiceCustom(models.AbstractModel):
    _name = 'report.custom_invoice_report.report_invoice_custom_document'
    _description = 'Custom Invoice Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override to ensure docs are properly passed to the report template
        """
        docs = self.env['account.move'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'data': data,
        }
# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_note_number = fields.Char(
        string='Delivery Note No.',
        copy=False,
        readonly=True,
    )

    ref_number = fields.Char(
        string='Ref No.',
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generate delivery note number on creation"""
        for vals in vals_list:
            if vals.get('picking_type_id'):
                picking_type = self.env['stock.picking.type'].browse(vals['picking_type_id'])
                if picking_type.code == 'outgoing':
                    # Generate delivery note number if not provided
                    if not vals.get('delivery_note_number'):
                        sequence = self.env['ir.sequence'].next_by_code('stock.delivery.note') or '/'
                        vals['delivery_note_number'] = sequence
        return super(StockPicking, self).create(vals_list)

    def get_payment_terms(self):
        """Get payment terms from related sale order"""
        if self.sale_id and self.sale_id.payment_term_id:
            return self.sale_id.payment_term_id.name
        return ''


class ReportDeliveryNote(models.AbstractModel):
    _name = 'report.custom_invoice_report.report_delivery_note_document'
    _description = 'Delivery Note Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Override to ensure docs are properly passed to the report template
        """
        docs = self.env['stock.picking'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': docs,
            'data': data,
        }
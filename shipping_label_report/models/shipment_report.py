# -*- coding: utf-8 -*-
from odoo import models, api
import base64


class ShipmentOrderReport(models.AbstractModel):
    _name = 'report.shipping_label_report.report_shipment_label_document'
    _description = 'Shipment Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['shipment.order'].browse(docids)
        
        def get_barcode_image(value, barcode_type='Code128', width=350, height=50):
            """Generate barcode image as base64"""
            try:
                barcode_value = value or 'NO-CODE'
                barcode = self.env['ir.actions.report'].barcode(
                    barcode_type=barcode_type,
                    value=barcode_value,
                    width=width,
                    height=height,
                    humanreadable=0
                )
                return base64.b64encode(barcode).decode('utf-8')
            except Exception:
                return False

        return {
            'doc_ids': docids,
            'doc_model': 'shipment.order',
            'docs': docs,
            'get_barcode_image': get_barcode_image,
        }

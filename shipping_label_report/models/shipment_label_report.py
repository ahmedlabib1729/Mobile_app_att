# -*- coding: utf-8 -*-
from odoo import models, api
import base64
import io

try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False


class ShipmentLabelReport(models.AbstractModel):
    _name = 'report.shipping_label_report.report_shipment_label_document'
    _description = 'Shipment Label Report'

    def _get_barcode_image(self, value, width=350, height=50):
        """Generate barcode as base64 PNG image"""
        if not value or not BARCODE_AVAILABLE:
            return False
        
        try:
            # Clean the value - remove spaces
            clean_value = str(value).replace(' ', '').strip()
            if not clean_value:
                return False
            
            # Create Code128 barcode
            code128 = barcode.get_barcode_class('code128')
            
            # Create barcode with ImageWriter (uses Pillow)
            writer = ImageWriter()
            barcode_obj = code128(clean_value, writer=writer)
            
            # Save to buffer
            buffer = io.BytesIO()
            barcode_obj.write(buffer, {
                'module_width': 0.4,
                'module_height': 15.0,
                'quiet_zone': 2,
                'font_size': 10,
                'text_distance': 5,
                'write_text': False,  # We'll show text separately
            })
            
            # Get base64
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode('utf-8')
            
        except Exception as e:
            # Fallback: return False if barcode generation fails
            return False

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['shipment.order'].browse(docids)
        
        # Pre-generate barcodes for each document
        barcodes = {}
        for doc in docs:
            barcode_value = doc.tracking_number or doc.order_number or 'NOCODE'
            barcodes[doc.id] = self._get_barcode_image(barcode_value)
        
        return {
            'doc_ids': docids,
            'doc_model': 'shipment.order',
            'docs': docs,
            'barcodes': barcodes,
            'get_barcode': self._get_barcode_image,
        }

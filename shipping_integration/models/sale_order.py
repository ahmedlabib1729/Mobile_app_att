# shipping_integration/models/sale_order.py
from odoo import models, fields, api
import json


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shipping_provider_id = fields.Many2one('shipping.provider', string='Shipping Provider')
    shipping_tracking_number = fields.Char(string='Tracking Number')
    shipping_label = fields.Binary(string='Shipping Label')
    shipping_label_filename = fields.Char(string='Label Filename')
    shipping_request_ids = fields.One2many('shipping.request', 'sale_order_id', string='Shipping Requests')

    shipping_status = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent to Carrier'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], string='Shipping Status', default='not_sent')

    def action_create_shipment(self):
        """Open wizard to create shipment"""
        return {
            'name': 'Create Shipment',
            'type': 'ir.actions.act_window',
            'res_model': 'create.shipment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_provider_id': self.shipping_provider_id.id if self.shipping_provider_id else False,
            }
        }

    def action_print_label(self):
        """Print shipping label"""
        if not self.shipping_tracking_number or not self.shipping_provider_id:
            raise Exception("No tracking number available")

        try:
            # Get label from provider
            response = self.shipping_provider_id.send_request(
                'label',
                method='GET',
                tracking_number=self.shipping_tracking_number
            )

            # Handle response based on type
            if isinstance(response, dict) and 'pdf' in response:
                label_data = response['pdf']
            elif isinstance(response, str):
                label_data = response
            else:
                label_data = str(response)

            # Save label
            self.shipping_label = label_data
            self.shipping_label_filename = f"label_{self.shipping_tracking_number}.pdf"

            # Return action to download
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self._name}/{self.id}/shipping_label/{self.shipping_label_filename}?download=true',
                'target': 'self',
            }

        except Exception as e:
            raise Exception(f"Error getting label: {str(e)}")


class CreateShipmentWizard(models.TransientModel):
    _name = 'create.shipment.wizard'
    _description = 'Create Shipment Wizard'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True)
    provider_id = fields.Many2one('shipping.provider', string='Shipping Provider', required=True)

    # Additional fields that might be needed
    weight = fields.Float(string='Total Weight (kg)', default=1.0)
    pieces_count = fields.Integer(string='Number of Pieces', default=1)
    cod_amount = fields.Float(string='COD Amount', default=0.0)
    notes = fields.Text(string='Notes')

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Calculate default values from order"""
        if self.sale_order_id:
            # Calculate total weight from order lines if possible
            total_weight = 0
            for line in self.sale_order_id.order_line:
                if line.product_id and line.product_id.weight:
                    total_weight += line.product_id.weight * line.product_uom_qty

            if total_weight > 0:
                self.weight = total_weight

            # Set COD amount if payment term indicates COD
            if 'cod' in (self.sale_order_id.payment_term_id.name or '').lower():
                self.cod_amount = self.sale_order_id.amount_total

    def action_create_shipment(self):
        """Create shipment with selected provider"""
        self.ensure_one()

        try:
            # Create shipping request log
            request = self.env['shipping.request'].create({
                'sale_order_id': self.sale_order_id.id,
                'provider_id': self.provider_id.id,
                'request_type': 'create',
                'state': 'draft'
            })

            # Add dynamic values to context
            self.sale_order_id = self.sale_order_id.with_context(
                shipping_weight=self.weight,
                shipping_pieces_count=self.pieces_count,
                shipping_cod_amount=self.cod_amount,
                shipping_notes=self.notes
            )

            # Create shipment
            result = self.provider_id.create_shipment(self.sale_order_id)

            # Update request log
            request.write({
                'state': 'success',
                'tracking_number': result.get('tracking_number'),
                'response_data': json.dumps(result.get('response'), indent=2)
            })

            # Update sale order
            self.sale_order_id.write({
                'shipping_provider_id': self.provider_id.id,
                'shipping_tracking_number': result.get('tracking_number'),
                'shipping_status': 'sent'
            })

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Shipment created successfully. Tracking: {result.get("tracking_number")}',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            # Log error
            if 'request' in locals():
                request.write({
                    'state': 'error',
                    'error_message': str(e)
                })

            # Show error message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Error creating shipment: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }
# -*- coding: utf-8 -*-
import json
import base64
import requests
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    emirates_post_shipment_id = fields.Many2one(
        'emirates.post.shipment',
        string='Emirates Post Shipment',
        readonly=True,
        copy=False
    )

    emirates_post_awb = fields.Char(
        string='Emirates Post AWB',
        related='emirates_post_shipment_id.name',
        store=True
    )

    emirates_post_tracking_url = fields.Char(
        string='Emirates Post Tracking URL',
        related='emirates_post_shipment_id.tracking_url'
    )

    is_emirates_post_carrier = fields.Boolean(
        string='Is Emirates Post Carrier',
        compute='_compute_is_emirates_post_carrier'
    )

    def _compute_is_emirates_post_carrier(self):
        """Check if this picking uses Emirates Post carrier"""
        for picking in self:
            is_emirates = False

            # Check from sale order
            if picking.sale_id and hasattr(picking.sale_id, 'carrier_id') and picking.sale_id.carrier_id:
                carrier = picking.sale_id.carrier_id
                if carrier and hasattr(carrier, 'delivery_type'):
                    is_emirates = carrier.delivery_type == 'emirates_post'

            # If not found, check if any Emirates Post carrier exists in context
            if not is_emirates and self.env.context.get('default_carrier_id'):
                carrier = self.env['delivery.carrier'].browse(self.env.context.get('default_carrier_id'))
                if carrier.exists() and carrier.delivery_type == 'emirates_post':
                    is_emirates = True

            picking.is_emirates_post_carrier = is_emirates

    def get_carrier(self):
        """Get carrier from sale order or context"""
        self.ensure_one()

        # Try from sale order
        if self.sale_id and hasattr(self.sale_id, 'carrier_id') and self.sale_id.carrier_id:
            return self.sale_id.carrier_id

        # Try from context
        if self.env.context.get('default_carrier_id'):
            carrier = self.env['delivery.carrier'].browse(self.env.context.get('default_carrier_id'))
            if carrier.exists():
                return carrier

        # Last resort - find any Emirates Post carrier
        emirates_carrier = self.env['delivery.carrier'].search([
            ('delivery_type', '=', 'emirates_post')
        ], limit=1)

        return emirates_carrier

    def action_create_emirates_post_shipment(self):
        """Open wizard to create Emirates Post shipment"""
        self.ensure_one()

        # Get carrier
        carrier = self.get_carrier()
        if not carrier:
            raise UserError(
                _('No Emirates Post carrier configuration found. Please create one in Inventory > Configuration > Delivery > Shipping Methods.'))

        if self.emirates_post_shipment_id:
            raise UserError(_('Emirates Post shipment already created.'))

        # Open wizard
        return {
            'name': _('Create Emirates Post Shipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'emirates.post.shipment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_carrier_id': carrier.id,
            }
        }

    def action_track_emirates_post_shipment(self):
        """Track Emirates Post shipment"""
        self.ensure_one()

        if not self.emirates_post_tracking_url:
            raise UserError(_('No tracking URL available.'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.emirates_post_tracking_url,
            'target': '_blank',
        }

    def action_print_emirates_post_label(self):
        """Print Emirates Post shipping label"""
        self.ensure_one()

        if not self.emirates_post_shipment_id:
            raise UserError(_('No Emirates Post shipment found.'))

        carrier = self.get_carrier()
        if not carrier:
            raise UserError(_('No carrier configuration found!'))

        config = carrier.emirates_post_config_id
        if not config:
            raise UserError(_('No Emirates Post configuration found!'))

        # For test mode, return mock label
        if config.debug_mode:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Mode'),
                    'message': _('Label printing is disabled in test mode.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        try:
            headers = config._get_headers()
            url = f"{config.api_url.rstrip('/')}/booking/rest/PrintLabel"

            data = {
                "LabelRequest": {
                    "AWBNo": self.emirates_post_awb
                }
            }

            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                result = response.json()
                label_data = result.get('LabelResponse', {}).get('AWB')

                if label_data:
                    # Save label to shipment
                    self.emirates_post_shipment_id.write({
                        'label_data': label_data,
                        'label_filename': f'EP_{self.emirates_post_awb}.pdf'
                    })

                    # Return action to download
                    return {
                        'type': 'ir.actions.act_url',
                        'url': f'/web/content/{self.emirates_post_shipment_id._name}/{self.emirates_post_shipment_id.id}/label_data/{self.emirates_post_shipment_id.label_filename}?download=true',
                        'target': 'self',
                    }
                else:
                    raise UserError(_('No label data in response'))
            else:
                raise UserError(_('Failed to get label: %s') % response.text)

        except Exception as e:
            raise UserError(_('Failed to print label: %s') % str(e))
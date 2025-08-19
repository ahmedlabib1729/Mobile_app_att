# -*- coding: utf-8 -*-
import json
import base64
import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    iw_shipment_id = fields.Many2one(
        'iw.shipment',
        string='IW Shipment',
        readonly=True,
        copy=False
    )

    iw_consignment_ref = fields.Char(
        string='IW Consignment Ref',
        related='iw_shipment_id.name',
        store=True
    )

    iw_tracking_url = fields.Char(
        string='IW Tracking URL',
        related='iw_shipment_id.tracking_url'
    )

    iw_label_pdf = fields.Binary(
        string='IW Label',
        related='iw_shipment_id.label_pdf'
    )

    iw_label_filename = fields.Char(
        string='IW Label Filename',
        related='iw_shipment_id.label_filename'
    )

    # Simple field without compute
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier'
    )

    # Simple boolean field - we'll compute it manually
    is_iw_carrier = fields.Boolean(
        string='Is IW Carrier',
        store=True
    )

    # Related fields for display
    iw_service_type_id = fields.Selection(
        related='iw_shipment_id.service_type_id',
        string='IW Service Type',
        readonly=True
    )

    iw_load_type = fields.Selection(
        related='iw_shipment_id.load_type',
        string='IW Load Type',
        readonly=True
    )

    iw_num_pieces = fields.Integer(
        related='iw_shipment_id.num_pieces',
        string='IW Pieces',
        readonly=True
    )

    iw_weight = fields.Float(
        related='iw_shipment_id.weight',
        string='IW Weight',
        readonly=True
    )

    iw_shipment_state = fields.Selection(
        related='iw_shipment_id.state',
        string='IW Shipment State',
        readonly=True
    )

    iw_is_cod = fields.Boolean(
        related='iw_shipment_id.is_cod',
        string='IW COD',
        readonly=True
    )

    iw_cod_amount = fields.Float(
        related='iw_shipment_id.cod_amount',
        string='IW COD Amount',
        readonly=True
    )

    iw_cod_currency = fields.Many2one(
        related='iw_shipment_id.cod_currency',
        string='IW COD Currency',
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set carrier and is_iw_carrier"""
        pickings = super().create(vals_list)
        for picking in pickings:
            # Set carrier from sale order if not set
            if not picking.carrier_id and picking.sale_id and picking.sale_id.carrier_id:
                picking.carrier_id = picking.sale_id.carrier_id
            # Update is_iw_carrier
            picking.is_iw_carrier = bool(
                picking.carrier_id and
                picking.carrier_id.delivery_type == 'iw_express'
            )
        return pickings

    def write(self, vals):
        """Override write to update is_iw_carrier when needed"""
        res = super().write(vals)

        # If carrier_id or sale_id changed, update is_iw_carrier
        if 'carrier_id' in vals or 'sale_id' in vals:
            for picking in self:
                # Update carrier from sale if needed
                if not picking.carrier_id and picking.sale_id and picking.sale_id.carrier_id:
                    picking.carrier_id = picking.sale_id.carrier_id

                # Update is_iw_carrier
                picking.is_iw_carrier = bool(
                    picking.carrier_id and
                    picking.carrier_id.delivery_type == 'iw_express'
                )

        return res

    def action_create_iw_shipment(self):
        """Open wizard to create IW shipment"""
        self.ensure_one()

        # Update carrier if needed
        if not self.carrier_id and self.sale_id and self.sale_id.carrier_id:
            self.carrier_id = self.sale_id.carrier_id
            self.is_iw_carrier = bool(
                self.carrier_id and
                self.carrier_id.delivery_type == 'iw_express'
            )

        if not self.carrier_id or self.carrier_id.delivery_type != 'iw_express':
            raise UserError(_('Please select IW Express as delivery method in the related sale order.'))

        if self.iw_shipment_id:
            raise UserError(_('IW Express shipment already created for this delivery.'))

        # Validate all products have default_code (required for pieces_detail)
        missing_code_products = []
        for move in self.move_ids:
            if not move.product_id.default_code:
                missing_code_products.append(move.product_id.name)

        if missing_code_products:
            raise UserError(_(
                'Cannot create IW Express shipment!\n\n'
                'The following products need Internal Reference:\n%s\n\n'
                'Please add Internal Reference to these products first.'
            ) % '\n'.join(['• ' + name for name in missing_code_products]))

        # Open Wizard
        return {
            'name': _('Create IW Express Shipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'iw.shipment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_carrier_id': self.carrier_id.id,
            }
        }

    def action_print_iw_label(self):
        """Print IW shipping label"""
        self.ensure_one()

        if not self.iw_shipment_id:
            raise UserError(_('No IW Express shipment found.'))

        if not self.iw_label_pdf:
            # Get label from API
            self._get_iw_label()

        if self.iw_label_pdf:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{self.iw_shipment_id._name}/{self.iw_shipment_id.id}/label_pdf/IW_Label_{self.iw_consignment_ref}.pdf?download=true',
                'target': 'self',
            }
        else:
            raise UserError(_('No label available for this shipment.'))

    def action_track_iw_shipment(self):
        """Track IW shipment"""
        self.ensure_one()

        if not self.iw_tracking_url:
            raise UserError(_('No tracking URL available.'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.iw_tracking_url,
            'target': '_blank',
        }

    def action_cancel_iw_shipment(self):
        """Cancel IW shipment"""
        self.ensure_one()

        if not self.iw_shipment_id:
            raise UserError(_('No IW Express shipment to cancel.'))

        if self.iw_shipment_id.state not in ['draft', 'confirmed']:
            raise UserError(_('Cannot cancel shipment in current state.'))

        # TODO: Call IW API to cancel if they provide such endpoint

        # Update status
        self.iw_shipment_id.state = 'cancelled'

        # Add note in chatter
        self.message_post(
            body=_('IW Express shipment cancelled. Reference: %s') % self.iw_consignment_ref,
            subject=_('Shipment Cancelled')
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('IW Express shipment cancelled successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_iw_label(self):
        """Get label from IW API"""
        self.ensure_one()

        if not self.iw_shipment_id or not self.carrier_id:
            return

        config = self.carrier_id.get_iw_config(self.partner_id)

        try:
            # Call label API
            label_content = config._make_api_request(
                f'{self.iw_consignment_ref}/shippingLabel',
                method='GET',
                is_label=True
            )

            if label_content:
                # Save PDF
                self.iw_shipment_id.write({
                    'label_pdf': base64.b64encode(label_content),
                    'label_filename': f'IW_Label_{self.iw_consignment_ref}.pdf'
                })

                self.message_post(
                    body=_('Shipping label retrieved successfully'),
                    subject=_('Label Retrieved')
                )

        except Exception as e:
            raise UserError(_('Failed to get label: %s') % str(e))

    @api.model
    def _cron_update_iw_tracking(self):
        """Cron job to update IW tracking status"""
        pickings = self.search([
            ('iw_shipment_id', '!=', False),
            ('iw_shipment_id.state', 'not in', ['delivered', 'cancelled']),
            ('state', '=', 'done')
        ])

        for picking in pickings:
            try:
                picking.iw_shipment_id.action_update_tracking()
            except Exception as e:
                _logger.error(f"Failed to update tracking for picking {picking.name}: {str(e)}")
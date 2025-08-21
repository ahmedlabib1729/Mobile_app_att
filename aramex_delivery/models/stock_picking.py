# -*- coding: utf-8 -*-
import json
import base64
import logging
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ========== Aramex Shipment Fields ==========
    aramex_shipment_id = fields.Many2one(
        'aramex.shipment',
        string='Aramex Shipment',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )

    aramex_awb = fields.Char(
        string='Aramex AWB',
        related='aramex_shipment_id.awb_number',
        store=True,
        readonly=True
    )

    aramex_tracking_url = fields.Char(
        string='Aramex Tracking URL',
        related='aramex_shipment_id.tracking_url',
        readonly=True
    )

    aramex_label_pdf = fields.Binary(
        string='Aramex Label',
        related='aramex_shipment_id.label_pdf',
        readonly=True
    )

    aramex_label_filename = fields.Char(
        string='Aramex Label Filename',
        related='aramex_shipment_id.label_filename',
        readonly=True
    )

    aramex_shipment_state = fields.Selection(
        string='Aramex Status',
        related='aramex_shipment_id.state',
        store=True,
        readonly=True
    )

    # ========== Carrier Information ==========
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier',
        compute='_compute_carrier_id',
        store=True
    )

    is_aramex_carrier = fields.Boolean(
        compute='_compute_is_aramex_carrier',
        store=True,
        string='Is Aramex Delivery'
    )

    # ========== Additional Aramex Info ==========
    aramex_pickup_guid = fields.Char(
        string='Aramex Pickup GUID',
        related='aramex_shipment_id.pickup_guid',
        readonly=True
    )

    aramex_foreign_hawb = fields.Char(
        string='Foreign HAWB',
        help='Foreign House Air Waybill if applicable'
    )

    aramex_cod_amount = fields.Float(
        string='COD Amount',
        compute='_compute_cod_amount',
        store=True
    )

    aramex_service_type = fields.Char(
        string='Aramex Service',
        compute='_compute_aramex_service_info',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_currency_id',
        store=True
    )

    # ========== Compute Methods ==========
    @api.depends('sale_id.currency_id', 'company_id.currency_id')
    def _compute_currency_id(self):
        """Get currency from sale order or company"""
        for picking in self:
            if picking.sale_id and picking.sale_id.currency_id:
                picking.currency_id = picking.sale_id.currency_id
            else:
                picking.currency_id = picking.company_id.currency_id or self.env.company.currency_id

    @api.depends('sale_id.carrier_id', 'carrier_id')
    def _compute_carrier_id(self):
        """Get carrier from sale order or direct assignment"""
        for picking in self:
            if not picking.carrier_id and picking.sale_id and picking.sale_id.carrier_id:
                picking.carrier_id = picking.sale_id.carrier_id

    @api.depends('carrier_id', 'carrier_id.delivery_type')
    def _compute_is_aramex_carrier(self):
        """Check if carrier is Aramex"""
        for picking in self:
            picking.is_aramex_carrier = (
                    picking.carrier_id and
                    picking.carrier_id.delivery_type == 'aramex'
            )

    @api.depends('sale_id.is_cod_payment', 'sale_id.cod_amount')
    def _compute_cod_amount(self):
        """Get COD amount from sale order"""
        for picking in self:
            if picking.sale_id and picking.sale_id.is_cod_payment:
                picking.aramex_cod_amount = picking.sale_id.cod_amount
            else:
                picking.aramex_cod_amount = 0.0

    @api.depends('aramex_shipment_id.product_group', 'aramex_shipment_id.product_type')
    def _compute_aramex_service_info(self):
        """Compute service type description"""
        for picking in self:
            if picking.aramex_shipment_id:
                shipment = picking.aramex_shipment_id
                service_info = []

                if shipment.product_group:
                    service_info.append(
                        dict(shipment._fields['product_group'].selection).get(shipment.product_group, ''))
                if shipment.product_type:
                    service_info.append(dict(shipment._fields['product_type'].selection).get(shipment.product_type, ''))

                picking.aramex_service_type = ' - '.join(service_info) if service_info else False
            else:
                picking.aramex_service_type = False

    # ========== Action Methods ==========
    def action_view_aramex_shipment(self):
        """View Aramex shipment details"""
        self.ensure_one()

        if not self.aramex_shipment_id:
            raise UserError(_('No Aramex shipment found.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Aramex Shipment'),
            'res_model': 'aramex.shipment',
            'res_id': self.aramex_shipment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_aramex_shipment(self):
        """Open wizard to create Aramex shipment"""
        self.ensure_one()

        # Validations
        if not self.carrier_id or self.carrier_id.delivery_type != 'aramex':
            raise UserError(_('Please select Aramex as delivery method in the related sale order.'))

        if self.aramex_shipment_id:
            raise UserError(_(
                'Aramex shipment already created!\n'
                'AWB Number: %s'
            ) % self.aramex_awb)

        if self.state not in ['assigned', 'done']:
            raise UserError(_('Delivery order must be ready or done to create shipment.'))

        # Check for missing product SKUs
        missing_sku_products = []
        for move in self.move_ids:
            if not move.product_id.default_code:
                missing_sku_products.append(move.product_id.name)

        if missing_sku_products:
            raise UserError(_(
                'Cannot create Aramex shipment!\n\n'
                'The following products need Internal Reference (SKU):\n%(products)s\n\n'
                'Please update product information first.',
                products='\n'.join(['• ' + name for name in missing_sku_products])
            ))

        # Check partner information
        partner = self.partner_id
        warnings = []

        if not partner.country_id:
            warnings.append(_('Customer country'))
        if not partner.city:
            warnings.append(_('Customer city'))
        if not (partner.phone or partner.mobile):
            warnings.append(_('Customer phone number'))
        if not partner.street:
            warnings.append(_('Customer street address'))

        if warnings:
            raise UserError(_(
                'Missing customer information:\n%(missing)s\n\n'
                'Please complete customer details before creating shipment.',
                missing='\n'.join(['• ' + w for w in warnings])
            ))

        # Open wizard
        return {
            'name': _('Create Aramex Shipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'aramex.shipment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_carrier_id': self.carrier_id.id,
            }
        }

    def action_print_aramex_label(self):
        """Print Aramex shipping label"""
        self.ensure_one()

        if not self.aramex_shipment_id:
            raise UserError(_('No Aramex shipment found.'))

        if not self.aramex_label_pdf:
            # Try to get label from API
            self._get_aramex_label()

        if not self.aramex_label_pdf:
            raise UserError(_(
                'No label available for this shipment.\n'
                'AWB: %s'
            ) % self.aramex_awb)

        # Return action to download PDF
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.aramex_shipment_id._name}/{self.aramex_shipment_id.id}/label_pdf/{self.aramex_label_filename}?download=true',
            'target': 'self',
        }

    def action_track_aramex_shipment(self):
        """Track Aramex shipment"""
        self.ensure_one()

        if not self.aramex_tracking_url:
            raise UserError(_('No tracking URL available.'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.aramex_tracking_url,
            'target': '_blank',
        }

    def action_cancel_aramex_shipment(self):
        """Cancel Aramex shipment"""
        self.ensure_one()

        if not self.aramex_shipment_id:
            raise UserError(_('No Aramex shipment to cancel.'))

        if self.aramex_shipment_id.state in ['delivered', 'cancelled']:
            raise UserError(_(
                'Cannot cancel shipment in %(state)s state.',
                state=self.aramex_shipment_id.state
            ))

        # Get Aramex config
        config = self.carrier_id.get_aramex_config(self.partner_id)

        try:
            # TODO: Implement API call to cancel shipment
            # For now, just update status
            self.aramex_shipment_id.write({
                'state': 'cancelled',
                'error_message': f'Cancelled by user {self.env.user.name} on {fields.Datetime.now()}'
            })

            # Add note to chatter
            self.message_post(
                body=_(
                    '<b>Aramex shipment cancelled</b><br/>'
                    'AWB: %(awb)s<br/>'
                    'Cancelled by: %(user)s',
                    awb=self.aramex_awb,
                    user=self.env.user.name
                ),
                subject=_('Shipment Cancelled')
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Aramex shipment cancelled successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_(
                'Failed to cancel shipment:\n%(error)s',
                error=str(e)
            ))

    def action_schedule_aramex_pickup(self):
        """Schedule pickup for Aramex shipment"""
        self.ensure_one()

        if not self.aramex_shipment_id:
            raise UserError(_('Please create Aramex shipment first.'))

        if self.aramex_pickup_guid:
            raise UserError(_(
                'Pickup already scheduled!\n'
                'Pickup GUID: %s'
            ) % self.aramex_pickup_guid)

        # Open pickup wizard
        return {
            'name': _('Schedule Aramex Pickup'),
            'type': 'ir.actions.act_window',
            'res_model': 'aramex.pickup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shipment_id': self.aramex_shipment_id.id,
                'default_picking_id': self.id,
            }
        }

    def action_update_aramex_tracking(self):
        """Manually update tracking information"""
        self.ensure_one()

        if not self.aramex_shipment_id:
            raise UserError(_('No Aramex shipment found.'))

        try:
            self._update_aramex_tracking()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        'Tracking updated successfully.\n'
                        'Status: %(status)s',
                        status=self.aramex_shipment_state
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_(
                'Failed to update tracking:\n%(error)s',
                error=str(e)
            ))

    # ========== Helper Methods ==========
    def _get_aramex_label(self):
        """Get label from Aramex API"""
        self.ensure_one()

        if not self.aramex_shipment_id or not self.carrier_id:
            return

        config = self.carrier_id.get_aramex_config(self.partner_id)

        try:
            # TODO: Implement API call to get label
            # For now, log the attempt
            _logger.info(f"Attempting to get Aramex label for AWB: {self.aramex_awb}")

            # This would be the actual API call
            # response = config._call_aramex_api('PrintLabel', {
            #     'ShipmentNumber': self.aramex_awb,
            #     'LabelInfo': {
            #         'ReportID': self.carrier_id.aramex_label_report_id,
            #         'ReportType': self.carrier_id.aramex_label_report_type,
            #     }
            # })

        except Exception as e:
            _logger.error(f"Failed to get Aramex label: {str(e)}")
            self.message_post(
                body=_('Failed to retrieve label: %s') % str(e),
                subject=_('Label Error')
            )

    def _update_aramex_tracking(self):
        """Update tracking information from Aramex API"""
        self.ensure_one()

        if not self.aramex_shipment_id or not self.carrier_id:
            return

        config = self.carrier_id.get_aramex_config(self.partner_id)

        try:
            # TODO: Implement API call for tracking
            _logger.info(f"Updating tracking for AWB: {self.aramex_awb}")

            # Update last tracking time
            self.aramex_shipment_id.write({
                'last_tracking_update': fields.Datetime.now(),
                'tracking_notes': f'Tracking updated at {fields.Datetime.now()}'
            })

        except Exception as e:
            _logger.error(f"Failed to update tracking: {str(e)}")
            raise

    @api.model
    def _cron_update_aramex_tracking(self):
        """Cron job to update Aramex tracking status"""
        # Find pickings with active Aramex shipments
        pickings = self.search([
            ('aramex_shipment_id', '!=', False),
            ('aramex_shipment_id.state', 'not in', ['delivered', 'cancelled', 'returned']),
            ('state', '=', 'done'),
            '|',
            ('aramex_shipment_id.last_tracking_update', '=', False),
            ('aramex_shipment_id.last_tracking_update', '<', fields.Datetime.now() - timedelta(hours=4))
        ], limit=50)  # Process 50 at a time

        for picking in pickings:
            try:
                picking._update_aramex_tracking()
                self.env.cr.commit()  # Commit after each successful update
            except Exception as e:
                _logger.error(
                    f"Failed to update tracking for picking {picking.name}, "
                    f"AWB {picking.aramex_awb}: {str(e)}"
                )
                self.env.cr.rollback()  # Rollback on error

    # ========== Override Methods ==========
    def button_validate(self):
        """Override to check Aramex requirements before validation"""
        # Check if any picking needs Aramex shipment
        aramex_pickings = self.filtered('is_aramex_carrier')

        for picking in aramex_pickings:
            if not picking.aramex_shipment_id and picking.picking_type_code == 'outgoing':
                # Show warning but don't block
                picking.message_post(
                    body=_(
                        '<b>Warning:</b> Delivery validated without creating Aramex shipment.<br/>'
                        'You can still create the shipment using the "Create Aramex Shipment" button.'
                    ),
                    subject=_('Aramex Shipment Pending'),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment'
                )

        return super().button_validate()

    def action_done(self):
        """Override to update Aramex shipment state"""
        res = super().action_done()

        # Update Aramex shipment state if exists
        for picking in self:
            if picking.aramex_shipment_id and picking.aramex_shipment_id.state == 'confirmed':
                picking.aramex_shipment_id.write({
                    'state': 'picked_up',
                    'pickup_date': fields.Date.today()
                })

        return res
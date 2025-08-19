# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class IWShipment(models.Model):
    _name = 'iw.shipment'
    _description = 'IW Express Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Consignment Reference',
        readonly=True,
        copy=False,
        tracking=True,
        help='IW Express consignment reference number'
    )

    customer_reference_number = fields.Char(
        string='Customer Reference',
        required=True,
        tracking=True,
        help='Your reference number for this shipment'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('pickup_scheduled', 'Pickup Scheduled'),
        ('pickup_completed', 'Pickup Completed'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('attempted', 'Attempted'),
        ('rto', 'Return to Origin'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ], string='Status', default='draft', tracking=True)

    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        ondelete='cascade'
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        related='picking_id.sale_id',
        store=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='picking_id.partner_id',
        store=True
    )

    # Service Details
    service_type_id = fields.Selection([
        ('PREMIUM', 'Premium'),
        ('INTERNATIONAL', 'International'),
        ('DELIVERY', 'Delivery'),
    ], string='Service Type', required=True, tracking=True)

    consignment_type = fields.Selection([
        ('FORWARD', 'Forward'),
        ('REVERSE', 'Reverse'),
    ], string='Consignment Type', default='FORWARD', required=True)

    load_type = fields.Selection([
        ('DOCUMENT', 'Document'),
        ('NON-DOCUMENT', 'Non-Document'),
    ], string='Load Type', default='NON-DOCUMENT', required=True)

    # Package Information
    num_pieces = fields.Integer(string='Number of Pieces', default=1)
    weight = fields.Float(string='Total Weight', required=True)
    weight_unit = fields.Char(string='Weight Unit', default='KG')

    dimension_unit = fields.Char(string='Dimension Unit', default='CM')
    length = fields.Float(string='Length')
    width = fields.Float(string='Width')
    height = fields.Float(string='Height')

    declared_value = fields.Float(string='Declared Value')
    description = fields.Text(string='Description', required=True)

    # COD Details
    is_cod = fields.Boolean(string='Cash on Delivery')
    cod_amount = fields.Float(string='COD Amount')
    cod_currency = fields.Many2one('res.currency', string='COD Currency')
    cod_collection_mode = fields.Selection([
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('dd', 'Demand Draft'),
    ], string='COD Collection Mode', default='cash')
    cod_favor_of = fields.Char(string='COD In Favor Of')

    # Additional Information
    notes = fields.Text(string='Notes')
    is_risk_surcharge_applicable = fields.Boolean(string='Insurance Required')

    # Civil IDs
    customer_civil_id = fields.Char(string='Customer Civil ID')
    receiver_civil_id = fields.Char(string='Receiver Civil ID')

    # References
    reference_number = fields.Char(string='Reference Number')
    inco_terms = fields.Char(string='Inco Terms')

    # Tracking
    tracking_url = fields.Char(
        string='Tracking URL',
        compute='_compute_tracking_url',
        store=True
    )

    # Documents
    label_pdf = fields.Binary(string='Shipping Label', attachment=True)
    label_filename = fields.Char(string='Label Filename')

    # Dates
    pickup_date = fields.Date(string='Pickup Date')
    delivery_date = fields.Datetime(string='Delivery Date')

    # Tracking Events
    tracking_history = fields.Text(string='Tracking History')
    last_update_date = fields.Datetime(string='Last Update')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    @api.depends('name')
    def _compute_tracking_url(self):
        for record in self:
            if record.name:
                # You can customize this URL based on IW Express tracking page
                record.tracking_url = f"https://www.emiratespost.ae/all-services/track-a-package/step-two?q={record.name}"
            else:
                record.tracking_url = False

    def action_cancel(self):
        """Cancel the shipment"""
        for shipment in self:
            if shipment.state in ['delivered', 'cancelled']:
                raise UserError(_('Cannot cancel delivered or already cancelled shipment.'))

            # TODO: Call IW API to cancel shipment if needed

            shipment.state = 'cancelled'
            shipment.message_post(
                body=_('Shipment cancelled'),
                subject=_('Shipment Cancelled')
            )

    def action_update_tracking(self):
        """Update tracking information from IW API"""
        for shipment in self:
            if not shipment.name:
                continue

            try:
                # Get the configuration
                config = shipment.picking_id.carrier_id.get_iw_config(shipment.partner_id)

                # Call tracking API
                response = config._make_api_request(
                    f'tracking/{shipment.name}/shipment',
                    method='GET'
                )

                # Update shipment status based on response
                # TODO: Map IW status to our status
                if response.get('status'):
                    # This is a simplified example - adjust based on actual API response
                    status_mapping = {
                        'DELIVERED': 'delivered',
                        'IN_TRANSIT': 'in_transit',
                        'OUT_FOR_DELIVERY': 'out_for_delivery',
                        'PICKUP_COMPLETED': 'pickup_completed',
                        'ATTEMPTED': 'attempted',
                        'RTO': 'rto',
                        'ON_HOLD': 'on_hold',
                    }

                    new_state = status_mapping.get(response['status'], shipment.state)
                    if new_state != shipment.state:
                        shipment.state = new_state
                        shipment.last_update_date = fields.Datetime.now()

                        # Update tracking history
                        history = shipment.tracking_history or ''
                        history += f"\n{fields.Datetime.now()}: Status changed to {new_state}"
                        if response.get('remarks'):
                            history += f" - {response['remarks']}"
                        shipment.tracking_history = history

                        shipment.message_post(
                            body=_('Tracking updated: %s') % new_state,
                            subject=_('Tracking Update')
                        )

                    # Update delivery date if delivered
                    if new_state == 'delivered' and response.get('delivery_date'):
                        shipment.delivery_date = response['delivery_date']

            except Exception as e:
                _logger.error(f"Failed to update tracking for {shipment.name}: {str(e)}")
                shipment.message_post(
                    body=_('Failed to update tracking: %s') % str(e),
                    subject=_('Tracking Error')
                )
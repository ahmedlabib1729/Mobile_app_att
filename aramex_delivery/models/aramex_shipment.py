# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)


class AramexShipment(models.Model):
    _name = 'aramex.shipment'
    _description = 'Aramex Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'awb_number'

    # ========== Shipment Identification ==========
    awb_number = fields.Char(
        string='AWB Number',
        readonly=True,
        copy=False,
        tracking=True,
        help='Aramex Air Waybill Number'
    )

    # References (3 reference fields as per Aramex API)
    reference1 = fields.Char(
        string='Reference 1',
        required=True,
        tracking=True,
        help='Primary reference for this shipment'
    )

    reference2 = fields.Char(
        string='Reference 2',
        tracking=True,
        help='Secondary reference'
    )

    reference3 = fields.Char(
        string='Reference 3',
        tracking=True,
        help='Additional reference'
    )

    # ========== Related Records ==========
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        ondelete='cascade',
        index=True
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        related='picking_id.sale_id',
        store=True,
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='picking_id.partner_id',
        store=True,
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # ========== Shipment Details ==========
    product_group = fields.Selection([
        ('EXP', 'Express'),
        ('DOM', 'Domestic'),
    ], string='Product Group', required=True, default='DOM', tracking=True)

    product_type = fields.Selection([
        ('OND', 'Overnight Document'),
        ('ONP', 'Overnight Parcel'),
        ('PDX', 'Priority Document Express'),
        ('PPX', 'Priority Parcel Express'),
        ('DDX', 'Deferred Document Express'),
        ('DPX', 'Deferred Parcel Express'),
        ('GDX', 'Ground Document Express'),
        ('GPX', 'Ground Parcel Express'),
        ('EPX', 'Economy Parcel Express'),
    ], string='Product Type', required=True, default='ONP', tracking=True)

    payment_type = fields.Selection([
        ('P', 'Prepaid'),
        ('C', 'Collect'),
        ('3', 'Third Party'),
    ], string='Payment Type', default='P', required=True)

    payment_options = fields.Char(
        string='Payment Options',
        help='Payment options string as per Aramex requirements'
    )

    delivery_date = fields.Datetime(
        string='Delivery Date',
        help='Actual delivery date and time'
    )
    services = fields.Char(
        string='Services',
        help='Additional services codes (comma separated)'
    )

    # ========== Package Information ==========
    number_of_pieces = fields.Integer(
        string='Number of Pieces',
        default=1,
        required=True,
        tracking=True
    )

    actual_weight = fields.Float(
        string='Actual Weight (KG)',
        required=True,
        tracking=True
    )

    chargeable_weight = fields.Float(
        string='Chargeable Weight (KG)',
        help='Calculated by Aramex based on dimensions and actual weight'
    )

    # Dimensions
    length = fields.Float(string='Length (cm)')
    width = fields.Float(string='Width (cm)')
    height = fields.Float(string='Height (cm)')

    description_of_goods = fields.Char(
        string='Description of Goods',
        required=True,
        default='General Goods'
    )

    goods_origin_country = fields.Many2one(
        'res.country',
        string='Goods Origin Country',
        help='Country where goods originated from'
    )

    # ========== Financial Information ==========
    # Customs Value
    customs_value_amount = fields.Float(
        string='Customs Value',
        help='Value of goods for customs purposes'
    )

    customs_value_currency = fields.Many2one(
        'res.currency',
        string='Customs Currency'
    )

    # Cash on Delivery
    cod_amount = fields.Float(
        string='COD Amount',
        tracking=True
    )

    cod_currency = fields.Many2one(
        'res.currency',
        string='COD Currency'
    )

    # Insurance
    insurance_amount = fields.Float(string='Insurance Amount')
    insurance_currency = fields.Many2one('res.currency', string='Insurance Currency')

    # Additional Amounts
    cash_additional_amount = fields.Float(string='Cash Additional Amount')
    cash_additional_amount_description = fields.Char(string='Cash Additional Description')

    collect_amount = fields.Float(string='Collect Amount')

    # ========== Pickup Information ==========
    pickup_guid = fields.Char(
        string='Pickup GUID',
        help='Unique identifier for pickup request'
    )

    pickup_id = fields.Char(
        string='Pickup ID',
        help='Pickup reference number'
    )

    pickup_date = fields.Date(string='Pickup Date')

    foreign_hawb = fields.Char(
        string='Foreign HAWB',
        help='Foreign House Air Waybill'
    )

    # ========== Tracking & Status ==========
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ], string='Status', default='draft', tracking=True, index=True)

    tracking_url = fields.Char(
        string='Tracking URL',
        compute='_compute_tracking_url',
        store=True
    )

    last_tracking_update = fields.Datetime(
        string='Last Tracking Update',
        help='Last time tracking information was updated'
    )

    tracking_notes = fields.Text(
        string='Tracking Notes',
        help='Latest tracking information'
    )

    # ========== Documents ==========
    label_pdf = fields.Binary(
        string='Shipping Label',
        attachment=True
    )

    label_filename = fields.Char(
        string='Label Filename',
        default='Aramex_Label.pdf'
    )

    label_url = fields.Char(
        string='Label URL',
        help='URL to download the label from Aramex'
    )

    # ========== Shipper Information ==========
    shipper_name = fields.Char(string='Shipper Name')
    shipper_company = fields.Char(string='Shipper Company')
    shipper_phone = fields.Char(string='Shipper Phone')
    shipper_address = fields.Text(string='Shipper Address')
    shipper_country_code = fields.Char(string='Shipper Country Code')

    # ========== Consignee Information ==========
    consignee_name = fields.Char(string='Consignee Name')
    consignee_company = fields.Char(string='Consignee Company')
    consignee_phone = fields.Char(string='Consignee Phone')
    consignee_address = fields.Text(string='Consignee Address')
    consignee_country_code = fields.Char(string='Consignee Country Code')

    # ========== Additional Information ==========
    comments = fields.Text(string='Comments')

    accounting_instructions = fields.Text(
        string='Accounting Instructions',
        help='Special accounting instructions for this shipment'
    )

    operations_instructions = fields.Text(
        string='Operations Instructions',
        help='Special operations instructions for this shipment'
    )

    # Error handling
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help='Last error message from Aramex API'
    )

    # API Response
    api_response = fields.Text(
        string='API Response',
        readonly=True,
        help='Last API response for debugging'
    )

    # ========== Computed Fields ==========
    @api.depends('awb_number')
    def _compute_tracking_url(self):
        """Compute Aramex tracking URL"""
        for record in self:
            if record.awb_number:
                # Aramex tracking URL format
                record.tracking_url = f"https://www.aramex.com/track/results?ShipmentNumber={record.awb_number}"
            else:
                record.tracking_url = False

    # ========== Display Name ==========
    def name_get(self):
        """Improve shipment display name"""
        result = []
        for shipment in self:
            if shipment.awb_number:
                name = f"{shipment.awb_number} - {shipment.partner_id.name if shipment.partner_id else 'N/A'}"
            else:
                name = f"Draft - {shipment.reference1}"
            result.append((shipment.id, name))
        return result

    # ========== Business Logic ==========
    def action_confirm(self):
        """Confirm the shipment"""
        for shipment in self:
            if shipment.state != 'draft':
                raise UserError(_('Only draft shipments can be confirmed.'))
            shipment.state = 'confirmed'

    def action_cancel(self):
        """Cancel the shipment"""
        for shipment in self:
            if shipment.state in ['delivered', 'cancelled']:
                raise UserError(_('Cannot cancel delivered or already cancelled shipments.'))
            shipment.state = 'cancelled'
            shipment.message_post(
                body=_('Shipment cancelled'),
                subject=_('Shipment Cancellation')
            )

    def action_print_label(self):
        """Download and print shipping label"""
        self.ensure_one()

        if not self.label_pdf:
            raise UserError(_('No label available for this shipment. Please generate the label first.'))

        # Return action to download the PDF
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/label_pdf/{self.label_filename}?download=true',
            'target': 'self',
        }

    def action_track_shipment(self):
        """Open tracking URL in new window"""
        self.ensure_one()

        if not self.tracking_url:
            raise UserError(_('No tracking URL available.'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.tracking_url,
            'target': '_blank',
        }

    def update_tracking_status(self):
        """Update tracking status from Aramex API"""
        # This method will be called by cron job or manually
        # Implementation will depend on Aramex tracking API
        for shipment in self:
            if shipment.awb_number and shipment.state not in ['delivered', 'cancelled']:
                try:
                    # TODO: Call Aramex tracking API
                    # tracking_info = self._get_tracking_info(shipment.awb_number)
                    # shipment.write({
                    #     'state': tracking_info.get('status'),
                    #     'tracking_notes': tracking_info.get('notes'),
                    #     'last_tracking_update': fields.Datetime.now()
                    # })
                    pass
                except Exception as e:
                    _logger.error(f"Failed to update tracking for AWB {shipment.awb_number}: {str(e)}")

    # ========== Helper Methods ==========
    @api.model
    def _prepare_shipper_data(self, picking):
        """Prepare shipper data from picking"""
        warehouse = picking.picking_type_id.warehouse_id
        company = picking.company_id

        if warehouse and warehouse.partner_id:
            shipper = warehouse.partner_id
        else:
            shipper = company.partner_id

        return {
            'shipper_name': shipper.name,
            'shipper_company': company.name,
            'shipper_phone': shipper.phone or shipper.mobile,
            'shipper_address': shipper._display_address(),
            'shipper_country_code': shipper.country_id.code if shipper.country_id else '',
        }

    @api.model
    def _prepare_consignee_data(self, partner):
        """Prepare consignee data from partner"""
        return {
            'consignee_name': partner.name,
            'consignee_company': partner.parent_id.name if partner.parent_id else '',
            'consignee_phone': partner.phone or partner.mobile,
            'consignee_address': partner._display_address(),
            'consignee_country_code': partner.country_id.code if partner.country_id else '',
        }

    # ========== Constraints ==========
    _sql_constraints = [
        ('awb_number_unique', 'UNIQUE(awb_number)', 'AWB Number must be unique!'),
    ]
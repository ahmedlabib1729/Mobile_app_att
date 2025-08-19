# -*- coding: utf-8 -*-
import json
import base64
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AramexShipmentWizard(models.TransientModel):
    _name = 'aramex.shipment.wizard'
    _description = 'Create Aramex Shipment Wizard'

    # ========== Basic Information ==========
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        required=True,
        readonly=True
    )

    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier',
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='picking_id.partner_id',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='picking_id.company_id',
        readonly=True
    )

    # ========== Configuration ==========
    aramex_config_id = fields.Many2one(
        'aramex.config',
        string='Aramex Configuration',
        required=True,
        help='Select the appropriate Aramex configuration'
    )

    # ========== References ==========
    reference1 = fields.Char(
        string='Reference 1',
        required=True,
        help='Primary reference for this shipment'
    )

    reference2 = fields.Char(
        string='Reference 2',
        help='Secondary reference (e.g., PO number)'
    )

    reference3 = fields.Char(
        string='Reference 3',
        help='Additional reference'
    )

    # ========== Service Details ==========
    product_group = fields.Selection([
        ('EXP', 'Express'),
        ('DOM', 'Domestic'),
    ], string='Product Group', required=True)

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
    ], string='Product Type', required=True)

    payment_type = fields.Selection([
        ('P', 'Prepaid'),
        ('C', 'Collect'),
        ('3', 'Third Party'),
    ], string='Payment Type', required=True, default='P')

    payment_options = fields.Char(
        string='Payment Options',
        help='e.g., ASCC, ARCC'
    )

    services = fields.Char(
        string='Additional Services',
        help='Comma-separated service codes (e.g., CODS,SIGN,CHST)'
    )

    # ========== Package Information ==========
    number_of_pieces = fields.Integer(
        string='Number of Pieces',
        default=1,
        required=True
    )

    actual_weight = fields.Float(
        string='Total Weight (KG)',
        required=True,
        compute='_compute_weight',
        store=True,
        readonly=False
    )

    weight_unit = fields.Selection([
        ('KG', 'Kilograms'),
        ('LB', 'Pounds'),
    ], string='Weight Unit', default='KG', required=True)

    # Dimensions
    length = fields.Float(string='Length (cm)')
    width = fields.Float(string='Width (cm)')
    height = fields.Float(string='Height (cm)')
    dimensions_unit = fields.Selection([
        ('CM', 'Centimeters'),
        ('M', 'Meters'),
    ], string='Dimensions Unit', default='CM')

    # ========== Shipment Details ==========
    description_of_goods = fields.Char(
        string='Description of Goods',
        required=True,
        default='General Merchandise'
    )

    goods_origin_country = fields.Many2one(
        'res.country',
        string='Goods Origin Country',
        help='Country where goods originated from'
    )

    comments = fields.Text(
        string='Comments',
        help='Any special instructions or comments'
    )

    foreign_hawb = fields.Char(
        string='Foreign HAWB',
        help='Foreign House Air Waybill if applicable'
    )

    # ========== Financial Information ==========
    # COD
    is_cod = fields.Boolean(
        string='Cash on Delivery',
        compute='_compute_cod_info',
        store=True,
        readonly=False
    )

    cod_amount = fields.Float(
        string='COD Amount',
        required=False
    )

    cod_currency_id = fields.Many2one(
        'res.currency',
        string='COD Currency',
        compute='_compute_cod_info',
        store=True,
        readonly=False
    )

    # Customs
    customs_value_amount = fields.Float(
        string='Customs Value',
        help='Value of goods for customs purposes'
    )

    customs_value_currency = fields.Many2one(
        'res.currency',
        string='Customs Currency'
    )

    # Insurance
    insurance_amount = fields.Float(string='Insurance Amount')
    insurance_currency = fields.Many2one('res.currency', string='Insurance Currency')

    # ========== Pickup Information ==========
    shipping_datetime = fields.Datetime(
        string='Shipping Date/Time',
        required=True,
        default=lambda self: fields.Datetime.now()
    )

    due_date = fields.Datetime(
        string='Due Date',
        help='Expected delivery date'
    )

    create_pickup = fields.Boolean(
        string='Create Pickup Request',
        default=True
    )

    pickup_location = fields.Char(
        string='Pickup Location',
        help='Specific pickup location instructions'
    )

    # ========== Shipper Information ==========
    use_warehouse_address = fields.Boolean(
        string='Use Warehouse Address',
        default=True
    )

    shipper_name = fields.Char(string='Shipper Name')
    shipper_company = fields.Char(string='Shipper Company')
    shipper_phone = fields.Char(string='Shipper Phone')
    shipper_email = fields.Char(string='Shipper Email')
    shipper_address = fields.Text(string='Shipper Address')

    # ========== Attachments ==========
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        help='Attach documents like invoice, packing list, etc.'
    )

    # ========== Multi-Package Support ==========
    use_multi_package = fields.Boolean(
        string='Multiple Packages',
        help='Check if shipment has multiple packages with different weights'
    )

    package_line_ids = fields.One2many(
        'aramex.shipment.wizard.package',
        'wizard_id',
        string='Package Details'
    )

    # ========== Compute Methods ==========
    @api.depends('picking_id', 'picking_id.sale_id', 'picking_id.sale_id.is_cod_payment')
    def _compute_cod_info(self):
        """Compute COD information from sale order"""
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sale_id:
                sale = wizard.picking_id.sale_id
                wizard.is_cod = sale.is_cod_payment
                if sale.is_cod_payment:
                    wizard.cod_amount = sale.cod_amount
                    wizard.cod_currency_id = sale.currency_id
                else:
                    wizard.cod_amount = 0.0
                    wizard.cod_currency_id = sale.currency_id
            else:
                wizard.is_cod = False
                wizard.cod_amount = 0.0
                wizard.cod_currency_id = wizard.company_id.currency_id

    @api.depends('picking_id', 'picking_id.move_ids.product_uom_qty',
                 'picking_id.move_ids.product_id.weight')
    def _compute_weight(self):
        """Calculate total weight from picking"""
        for wizard in self:
            if wizard.picking_id:
                total_weight = 0.0
                for move in wizard.picking_id.move_ids:
                    qty = move.quantity_done if wizard.picking_id.state == 'done' else move.product_uom_qty
                    weight = move.product_id.weight or 0.0
                    total_weight += weight * qty
                wizard.actual_weight = total_weight or 1.0
            else:
                wizard.actual_weight = 1.0

    # ========== Onchange Methods ==========
    @api.onchange('carrier_id', 'partner_id')
    def _onchange_carrier_partner(self):
        """Set default configuration based on carrier and partner"""
        if self.carrier_id and self.carrier_id.delivery_type == 'aramex':
            try:
                config = self.carrier_id.get_aramex_config(self.partner_id)
                if config:
                    self.aramex_config_id = config
                    self.product_group = config.default_product_group or self.carrier_id.aramex_default_product_group
                    self.product_type = config.default_product_type or self.carrier_id.aramex_default_product_type
                    self.payment_type = config.default_payment_type or self.carrier_id.aramex_default_payment_type
                    self.services = config.default_services or self.carrier_id.aramex_default_service_codes
            except:
                pass

    @api.onchange('use_multi_package')
    def _onchange_use_multi_package(self):
        """Initialize package lines when enabling multi-package"""
        if self.use_multi_package and not self.package_line_ids:
            self.package_line_ids = [(0, 0, {
                'sequence': 1,
                'weight': self.actual_weight,
                'description': 'Package 1',
            })]

    @api.onchange('use_warehouse_address')
    def _onchange_use_warehouse_address(self):
        """Update shipper information based on selection"""
        if self.use_warehouse_address and self.picking_id:
            warehouse = self.picking_id.picking_type_id.warehouse_id
            if warehouse and warehouse.partner_id:
                partner = warehouse.partner_id
                self.shipper_name = partner.name
                self.shipper_company = self.company_id.name
                self.shipper_phone = partner.phone or partner.mobile
                self.shipper_email = partner.email
                self.shipper_address = partner._display_address()
        else:
            # Clear shipper fields for manual entry
            self.shipper_name = False
            self.shipper_company = False
            self.shipper_phone = False
            self.shipper_email = False
            self.shipper_address = False

    # ========== Default Methods ==========
    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super().default_get(fields_list)

        if self.env.context.get('default_picking_id'):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])

            # Set references
            res['reference1'] = picking.name
            if picking.origin:
                res['reference2'] = picking.origin
            if picking.sale_id:
                res['reference3'] = picking.sale_id.client_order_ref or ''

            # Set carrier and config
            if picking.carrier_id:
                res['carrier_id'] = picking.carrier_id.id
                if picking.carrier_id.delivery_type == 'aramex':
                    try:
                        config = picking.carrier_id.get_aramex_config(picking.partner_id)
                        if config:
                            res['aramex_config_id'] = config.id
                            res[
                                'product_group'] = config.default_product_group or picking.carrier_id.aramex_default_product_group
                            res[
                                'product_type'] = config.default_product_type or picking.carrier_id.aramex_default_product_type
                            res[
                                'payment_type'] = config.default_payment_type or picking.carrier_id.aramex_default_payment_type
                            res['services'] = config.default_services or picking.carrier_id.aramex_default_service_codes
                    except:
                        pass

            # Set goods origin country
            if self.env.company.country_id:
                res['goods_origin_country'] = self.env.company.country_id.id

            # Set currency defaults
            if picking.sale_id:
                res['cod_currency_id'] = picking.sale_id.currency_id.id
                res['customs_value_currency'] = picking.sale_id.currency_id.id
                res['insurance_currency'] = picking.sale_id.currency_id.id
            else:
                currency_id = self.env.company.currency_id.id
                res['cod_currency_id'] = currency_id
                res['customs_value_currency'] = currency_id
                res['insurance_currency'] = currency_id

        return res

    # ========== Validation Methods ==========
    def _validate_shipment_data(self):
        """Validate shipment data before creation"""
        self.ensure_one()

        errors = []

        # Check weight
        if self.actual_weight <= 0:
            errors.append(_('Weight must be greater than 0'))

        # Check COD
        if self.is_cod and self.cod_amount <= 0:
            errors.append(_('COD amount must be greater than 0'))

        # Check partner data
        partner = self.partner_id
        if not partner.country_id:
            errors.append(_('Customer country is required'))
        if not partner.city:
            errors.append(_('Customer city is required'))
        if not (partner.phone or partner.mobile):
            errors.append(_('Customer phone number is required'))
        if not partner.street:
            errors.append(_('Customer street address is required'))

        # Check products
        for move in self.picking_id.move_ids:
            if not move.product_id.default_code:
                errors.append(_('Product %s is missing Internal Reference (SKU)') % move.product_id.name)

        # Check shipper data
        if not self.use_warehouse_address:
            if not self.shipper_name:
                errors.append(_('Shipper name is required'))
            if not self.shipper_phone:
                errors.append(_('Shipper phone is required'))
            if not self.shipper_address:
                errors.append(_('Shipper address is required'))

        if errors:
            raise ValidationError('\n'.join(errors))

    # ========== Action Methods ==========
    def action_create_shipment(self):
        """Create Aramex shipment"""
        self.ensure_one()

        # Validate data
        self._validate_shipment_data()

        # Prepare shipment data
        shipment_data = self._prepare_shipment_data()

        try:
            # Call Aramex API
            response = self.aramex_config_id._call_aramex_api('CreateShipments', shipment_data)

            # Process response
            return self._process_shipment_response(response)

        except Exception as e:
            _logger.error(f"Aramex shipment creation failed: {str(e)}")
            raise UserError(_(
                'Failed to create Aramex shipment:\n%s'
            ) % str(e))

    def _prepare_shipment_data(self):
        """Prepare data for Aramex API"""
        self.ensure_one()

        picking = self.picking_id
        partner = self.partner_id

        # Prepare shipment items
        items = []
        for i in range(self.number_of_pieces):
            item = {
                'PackageType': 'Box',
                'Quantity': 1,
                'Weight': {
                    'Unit': self.weight_unit,
                    'Value': self.actual_weight / self.number_of_pieces
                },
                'Comments': f'Package {i + 1} of {self.number_of_pieces}',
                'Reference': self.reference1
            }
            items.append(item)

        # Prepare address data
        shipper_address = self._prepare_shipper_address()
        consignee_address = self._prepare_consignee_address()

        # Main shipment data
        shipment = {
            'Reference1': self.reference1,
            'Reference2': self.reference2 or '',
            'Reference3': self.reference3 or '',
            'Shipper': shipper_address,
            'Consignee': consignee_address,
            'ShippingDateTime': self.shipping_datetime.strftime('%Y-%m-%dT%H:%M:%S'),
            'Comments': self.comments or '',
            'PickupLocation': self.pickup_location or '',
            'Details': {
                'Dimensions': {
                    'Length': self.length or 0,
                    'Width': self.width or 0,
                    'Height': self.height or 0,
                    'Unit': self.dimensions_unit
                },
                'ActualWeight': {
                    'Unit': self.weight_unit,
                    'Value': self.actual_weight
                },
                'DescriptionOfGoods': self.description_of_goods,
                'GoodsOriginCountry': self.goods_origin_country.code if self.goods_origin_country else '',
                'NumberOfPieces': self.number_of_pieces,
                'ProductGroup': self.product_group,
                'ProductType': self.product_type,
                'PaymentType': self.payment_type,
                'PaymentOptions': self.payment_options or '',
                'Services': self.services or '',
                'Items': items
            }
        }

        # Add financial information
        if self.is_cod:
            shipment['Details']['CashOnDeliveryAmount'] = {
                'CurrencyCode': self.cod_currency_id.name,
                'Value': self.cod_amount
            }

        if self.customs_value_amount:
            shipment['Details']['CustomsValueAmount'] = {
                'CurrencyCode': self.customs_value_currency.name,
                'Value': self.customs_value_amount
            }

        if self.insurance_amount:
            shipment['Details']['InsuranceAmount'] = {
                'CurrencyCode': self.insurance_currency.name,
                'Value': self.insurance_amount
            }

        # Add due date if specified
        if self.due_date:
            shipment['DueDate'] = self.due_date.strftime('%Y-%m-%dT%H:%M:%S')

        # Add foreign HAWB if specified
        if self.foreign_hawb:
            shipment['ForeignHAWB'] = self.foreign_hawb

        # Full request data - هنا التعديل المهم
        data = {
            'ShipmentCreationRequest': {
                'ClientInfo': self.aramex_config_id._prepare_client_info(),
                'Transaction': self.aramex_config_id._prepare_transaction(
                    self.reference1,
                    f'Odoo Picking: {picking.name}'
                ),
                'Shipments': [shipment],
                'LabelInfo': {
                    'ReportID': self.carrier_id.aramex_label_report_id,
                    'ReportType': self.carrier_id.aramex_label_report_type
                }
            }
        }

        return data

    def _prepare_shipper_address(self):
        """Prepare shipper address data"""
        if self.use_warehouse_address:
            warehouse = self.picking_id.picking_type_id.warehouse_id
            if warehouse and warehouse.partner_id:
                partner = warehouse.partner_id
            else:
                partner = self.company_id.partner_id

            shipper_name = warehouse.name if warehouse else self.company_id.name
            shipper_company = self.company_id.name
            shipper_phone = partner.phone or partner.mobile or ''
            shipper_email = partner.email or ''
            shipper_address = partner
        else:
            shipper_name = self.shipper_name
            shipper_company = self.shipper_company or ''
            shipper_phone = self.shipper_phone
            shipper_email = self.shipper_email or ''
            shipper_address = None

        data = {
            'PartyAddress': {
                'Line1': shipper_address.street or self.shipper_address if shipper_address else self.shipper_address,
                'Line2': shipper_address.street2 or '' if shipper_address else '',
                'Line3': '',
                'City': shipper_address.city or '' if shipper_address else '',
                'StateOrProvinceCode': shipper_address.state_id.code or '' if shipper_address and shipper_address.state_id else '',
                'PostCode': shipper_address.zip or '' if shipper_address else '',
                'CountryCode': shipper_address.country_id.code if shipper_address and shipper_address.country_id else self.company_id.country_id.code
            },
            'Contact': {
                'PersonName': shipper_name,
                'CompanyName': shipper_company,
                'PhoneNumber1': shipper_phone,
                'PhoneNumber1Ext': '',
                'PhoneNumber2': '',
                'PhoneNumber2Ext': '',
                'FaxNumber': '',
                'CellPhone': shipper_phone,
                'EmailAddress': shipper_email,
                'Type': ''
            }
        }

        return data

    def _prepare_consignee_address(self):
        """Prepare consignee address data"""
        partner = self.partner_id

        data = {
            'PartyAddress': {
                'Line1': partner.street or '',
                'Line2': partner.street2 or '',
                'Line3': '',
                'City': partner.city or '',
                'StateOrProvinceCode': partner.state_id.code or '' if partner.state_id else '',
                'PostCode': partner.zip or '',
                'CountryCode': partner.country_id.code
            },
            'Contact': {
                'PersonName': partner.name,
                'CompanyName': partner.parent_id.name if partner.parent_id else '',
                'PhoneNumber1': partner.phone or partner.mobile or '',
                'PhoneNumber1Ext': '',
                'PhoneNumber2': partner.mobile if partner.phone else '',
                'PhoneNumber2Ext': '',
                'FaxNumber': '',
                'CellPhone': partner.mobile or partner.phone or '',
                'EmailAddress': partner.email or '',
                'Type': ''
            }
        }

        # Add reference if exists
        if partner.ref:
            data['Reference1'] = partner.ref

        return data

    def _process_shipment_response(self, response):
        """Process API response and create shipment record"""
        self.ensure_one()

        # Check for errors
        has_errors = response.get('HasErrors', False)
        if has_errors:
            notifications = response.get('Notifications', [])
            if isinstance(notifications, dict):
                notifications = [notifications]

            error_messages = []
            for notif in notifications:
                code = notif.get('Code', '')
                message = notif.get('Message', '')
                error_messages.append(f"{code}: {message}")

            raise UserError(_(
                'Aramex API returned errors:\n%s'
            ) % '\n'.join(error_messages))

        # Get shipment data
        shipments = response.get('Shipments', [])
        if not shipments:
            raise UserError(_('No shipment data in response!'))

        if isinstance(shipments, dict):
            shipments = [shipments]

        shipment_data = shipments[0]  # We only create one shipment

        # Get AWB number
        awb_number = shipment_data.get('ID')
        if not awb_number:
            raise UserError(_('No AWB number received from Aramex!'))

        # Create shipment record
        shipment_vals = {
            'awb_number': awb_number,
            'reference1': self.reference1,
            'reference2': self.reference2,
            'reference3': self.reference3,
            'picking_id': self.picking_id.id,
            'product_group': self.product_group,
            'product_type': self.product_type,
            'payment_type': self.payment_type,
            'payment_options': self.payment_options,
            'services': self.services,
            'number_of_pieces': self.number_of_pieces,
            'actual_weight': self.actual_weight,
            'description_of_goods': self.description_of_goods,
            'goods_origin_country': self.goods_origin_country.id if self.goods_origin_country else False,
            'cod_amount': self.cod_amount if self.is_cod else 0,
            'cod_currency': self.cod_currency_id.id if self.is_cod else False,
            'customs_value_amount': self.customs_value_amount,
            'customs_value_currency': self.customs_value_currency.id if self.customs_value_currency else False,
            'insurance_amount': self.insurance_amount,
            'insurance_currency': self.insurance_currency.id if self.insurance_currency else False,
            'foreign_hawb': self.foreign_hawb,
            'comments': self.comments,
            'pickup_date': self.shipping_datetime.date(),
            'state': 'confirmed',
            'company_id': self.company_id.id,
        }

        # Add shipper/consignee info
        shipment_vals.update(self.picking_id.aramex_shipment_id._prepare_shipper_data(self.picking_id))
        shipment_vals.update(self.picking_id.aramex_shipment_id._prepare_consignee_data(self.partner_id))

        # Get label if available
        if shipment_data.get('ShipmentLabel'):
            label_data = shipment_data['ShipmentLabel']
            if label_data.get('LabelFileContents'):
                shipment_vals['label_pdf'] = label_data['LabelFileContents']
                shipment_vals['label_filename'] = f'Aramex_Label_{awb_number}.pdf'
            if label_data.get('LabelURL'):
                shipment_vals['label_url'] = label_data['LabelURL']

        # Create shipment
        aramex_shipment = self.env['aramex.shipment'].create(shipment_vals)

        # Link to picking
        self.picking_id.aramex_shipment_id = aramex_shipment

        # Add note to picking
        note_body = _(
            '<b>Aramex shipment created successfully!</b><br/>'
            '<b>AWB Number:</b> %(awb)s<br/>'
            '<b>Service:</b> %(service)s<br/>'
            '<b>Weight:</b> %(weight).2f %(unit)s<br/>'
            '<b>Pieces:</b> %(pieces)d',
            awb=awb_number,
            service=dict(self._fields['product_type'].selection).get(self.product_type),
            weight=self.actual_weight,
            unit=self.weight_unit,
            pieces=self.number_of_pieces
        )

        if self.is_cod:
            note_body += _(
                '<br/><b>COD Amount:</b> %(amount).2f %(currency)s',
                amount=self.cod_amount,
                currency=self.cod_currency_id.name
            )

        self.picking_id.message_post(
            body=note_body,
            subject=_('Aramex Shipment Created'),
            message_type='notification'
        )

        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    'Aramex shipment created successfully!\n'
                    'AWB Number: %(awb)s',
                    awb=awb_number
                ),
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }


class AramexShipmentWizardPackage(models.TransientModel):
    _name = 'aramex.shipment.wizard.package'
    _description = 'Aramex Shipment Package Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'aramex.shipment.wizard',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    description = fields.Char(
        string='Description',
        required=True
    )

    weight = fields.Float(
        string='Weight (KG)',
        required=True,
        default=1.0
    )

    length = fields.Float(string='Length (cm)')
    width = fields.Float(string='Width (cm)')
    height = fields.Float(string='Height (cm)')
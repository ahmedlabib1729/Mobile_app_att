# -*- coding: utf-8 -*-
import json
import base64
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class IWShipmentWizard(models.TransientModel):
    _name = 'iw.shipment.wizard'
    _description = 'IW Express Shipment Creation Wizard'

    # Basic Information
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

    # Reference
    customer_reference_number = fields.Char(
        string='Customer Reference',
        required=True,
        help='Your reference number for this shipment'
    )

    reference_number = fields.Char(
        string='Reference Number',
        help='Additional reference number'
    )

    inco_terms = fields.Char(
        string='Inco Terms',
        help='International Commercial Terms'
    )

    # Service Details
    service_type_id = fields.Selection([
        ('PREMIUM', 'Premium'),
        ('INTERNATIONAL', 'International'),
        ('DELIVERY', 'Delivery'),
    ], string='Service Type', required=True)

    consignment_type = fields.Selection([
        ('FORWARD', 'Forward'),
        ('REVERSE', 'Reverse'),
    ], string='Consignment Type', default='FORWARD', required=True)

    load_type = fields.Selection([
        ('DOCUMENT', 'Document'),
        ('NON-DOCUMENT', 'Non-Document'),
    ], string='Load Type', required=True)

    # Package Information
    num_pieces = fields.Integer(
        string='Number of Pieces',
        default=1,
        required=True
    )

    weight = fields.Float(
        string='Total Weight',
        required=True,
        compute='_compute_weight',
        store=True,
        readonly=False
    )

    weight_unit = fields.Selection([
        ('KG', 'Kilogram'),
        ('GM', 'Gram'),
        ('LB', 'Pound'),
        ('OZ', 'Ounce'),
    ], string='Weight Unit', default='KG', required=True)

    dimension_unit = fields.Selection([
        ('CM', 'Centimeter'),
        ('IN', 'Inch'),
        ('MM', 'Millimeter'),
        ('M', 'Meter'),
    ], string='Dimension Unit', default='CM', required=True)

    # Overall dimensions (for single piece)
    length = fields.Float(string='Length' , default='23.50')
    width = fields.Float(string='Width' , default='22.00')
    height = fields.Float(string='Height' , default='10.00')

    # Value and Description
    declared_value = fields.Float(
        string='Declared Value',
        required=True,
        compute='_compute_declared_value',
        store=True,
        readonly=False
    )

    description = fields.Text(
        string='Description',
        required=True,
        default='General Merchandise'
    )

    notes = fields.Text(string='Notes')

    # COD
    is_cod = fields.Boolean(string='Cash on Delivery')

    cod_amount = fields.Float(
        string='COD Amount',
        required=False
    )

    cod_currency_id = fields.Many2one(
        'res.currency',
        string='COD Currency',
        compute='_compute_cod_currency',
        store=True,
        readonly=False
    )

    cod_collection_mode = fields.Selection([
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('dd', 'Demand Draft'),
    ], string='COD Collection Mode', default='cash')

    cod_favor_of = fields.Char(string='COD In Favor Of')

    # Insurance
    is_risk_surcharge_applicable = fields.Boolean(
        string='Insurance Required',
        default=False
    )

    # Civil IDs
    customer_civil_id = fields.Char(string='Customer Civil ID')
    receiver_civil_id = fields.Char(string='Receiver Civil ID')

    # Multi-piece support
    piece_line_ids = fields.One2many(
        'iw.shipment.wizard.piece',
        'wizard_id',
        string='Pieces Detail'
    )

    use_multi_piece = fields.Boolean(string='Multiple Pieces')

    @api.depends('picking_id', 'picking_id.sale_id', 'picking_id.sale_id.currency_id')
    def _compute_cod_currency(self):
        """Calculate currency from Sale Order"""
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sale_id:
                wizard.cod_currency_id = wizard.picking_id.sale_id.currency_id
            else:
                wizard.cod_currency_id = wizard.env.company.currency_id

    @api.depends('picking_id', 'picking_id.sale_id')
    def _compute_declared_value(self):
        """Calculate declared value from sale order"""
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sale_id:
                wizard.declared_value = wizard.picking_id.sale_id.amount_total
            else:
                wizard.declared_value = 0.0

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super().default_get(fields_list)

        if self.env.context.get('default_picking_id'):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])

            # Set reference to SALE ORDER name instead of picking
            if picking.sale_id:
                res['customer_reference_number'] = picking.sale_id.name
            else:
                # Fallback to picking name if no sale order
                res['customer_reference_number'] = picking.name

            # Set description based on products with colors and quantities
            description_lines = []
            for move in picking.move_ids:
                product = move.product_id

                # Get quantity - use quantity_done if picking is done, otherwise product_uom_qty
                if picking.state == 'done':
                    quantity = int(sum(move.move_line_ids.mapped('qty_done')))
                else:
                    quantity = int(move.product_uom_qty)

                # Skip if quantity is 0
                if quantity == 0:
                    continue

                # Build product description - START WITH QUANTITY
                product_desc = f"{quantity} X {product.name}"

                # Try to get color from product attributes if not already in name
                if product.product_template_variant_value_ids:
                    color_values = product.product_template_variant_value_ids.filtered(
                        lambda v: v.attribute_id.name.lower() in ['color', 'colour', 'لون']
                    )
                    if color_values:
                        color = color_values[0].name
                        # Only add color if it's not already in the product name
                        if color.lower() not in product.name.lower():
                            product_desc += f" {color}"

                description_lines.append(product_desc)

            # Join all product descriptions
            if description_lines:
                # Use newline for multiple products (optional)
                # res['description'] = '\n'.join(description_lines)

                # Or use comma (current behavior)
                res['description'] = ', '.join(description_lines)
            else:
                res['description'] = 'General Merchandise'

            # Set service type from carrier
            if picking.carrier_id and picking.carrier_id.delivery_type == 'iw_express':
                res['service_type_id'] = picking.carrier_id.iw_service_type
                res['load_type'] = picking.carrier_id.iw_load_type

            # Set COD info if payment term suggests COD
            if picking.sale_id:
                # Check if COD based on payment term name (customize as needed)
                payment_term = picking.sale_id.payment_term_id
                if payment_term and 'cod' in payment_term.name.lower():
                    res['is_cod'] = True

            # Set customer civil ID from partner
            if picking.partner_id.vat:
                res['receiver_civil_id'] = picking.partner_id.vat

        return res

    @api.depends('picking_id', 'picking_id.move_ids.product_uom_qty', 'picking_id.move_ids.product_id.weight')
    def _compute_weight(self):
        """Calculate total weight from picking"""
        for wizard in self:
            if wizard.picking_id:
                total_weight = sum([
                    (move.product_id.weight or 0.0) * move.product_uom_qty
                    for move in wizard.picking_id.move_ids
                ])
                wizard.weight = total_weight or 1.0
            else:
                wizard.weight = 1.0

    @api.onchange('load_type')
    def _onchange_load_type(self):
        """Clear dimensions for DOCUMENT type"""
        if self.load_type == 'DOCUMENT':
            self.length = 0
            self.width = 0
            self.height = 0

    @api.onchange('use_multi_piece', 'num_pieces')
    def _onchange_use_multi_piece(self):
        """Create piece lines when enabling multi-piece"""
        if self.use_multi_piece and self.num_pieces > 0 and not self.piece_line_ids:
            # Create piece lines based on picking moves
            pieces = []
            for i, move in enumerate(self.picking_id.move_ids):
                if i < self.num_pieces:
                    pieces.append((0, 0, {
                        'description': move.product_id.name,
                        'declared_value': move.product_id.lst_price * move.product_uom_qty,
                        'weight': (move.product_id.weight or 1.0) * move.product_uom_qty,
                        'quantity': int(move.product_uom_qty),
                        'hsn_code': move.product_id.default_code or '',
                    }))

            if len(pieces) < self.num_pieces:
                # Add empty pieces if needed
                for i in range(len(pieces), self.num_pieces):
                    pieces.append((0, 0, {
                        'description': f'Package {i + 1}',
                        'weight': self.weight / self.num_pieces,
                        'quantity': 1,
                    }))

            self.piece_line_ids = pieces

    @api.onchange('is_cod')
    def _onchange_is_cod(self):
        """Set COD amount from order total"""
        if self.is_cod:
            if self.picking_id.sale_id:
                self.cod_amount = self.picking_id.sale_id.amount_total
                self.cod_currency_id = self.picking_id.sale_id.currency_id
                # Set company name as default COD favor
                self.cod_favor_of = self.env.company.name
        else:
            self.cod_amount = 0.0
            self.cod_favor_of = False

    def _prepare_shipment_data(self):
        """Prepare data for IW Express API"""
        self.ensure_one()

        picking = self.picking_id
        partner = self.partner_id

        # Get IW config
        config = self.carrier_id.get_iw_config(partner)

        # Prepare origin details (from warehouse or company)
        if picking.picking_type_id.warehouse_id:
            warehouse = picking.picking_type_id.warehouse_id
            origin_partner = warehouse.partner_id or self.env.company.partner_id
            origin_name = warehouse.name
        else:
            origin_partner = self.env.company.partner_id
            origin_name = self.env.company.name

        # Prepare destination details
        dest_city = partner.city or ""
        dest_state = partner.state_id.name if partner.state_id else ""
        dest_country = partner.country_id.name if partner.country_id else ""
        dest_pincode = partner.zip or ""

        # Prepare origin details
        origin_city = origin_partner.city or ""
        origin_state = origin_partner.state_id.name if origin_partner.state_id else ""
        origin_country = origin_partner.country_id.name if origin_partner.country_id else ""
        origin_pincode = origin_partner.zip or ""

        # Build data dictionary - matching the exact structure from API docs
        data = {
            "cod_amount": str(self.cod_amount) if self.is_cod else "0",
            "currency": self.cod_currency_id.name if self.is_cod else config.currency_id.name,
            "cod_collection_mode": self.cod_collection_mode if self.is_cod else "cash",
            "cod_favor_of": self.cod_favor_of or "",
            "consignment_type": self.consignment_type,
            "customer_code": config.customer_code,
            "customer_reference_number": self.customer_reference_number,
            "declared_value": float(self.declared_value),
            "description": self.description,
            "destination_details": {
                "address_line_1": partner.street or partner.name,
                "address_line_2": partner.street2 or "",
                "alternate_phone": partner.mobile or "",
                "city": dest_city,
                "country": dest_country,
                "name": partner.name,
                "phone": partner.phone or partner.mobile or "",
                "pincode": dest_pincode,
                "state": dest_state
            },
            "dimension_unit": self.dimension_unit,
            "height": str(self.height) if self.load_type == 'NON-DOCUMENT' else "0",
            "is_risk_surcharge_applicable": self.is_risk_surcharge_applicable,
            "length": str(self.length) if self.load_type == 'NON-DOCUMENT' else "0",
            "load_type": self.load_type,
            "notes": self.notes or "",
            "num_pieces": int(self.num_pieces),
            "origin_details": {
                "address_line_1": origin_partner.street or origin_name,
                "address_line_2": origin_partner.street2 or "",
                "alternate_phone": origin_partner.mobile or "",
                "city": origin_city,
                "country": origin_country,
                "name": origin_name,
                "phone": origin_partner.phone or origin_partner.mobile or "",
                "pincode": origin_pincode,
                "state": origin_state
            },
            "service_type_id": self.service_type_id,
            "weight": float(self.weight),
            "weight_unit": self.weight_unit,
            "width": str(self.width) if self.load_type == 'NON-DOCUMENT' else "0"
        }

        # Add optional fields only if they have values
        if self.reference_number:
            data["reference_number"] = self.reference_number
        if self.inco_terms:
            data["inco_terms"] = self.inco_terms
        if self.customer_civil_id:
            data["customer_civil_id"] = self.customer_civil_id
        if self.receiver_civil_id:
            data["receiver_civil_id"] = self.receiver_civil_id

        # Add pieces detail
        if self.use_multi_piece and self.piece_line_ids:
            data["pieces_detail"] = []
            for piece in self.piece_line_ids:
                piece_data = {
                    "declared_value": float(piece.declared_value),
                    "description": piece.description,
                    "height": float(piece.height) if self.load_type == 'NON-DOCUMENT' else 0,
                    "length": float(piece.length) if self.load_type == 'NON-DOCUMENT' else 0,
                    "weight": float(piece.weight),
                    "width": float(piece.width) if self.load_type == 'NON-DOCUMENT' else 0,
                    "quantity": str(piece.quantity),
                }
                if piece.hsn_code:
                    piece_data["hsn_code"] = piece.hsn_code
                data["pieces_detail"].append(piece_data)
        else:
            # Single piece based on overall dimensions
            piece_detail = {
                "declared_value": float(self.declared_value),
                "description": self.description,  # This will use the description from wizard
                "height": float(self.height) if self.load_type == 'NON-DOCUMENT' else 0,
                "length": float(self.length) if self.load_type == 'NON-DOCUMENT' else 0,
                "weight": float(self.weight),
                "width": float(self.width) if self.load_type == 'NON-DOCUMENT' else 0,
                "quantity": "1"
            }

            # Add HSN code if available
            if picking.move_ids and picking.move_ids[0].product_id.default_code:
                piece_detail["hsn_code"] = picking.move_ids[0].product_id.default_code

            data["pieces_detail"] = [piece_detail]

        # Log the data if debug mode
        if config.debug_mode:
            _logger.info("IW Express Request Data:")
            _logger.info(json.dumps(data, indent=2))

        return data

    def action_create_shipment(self):
        """Create shipment via IW Express API"""
        self.ensure_one()

        # Validate
        if self.weight <= 0:
            raise ValidationError(_('Weight must be greater than 0!'))

        if self.is_cod and self.cod_amount <= 0:
            raise ValidationError(_('COD amount must be greater than 0!'))

        if self.load_type == 'NON-DOCUMENT':
            if not self.use_multi_piece and (not self.length or not self.width or not self.height):
                raise ValidationError(_('Dimensions (Length, Width, Height) are required for NON-DOCUMENT shipments!'))

        # Get config based on delivery address country
        partner = self.picking_id.partner_id
        try:
            config = self.carrier_id.get_iw_config(partner)
        except UserError as e:
            raise UserError(_(
                'Configuration Error:\n%(error)s\n\n'
                'Customer: %(customer)s\n'
                'Country: %(country)s',
                error=str(e),
                customer=partner.name,
                country=partner.country_id.name if partner.country_id else 'Not Set'
            ))

        if config.debug_mode:
            _logger.info(f"Using IW config: {config.display_name} for country: {config.country_id.name}")

        # Prepare data
        shipment_data = self._prepare_shipment_data()

        try:
            # Use v1 endpoint first (more stable)
            endpoint = 'softdata/upload'

            # Call API
            response = config._make_api_request(
                endpoint,
                method='POST',
                data=shipment_data
            )

            # Extract consignment reference
            consignment_ref = None
            label_data = None  # Initialize label_data

            # First, log the full response for debugging
            _logger.info(f"IW Express Full Response Type: {type(response)}")
            _logger.info(f"IW Express Full Response: {response}")

            # SPECIAL HANDLING FOR UAE - Response is just a number
            if isinstance(response, (int, float)):
                consignment_ref = str(response).strip()
                _logger.info(f"IW Express UAE: Got numeric response: {consignment_ref}")
            elif isinstance(response, str) and response.strip().isdigit():
                consignment_ref = response.strip()
                _logger.info(f"IW Express UAE: Got string numeric response: {consignment_ref}")
            elif isinstance(response, dict):
                # Try all possible keys
                consignment_ref = (
                        response.get('consignment_reference') or
                        response.get('consignmentReference') or
                        response.get('reference') or
                        response.get('referenceNumber') or
                        response.get('response_text') or
                        response.get('data')
                )

                # If still not found and response contains a number
                if not consignment_ref:
                    for key, value in response.items():
                        if str(value).strip().isdigit() and len(str(value)) > 10:
                            consignment_ref = str(value).strip()
                            _logger.info(f"IW Express: Found consignment ref in response['{key}']: {consignment_ref}")
                            break

                # Check for label data
                if 'label' in response:
                    label_data = response['label']

            # FINAL FALLBACK - Convert response to string and check
            if not consignment_ref:
                response_str = str(response).strip()
                if response_str.isdigit() and len(response_str) > 10:
                    consignment_ref = response_str
                    _logger.warning(f"IW Express: Using fallback - extracted from str(response): {consignment_ref}")

            if not consignment_ref:
                # Log full response for debugging
                _logger.error(f"IW Express Response: {json.dumps(response, indent=2)}")

                error_msg = _(
                    'No consignment reference received from IW Express!\n'
                    'Full Response: %(response)s',
                    response=json.dumps(response, indent=2) if isinstance(response, dict) else str(response)
                )

                if config.debug_mode:
                    raise UserError(error_msg)
                else:
                    raise UserError(
                        _('No consignment reference received from IW Express! Enable debug mode to see full response.'))

            # Create shipment record
            shipment_vals = {
                'name': consignment_ref,
                'customer_reference_number': self.customer_reference_number,
                'reference_number': self.reference_number,
                'inco_terms': self.inco_terms,
                'picking_id': self.picking_id.id,
                'service_type_id': self.service_type_id,
                'consignment_type': self.consignment_type,
                'load_type': self.load_type,
                'num_pieces': self.num_pieces,
                'weight': self.weight,
                'weight_unit': self.weight_unit,
                'dimension_unit': self.dimension_unit,
                'length': self.length,
                'width': self.width,
                'height': self.height,
                'declared_value': self.declared_value,
                'description': self.description,
                'is_cod': self.is_cod,
                'cod_amount': self.cod_amount if self.is_cod else 0,
                'cod_currency': self.cod_currency_id.id if self.is_cod else False,
                'cod_collection_mode': self.cod_collection_mode if self.is_cod else False,
                'cod_favor_of': self.cod_favor_of if self.is_cod else False,
                'is_risk_surcharge_applicable': self.is_risk_surcharge_applicable,
                'customer_civil_id': self.customer_civil_id,
                'receiver_civil_id': self.receiver_civil_id,
                'notes': self.notes,
                'state': 'confirmed',
                'company_id': self.picking_id.company_id.id,
            }

            # Add label if received
            if label_data:
                shipment_vals.update({
                    'label_pdf': label_data,
                    'label_filename': f'IW_Label_{consignment_ref}.pdf'
                })

            iw_shipment = self.env['iw.shipment'].create(shipment_vals)

            # Link to picking
            self.picking_id.iw_shipment_id = iw_shipment

            # Add note to picking
            note_body = _(
                '<b>IW Express shipment created successfully!</b><br/>'
                '<b>Configuration:</b> %(config)s<br/>'
                '<b>Country:</b> %(country)s<br/>'
                '<b>Consignment Ref:</b> %(ref)s<br/>'
                '<b>Service:</b> %(service)s (%(load)s)<br/>'
                '<b>Weight:</b> %(weight).2f %(unit)s<br/>'
                '<b>Pieces:</b> %(pieces)d',
                config=config.display_name,
                country=config.country_id.name,
                ref=consignment_ref,
                service=dict(self._fields['service_type_id'].selection).get(self.service_type_id),
                load=dict(self._fields['load_type'].selection).get(self.load_type),
                weight=self.weight,
                unit=self.weight_unit,
                pieces=self.num_pieces
            )

            if self.is_cod:
                note_body += _(
                    '<br/><b>COD Amount:</b> %(amount).2f %(currency)s',
                    amount=self.cod_amount,
                    currency=self.cod_currency_id.name
                )

            self.picking_id.message_post(
                body=note_body,
                subject=_('Shipment Created'),
                message_type='notification'
            )

            # Try to get label if not already received
            if not label_data and config.auto_print_label:
                try:
                    self.picking_id._get_iw_label()
                except Exception as e:
                    _logger.warning(f"Failed to get label immediately: {str(e)}")

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        'IW Express shipment created successfully!\n'
                        'Consignment Ref: %(ref)s\n'
                        'Service: %(service)s',
                        ref=consignment_ref,
                        service=dict(self._fields['service_type_id'].selection).get(self.service_type_id)
                    ),
                    'type': 'success',
                    'sticky': True,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        except UserError:
            raise
        except Exception as e:
            import traceback
            _logger.error(f"IW shipment creation failed: {str(e)}")
            _logger.error(f"Traceback: {traceback.format_exc()}")

            raise UserError(_(
                'Failed to create shipment:\n%(error)s\n\n'
                'Configuration: %(config)s\n'
                'Country: %(country)s',
                error=str(e),
                config=config.display_name if config else 'N/A',
                country=config.country_id.name if config and config.country_id else 'N/A'
            ))


class IWShipmentWizardPiece(models.TransientModel):
    _name = 'iw.shipment.wizard.piece'
    _description = 'IW Shipment Piece Detail'

    wizard_id = fields.Many2one('iw.shipment.wizard', required=True, ondelete='cascade')

    description = fields.Char(string='Description', required=True)
    declared_value = fields.Float(string='Declared Value', required=True)
    weight = fields.Float(string='Weight', required=True, default=1.0)
    quantity = fields.Integer(string='Quantity', default=1)
    hsn_code = fields.Char(string='HSN Code')

    # Dimensions (required for NON-DOCUMENT)
    length = fields.Float(string='Length')
    width = fields.Float(string='Width')
    height = fields.Float(string='Height')

    @api.onchange('wizard_id')
    def _onchange_wizard_id(self):
        """Set dimension requirement based on load type"""
        if self.wizard_id and self.wizard_id.load_type == 'DOCUMENT':
            self.length = 0
            self.width = 0
            self.height = 0
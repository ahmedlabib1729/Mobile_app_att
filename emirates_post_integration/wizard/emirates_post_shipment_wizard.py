# -*- coding: utf-8 -*-
import json
import requests
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EmiratesPostShipmentWizard(models.TransientModel):
    _name = 'emirates.post.shipment.wizard'
    _description = 'Emirates Post Shipment Wizard'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        required=True,
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='picking_id.partner_id',
        readonly=True
    )

    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier',
        readonly=True
    )

    # Reference
    reference_no = fields.Char(
        string='Reference Number',
        required=True,
        default=lambda self: self._default_reference()
    )

    # Sender Details
    sender_name = fields.Char(
        string='Sender Name',
        required=True,
        default=lambda self: self.env.company.name
    )
    sender_company = fields.Char(
        string='Sender Company',
        default=lambda self: self.env.company.name
    )
    sender_address = fields.Text(
        string='Sender Address',
        required=True,
        default=lambda self: self._default_sender_address()
    )
    sender_city = fields.Many2one(
        'emirates.post.emirate',
        string='Sender City',
        required=True
    )
    sender_phone = fields.Char(
        string='Sender Phone',
        required=True,
        default=lambda self: self.env.company.phone
    )
    sender_mobile = fields.Char(
        string='Sender Mobile',
        required=True,
        default=lambda self: self.env.company.mobile or self.env.company.phone
    )
    sender_email = fields.Char(
        string='Sender Email',
        default=lambda self: self.env.company.email
    )

    # Receiver Details
    receiver_name = fields.Char(
        string='Receiver Name',
        required=True
    )
    receiver_company = fields.Char(
        string='Receiver Company'
    )
    receiver_address = fields.Text(
        string='Receiver Address',
        required=True
    )
    receiver_city = fields.Many2one(
        'emirates.post.emirate',
        string='Receiver City',
        required=True
    )
    receiver_phone = fields.Char(
        string='Receiver Phone',
        required=True
    )
    receiver_mobile = fields.Char(
        string='Receiver Mobile',
        required=True
    )
    receiver_email = fields.Char(
        string='Receiver Email'
    )

    # Shipment Details
    cod_amount = fields.Float(
        string='COD Amount',
        default=0.0
    )
    pieces = fields.Integer(
        string='Pieces',
        default=1,
        required=True
    )
    weight = fields.Float(
        string='Weight (grams)',
        required=True,
        default=500
    )
    length = fields.Float(
        string='Length (cm)',
        default=10
    )
    width = fields.Float(
        string='Width (cm)',
        default=10
    )
    height = fields.Float(
        string='Height (cm)',
        default=10
    )
    item_value = fields.Float(
        string='Item Value',
        required=True
    )
    commodity_description = fields.Text(
        string='Description',
        required=True,
        compute='_compute_commodity_description',
        store=True,
        readonly=False
    )

    # Pickup Details
    pickup_date = fields.Date(
        string='Pickup Date',
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=1)
    )
    pickup_time_from = fields.Char(
        string='Pickup Time From',
        default='09:00',
        required=True
    )
    pickup_time_to = fields.Char(
        string='Pickup Time To',
        default='17:00',
        required=True
    )

    def _default_reference(self):
        if self.env.context.get('default_picking_id'):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])
            return picking.name
        return ''

    def _default_sender_address(self):
        company = self.env.company
        address_parts = []
        if company.street:
            address_parts.append(company.street)
        if company.street2:
            address_parts.append(company.street2)
        if company.city:
            address_parts.append(company.city)
        return ', '.join(address_parts)

    @api.depends('picking_id', 'picking_id.move_ids')
    def _compute_commodity_description(self):
        """حساب وصف المنتجات من تفاصيل الـ Picking"""
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.move_ids:
                # جمع تفاصيل المنتجات
                product_lines = []
                for move in wizard.picking_id.move_ids:
                    product = move.product_id
                    # الحصول على الكمية
                    if wizard.picking_id.state == 'done':
                        # إذا كان الـ picking مكتمل، استخدم الكمية الفعلية
                        qty = sum(move.move_line_ids.mapped('qty_done'))
                    else:
                        # وإلا استخدم الكمية المطلوبة
                        qty = move.product_uom_qty

                    if qty > 0:
                        # إضافة سطر لكل منتج
                        product_line = f"{product.name} - Qty: {int(qty)}"
                        product_lines.append(product_line)

                # دمج جميع السطور
                if product_lines:
                    wizard.commodity_description = '\n'.join(product_lines)
                else:
                    wizard.commodity_description = 'General Goods'
            else:
                wizard.commodity_description = 'General Goods'

    @api.model
    def default_get(self, fields_list):
        """Set default values including commodity description"""
        res = super().default_get(fields_list)

        if self.env.context.get('default_picking_id'):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])

            # حساب وصف المنتجات
            if picking.move_ids:
                product_lines = []
                for move in picking.move_ids:
                    product = move.product_id
                    # الحصول على الكمية
                    if picking.state == 'done':
                        qty = sum(move.move_line_ids.mapped('qty_done'))
                    else:
                        qty = move.product_uom_qty

                    if qty > 0:
                        product_line = f"{product.name} - Qty: {int(qty)}"
                        product_lines.append(product_line)

                if product_lines:
                    res['commodity_description'] = '\n'.join(product_lines)

        return res

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.receiver_name = self.partner_id.name
            self.receiver_company = self.partner_id.commercial_company_name or self.partner_id.name
            self.receiver_phone = self.partner_id.phone or ''
            self.receiver_mobile = self.partner_id.mobile or self.partner_id.phone or ''
            self.receiver_email = self.partner_id.email or ''

            # Address
            address_parts = []
            if self.partner_id.street:
                address_parts.append(self.partner_id.street)
            if self.partner_id.street2:
                address_parts.append(self.partner_id.street2)
            if self.partner_id.city:
                address_parts.append(self.partner_id.city)
            self.receiver_address = ', '.join(address_parts)

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            # Calculate weight
            total_weight = 0
            for move in self.picking_id.move_ids_without_package:
                weight = (move.product_id.weight or 0.0) * move.product_uom_qty
                total_weight += weight

            # Convert kg to grams
            self.weight = total_weight * 1000 if total_weight > 0 else 500

            # Calculate value
            if self.picking_id.sale_id:
                self.item_value = self.picking_id.sale_id.amount_total
                if self.picking_id.sale_id.payment_term_id and 'cod' in self.picking_id.sale_id.payment_term_id.name.lower():
                    self.cod_amount = self.picking_id.sale_id.amount_total

            # تحديث وصف المنتجات
            self._compute_commodity_description()

    def action_create_shipment(self):
        """Create Emirates Post shipment"""
        self.ensure_one()

        if not self.carrier_id.emirates_post_config_id:
            raise UserError(_('No Emirates Post configuration found!'))

        config = self.carrier_id.emirates_post_config_id

        # For testing with unavailable API
        if config.debug_mode:
            # Create mock shipment
            import random
            mock_awb = f"100000{random.randint(1000000, 9999999)}"

            shipment = self.env['emirates.post.shipment'].create({
                'name': mock_awb,
                'reference_no': self.reference_no,
                'picking_id': self.picking_id.id,
                'state': 'confirmed',

                # Sender
                'sender_name': self.sender_name,
                'sender_company': self.sender_company,
                'sender_address': self.sender_address,
                'sender_city': self.sender_city.id,
                'sender_phone': self.sender_phone,
                'sender_mobile': self.sender_mobile,
                'sender_email': self.sender_email,

                # Receiver
                'receiver_name': self.receiver_name,
                'receiver_company': self.receiver_company,
                'receiver_address': self.receiver_address,
                'receiver_city': self.receiver_city.id,
                'receiver_phone': self.receiver_phone,
                'receiver_mobile': self.receiver_mobile,
                'receiver_email': self.receiver_email,

                # Details
                'cod_amount': self.cod_amount,
                'pieces': self.pieces,
                'weight': self.weight,
                'length': self.length,
                'width': self.width,
                'height': self.height,
                'item_value': self.item_value,
                'commodity_description': self.commodity_description,
            })

            # Link to picking
            self.picking_id.emirates_post_shipment_id = shipment

            # Add note with product details
            note_body = _(
                '<b>Emirates Post TEST shipment created</b><br/>'
                '<b>AWB:</b> %s<br/>'
                '<b>Products:</b><br/>%s'
            ) % (mock_awb, self.commodity_description.replace('\n', '<br/>'))

            self.picking_id.message_post(
                body=note_body,
                subject=_('Test Shipment Created')
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Mode'),
                    'message': _('TEST shipment created with mock AWB: %s\n\nNote: This is test data only.') % mock_awb,
                    'type': 'warning',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    }
                }
            }

        # Normal API call (original code continues...)
        booking_data = {
            "BookingRequest": {
                # Sender Info
                "SenderContactName": self.sender_name,
                "SenderCompanyName": self.sender_company or None,
                "SenderAddress": self.sender_address,
                "SenderCity": int(self.sender_city.emirate_id),
                "SenderContactMobile": self.sender_mobile,
                "SenderContactPhone": self.sender_phone,
                "SenderEmail": self.sender_email,
                "SenderZipCode": "00000",
                "SenderState": self.sender_city.name,
                "SenderCountry": 971,  # UAE

                # Receiver Info
                "ReceiverContactName": self.receiver_name,
                "ReceiverCompanyName": self.receiver_company or None,
                "ReceiverAddress": self.receiver_address,
                "ReceiverCity": int(self.receiver_city.emirate_id),
                "ReceiverContactMobile": self.receiver_mobile,
                "ReceiverContactPhone": self.receiver_phone,
                "ReceiverEmail": self.receiver_email,
                "ReceiverZipCode": "00000",
                "ReceiverState": self.receiver_city.name,
                "ReceiverCountry": 971,  # UAE

                # Reference
                "ReferenceNo": self.reference_no,
                "ReferenceNo1": None,
                "ReferenceNo2": None,
                "ReferenceNo3": None,

                # Shipment Details
                "ContentTypeCode": "NonDocument",
                "NatureType": 11,
                "Service": "Domestic",
                "ShipmentType": "Express",
                "DeleiveryType": "Door to Door",
                "Registered": "No",
                "PaymentType": "Credit",
                "CODAmount": str(self.cod_amount),
                "CODCurrency": "AED" if self.cod_amount > 0 else None,
                "CommodityDescription": self.commodity_description,
                "Pieces": self.pieces,
                "Weight": self.weight,
                "WeightUnit": "Grams",
                "Length": self.length,
                "Width": self.width,
                "Height": self.height,
                "DimensionUnit": "Centimetre",
                "ItemValue": str(self.item_value),
                "ValueCurrency": "AED",

                # Additional
                "ProductCode": None,
                "DeliveryInstructionsID": None,
                "RequestSource": None,
                "SendMailToSender": "No",
                "SendMailToReceiver": "No",
                "PreferredPickupDate": self.pickup_date.strftime('%d-%b-%Y'),
                "PreferredPickupTimeFrom": self.pickup_time_from,
                "PreferredPickupTimeTo": self.pickup_time_to,
                "Is_Return_Service": "No",
                "PrintType": "LabelOnly",
                "Latitude": "25.2048",  # Default UAE coordinates
                "Longitude": "55.2708",
                "TransactionSource": None,
                "AWBType": "EAWB",
                "RequestType": "Booking",
                "Remarks": None,
                "SpecialNotes": None,
                "SenderRegionId": None,
                "ReceiverRegionId": None,
                "AWBNumber": None
            }
        }

        try:
            # Call API
            headers = config._get_headers()
            url = f"{config.api_url.rstrip('/')}/booking/rest/CreateBooking"

            if config.debug_mode:
                _logger.info(f"Emirates Post Booking URL: {url}")
                _logger.info(f"Emirates Post Booking Data: {json.dumps(booking_data, indent=2)}")

            response = requests.post(
                url,
                json=booking_data,
                headers=headers,
                timeout=30
            )

            if config.debug_mode:
                _logger.info(f"Emirates Post Response Status: {response.status_code}")
                _logger.info(f"Emirates Post Response: {response.text}")

            if response.status_code == 200:
                result = response.json()
                booking_response = result.get('BookingResponse', {})

                if booking_response.get('serviceResult', {}).get('success'):
                    awb_number = booking_response.get('AWBNumber')
                    label_data = booking_response.get('AWBLabel')

                    if not awb_number:
                        raise UserError(_('No AWB number in response!'))

                    # Create shipment record
                    shipment = self.env['emirates.post.shipment'].create({
                        'name': awb_number,
                        'reference_no': self.reference_no,
                        'picking_id': self.picking_id.id,
                        'state': 'confirmed',

                        # Sender
                        'sender_name': self.sender_name,
                        'sender_company': self.sender_company,
                        'sender_address': self.sender_address,
                        'sender_city': self.sender_city.id,
                        'sender_phone': self.sender_phone,
                        'sender_mobile': self.sender_mobile,
                        'sender_email': self.sender_email,

                        # Receiver
                        'receiver_name': self.receiver_name,
                        'receiver_company': self.receiver_company,
                        'receiver_address': self.receiver_address,
                        'receiver_city': self.receiver_city.id,
                        'receiver_phone': self.receiver_phone,
                        'receiver_mobile': self.receiver_mobile,
                        'receiver_email': self.receiver_email,

                        # Details
                        'cod_amount': self.cod_amount,
                        'pieces': self.pieces,
                        'weight': self.weight,
                        'length': self.length,
                        'width': self.width,
                        'height': self.height,
                        'item_value': self.item_value,
                        'commodity_description': self.commodity_description,

                        # Label
                        'label_data': label_data,
                        'label_filename': f'EP_{awb_number}.pdf',
                    })

                    # Link to picking
                    self.picking_id.emirates_post_shipment_id = shipment

                    # Add note with product details
                    note_body = _(
                        '<b>Emirates Post shipment created</b><br/>'
                        '<b>AWB:</b> %s<br/>'
                        '<b>Products:</b><br/>%s'
                    ) % (awb_number, self.commodity_description.replace('\n', '<br/>'))

                    self.picking_id.message_post(
                        body=note_body,
                        subject=_('Shipment Created')
                    )

                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'message': _('Emirates Post shipment created successfully!\nAWB: %s') % awb_number,
                            'type': 'success',
                            'sticky': True,
                            'next': {
                                'type': 'ir.actions.act_window_close'
                            }
                        }
                    }
                else:
                    error_msg = booking_response.get('serviceResult', {}).get('ErrorMsg', 'Unknown error')
                    raise UserError(_('Emirates Post API Error:\n%s') % error_msg)
            else:
                raise UserError(_(
                    'Emirates Post API Error!\n'
                    'Status: %(status)s\n'
                    'Response: %(response)s',
                    status=response.status_code,
                    response=response.text[:500]
                ))

        except requests.exceptions.RequestException as e:
            raise UserError(_(
                'Connection error:\n%(error)s',
                error=str(e)
            ))
        except Exception as e:
            raise UserError(_(
                'Error creating shipment:\n%(error)s',
                error=str(e)
            ))
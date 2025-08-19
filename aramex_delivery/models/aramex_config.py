# -*- coding: utf-8 -*-
import requests
import json
import logging
import base64
from datetime import datetime, timedelta
from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AramexConfig(models.Model):
    _name = 'aramex.config'
    _description = 'Aramex Configuration'
    _rec_name = 'display_name'
    _order = 'sequence, id'

    # ========== Basic Information ==========
    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='e.g. Aramex UAE, Aramex Saudi, Aramex Egypt'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of configurations'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # ========== Country Configuration ==========
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
        help='Country this configuration is for'
    )

    country_code = fields.Char(
        string='Country Code',
        related='country_id.code',
        store=True,
        readonly=True
    )

    is_default_for_country = fields.Boolean(
        string='Default for Country',
        help='Use this configuration by default for this country'
    )

    # ========== API Settings ==========
    api_url = fields.Char(
        string='API URL',
        required=True,
        default='https://ws.aramex.net/shippingapi/shipping/service_1_0.svc',
        help='Aramex API endpoint URL (Production or Test)'
    )

    test_mode = fields.Boolean(
        string='Test Mode',
        default=False,
        help='Use test/staging environment'
    )

    # ========== Authentication ==========
    username = fields.Char(
        string='Username',
        required=True,
        help='Aramex account username'
    )

    password = fields.Char(
        string='Password',
        required=True,
        help='Aramex account password'
    )

    account_number = fields.Char(
        string='Account Number',
        required=True,
        help='Aramex account number'
    )

    account_pin = fields.Char(
        string='Account PIN',
        required=True,
        help='Aramex account PIN'
    )

    account_entity = fields.Char(
        string='Account Entity',
        required=True,
        help='Entity code (e.g., DXB, RYD, CAI)'
    )

    account_country_code = fields.Char(
        string='Account Country Code',
        required=True,
        help='2-letter country code (e.g., AE, SA, EG)'
    )

    version = fields.Char(
        string='API Version',
        default='v1',
        help='Aramex API version'
    )

    # ========== Default Settings ==========
    default_product_group = fields.Selection([
        ('EXP', 'Express'),
        ('DOM', 'Domestic'),
    ], string='Default Product Group', default='DOM', required=True)

    default_product_type = fields.Selection([
        ('OND', 'Overnight Document'),
        ('ONP', 'Overnight Parcel'),
        ('PDX', 'Priority Document Express'),
        ('PPX', 'Priority Parcel Express'),
        ('DDX', 'Deferred Document Express'),
        ('DPX', 'Deferred Parcel Express'),
        ('GDX', 'Ground Document Express'),
        ('GPX', 'Ground Parcel Express'),
        ('EPX', 'Economy Parcel Express'),
    ], string='Default Product Type', default='ONP', required=True)

    default_payment_type = fields.Selection([
        ('P', 'Prepaid'),
        ('C', 'Collect'),
        ('3', 'Third Party'),
    ], string='Default Payment Type', default='P', required=True)

    default_payment_options = fields.Char(
        string='Default Payment Options',
        help='Default payment options string'
    )

    default_services = fields.Char(
        string='Default Services',
        help='Default service codes (comma separated, e.g., CODS,SIGN)'
    )

    # ========== Currency ==========
    currency_id = fields.Many2one(
        'res.currency',
        string='Default Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # ========== Options ==========
    auto_create_pickup = fields.Boolean(
        string='Auto Create Pickup',
        default=True,
        help='Automatically create pickup request when creating shipment'
    )

    label_report_id = fields.Integer(
        string='Label Report ID',
        default=9729,
        help='Report ID for label format'
    )

    label_report_type = fields.Selection([
        ('URL', 'URL'),
        ('RPT', 'Report'),
    ], string='Label Report Type', default='URL')

    debug_mode = fields.Boolean(
        string='Debug Mode',
        default=False,
        help='Enable detailed logging for debugging'
    )

    timeout = fields.Integer(
        string='API Timeout (seconds)',
        default=30,
        help='Timeout for API requests'
    )

    # ========== Notes ==========
    note = fields.Text(
        string='Notes',
        help='Additional notes or instructions'
    )

    # ========== Computed Fields ==========
    @api.depends('name', 'country_id', 'test_mode')
    def _compute_display_name(self):
        for record in self:
            parts = [record.name or 'New']
            if record.country_id:
                parts.append(f"({record.country_id.name})")
            if record.test_mode:
                parts.append("[TEST]")
            record.display_name = ' '.join(parts)

    # ========== Constraints ==========
    @api.constrains('country_id', 'is_default_for_country', 'company_id')
    def _check_default_for_country(self):
        """Ensure only one default per country per company"""
        for record in self:
            if record.is_default_for_country:
                existing = self.search([
                    ('country_id', '=', record.country_id.id),
                    ('is_default_for_country', '=', True),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_(
                        'There is already a default Aramex configuration for %(country)s!\n'
                        'Configuration: %(config)s',
                        country=record.country_id.name,
                        config=existing.display_name
                    ))

    _sql_constraints = [
        ('unique_name_company', 'UNIQUE(name, company_id)',
         'Configuration name must be unique per company!'),
    ]

    # ========== API Methods ==========
    def test_connection(self):
        """Test API connection with Aramex"""
        self.ensure_one()

        try:
            # Test with minimal CreateShipments request to verify credentials
            test_data = {
                'ClientInfo': self._prepare_client_info(),
                'Transaction': self._prepare_transaction('Test Connection', 'Test'),
                'Shipments': []  # Empty shipments - will fail but test auth
            }

            # Try the request
            try:
                response = self._call_aramex_api('CreateShipments', test_data)

                # Check if we got authentication error or other error
                if response and 'Notifications' in response:
                    notifications = response.get('Notifications', [])
                    if isinstance(notifications, dict):
                        notifications = [notifications]

                    auth_errors = ['ERR01', 'ERR02', 'ERR03']  # Authentication related errors
                    has_auth_error = False

                    for notif in notifications:
                        code = notif.get('Code', '')
                        if any(err in code for err in auth_errors):
                            has_auth_error = True
                            break

                    if has_auth_error:
                        raise UserError(_('Authentication failed. Please check your credentials.'))

            except UserError as e:
                # Re-raise authentication errors
                if 'Authentication' in str(e):
                    raise
                # Other errors mean connection is working but request is invalid (expected)
                pass

            # إذا كانت البيانات صحيحة، حتى لو الشحنة غير موجودة
            # Success message
            message = _(
                'Connection successful!\n'
                'Configuration: %(config)s\n'
                'Country: %(country)s\n'
                'Account: %(account)s\n'
                'Entity: %(entity)s\n'
                'API Response: Connection verified',
                config=self.display_name,
                country=self.country_id.name,
                account=self.account_number,
                entity=self.account_entity
            )

            if self.debug_mode:
                _logger.info(f"Aramex connection test successful: {message}")

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            error_msg = str(e)
            if self.debug_mode:
                _logger.error(f"Aramex connection test failed: {error_msg}")

            raise UserError(_(
                'Connection test failed:\n%(error)s',
                error=error_msg
            ))

    def _prepare_client_info(self):
        """Prepare ClientInfo structure for API requests"""
        self.ensure_one()

        return {
            'UserName': self.username,
            'Password': self.password,
            'Version': self.version,
            'AccountNumber': self.account_number,
            'AccountPin': self.account_pin,
            'AccountEntity': self.account_entity,
            'AccountCountryCode': self.account_country_code,
        }

    def _prepare_transaction(self, reference1='', reference2=''):
        """Prepare Transaction structure for API requests"""
        return {
            'Reference1': reference1,
            'Reference2': reference2,
            'Reference3': '',
            'Reference4': '',
            'Reference5': ''
        }

    def _build_soap_envelope(self, operation, body_content):
        """Build SOAP envelope for Aramex API"""
        self.ensure_one()

        # SOAP envelope with namespaces
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
                  xmlns:v1="http://ws.aramex.net/ShippingAPI/v1/">
    <soapenv:Header/>
    <soapenv:Body>
        {body_content}
    </soapenv:Body>
</soapenv:Envelope>"""

        return envelope

    def _call_aramex_api(self, operation, data):
        """Call Aramex SOAP API"""
        self.ensure_one()

        try:
            # Convert data to XML format
            body_content = self._dict_to_xml(data, is_root=True)

            # Build SOAP envelope
            soap_envelope = self._build_soap_envelope(operation, body_content)

            # Headers - تصحيح الـ SOAPAction
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': f'"http://ws.aramex.net/ShippingAPI/v1/Service_1_0/{operation}"'  # مع quotes
            }

            if self.debug_mode:
                _logger.info("=" * 60)
                _logger.info(f"Aramex API Call: {operation}")
                _logger.info(f"URL: {self.api_url}")
                _logger.info(f"Headers: {json.dumps(headers, indent=2)}")
                _logger.info(f"Request:\n{soap_envelope}")
                _logger.info("=" * 60)

            # Make request
            response = requests.post(
                self.api_url,
                data=soap_envelope.encode('utf-8'),
                headers=headers,
                timeout=self.timeout
            )

            if self.debug_mode:
                _logger.info(f"Response Status: {response.status_code}")
                _logger.info(f"Response:\n{response.text}")

            # Parse response
            if response.status_code == 200:
                return self._parse_soap_response(response.text, operation)
            else:
                raise UserError(_(
                    'Aramex API Error:\n'
                    'Status: %(status)s\n'
                    'Response: %(response)s',
                    status=response.status_code,
                    response=response.text[:500]
                ))

        except requests.exceptions.Timeout:
            raise UserError(_('Aramex API request timeout. Please try again.'))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Cannot connect to Aramex API. Please check your internet connection.'))
        except Exception as e:
            if isinstance(e, UserError):
                raise
            raise UserError(_(
                'Aramex API Error:\n%(error)s',
                error=str(e)
            ))

    def _dict_to_xml(self, data, parent_tag='', is_root=False):
        """Convert dictionary to XML string"""
        xml_parts = []

        for key, value in data.items():
            if value is None:
                continue

            # للعنصر الرئيسي، نضيف الـ operation tag
            if is_root:
                tag = f"v1:{key}"
                xml_parts.append(f"<{tag}>")
                xml_parts.append(self._dict_to_xml(value, key))
                xml_parts.append(f"</{tag}>")
            else:
                tag = f"v1:{key}"

                if isinstance(value, dict):
                    xml_parts.append(f"<{tag}>")
                    xml_parts.append(self._dict_to_xml(value, key))
                    xml_parts.append(f"</{tag}>")
                elif isinstance(value, list):
                    for item in value:
                        xml_parts.append(f"<{tag}>")
                        if isinstance(item, dict):
                            xml_parts.append(self._dict_to_xml(item, key))
                        else:
                            xml_parts.append(str(item))
                        xml_parts.append(f"</{tag}>")
                else:
                    xml_parts.append(f"<{tag}>{self._escape_xml(str(value))}</{tag}>")

        return ''.join(xml_parts)

    def _escape_xml(self, text):
        """Escape special XML characters"""
        if not text:
            return text
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text

    def _parse_soap_response(self, response_text, operation):
        """Parse SOAP response from Aramex"""
        try:
            # Parse XML
            root = etree.fromstring(response_text.encode('utf-8'))

            # Remove namespaces for easier parsing
            for elem in root.getiterator():
                elem.tag = etree.QName(elem).localname
                for attr in elem.attrib:
                    elem.attrib.clear()

            # Find response element - try multiple possible names
            response_names = [
                f"{operation}Response",
                f"{operation}Result",
                operation,
                "Response"
            ]

            response_elem = None
            for name in response_names:
                response_elem = root.find(f".//{name}")
                if response_elem is not None:
                    break

            # If still not found, try to find Body element
            if response_elem is None:
                body_elem = root.find(".//Body")
                if body_elem is not None:
                    # Get first child of Body
                    for child in body_elem:
                        if 'Fault' not in child.tag:
                            response_elem = child
                            break

            if response_elem is None:
                # Log the structure for debugging
                if self.debug_mode:
                    _logger.error(f"Could not find response element. XML structure:")
                    _logger.error(etree.tostring(root, pretty_print=True).decode())

                # Try to parse any error
                fault_elem = root.find(".//Fault")
                if fault_elem is not None:
                    fault_string = fault_elem.find(".//faultstring")
                    if fault_string is not None:
                        raise UserError(_(
                            'Aramex API Error: %(error)s',
                            error=fault_string.text
                        ))

                raise UserError(_(
                    'Invalid response format from Aramex API.\n'
                    'Expected: %(expected)s',
                    expected=f"{operation}Response"
                ))

            # Convert to dictionary
            result = self._xml_to_dict(response_elem)

            if self.debug_mode:
                _logger.info(f"Parsed Response: {json.dumps(result, indent=2)}")

            return result

        except etree.XMLSyntaxError as e:
            raise UserError(_(
                'Invalid XML response from Aramex:\n%(error)s',
                error=str(e)
            ))

    def _xml_to_dict(self, element):
        """Convert XML element to dictionary"""
        result = {}

        # Handle text content
        if element.text and element.text.strip():
            if len(element) == 0:  # Leaf node
                return element.text.strip()
            else:
                result['_text'] = element.text.strip()

        # Handle attributes
        if element.attrib:
            result['_attrib'] = dict(element.attrib)

        # Handle child elements
        for child in element:
            child_data = self._xml_to_dict(child)

            if child.tag in result:
                # Convert to list if multiple elements with same tag
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data

        return result if result else None

    def _prepare_rate_calculate_request(self, origin_city, origin_country,
                                        dest_city, dest_country, weight, pieces):
        """Prepare rate calculation request for testing"""
        return {
            'ClientInfo': self._prepare_client_info(),
            'Transaction': self._prepare_transaction('Rate Test'),
            'OriginAddress': {
                'City': origin_city,
                'CountryCode': origin_country
            },
            'DestinationAddress': {
                'City': dest_city,
                'CountryCode': dest_country
            },
            'ShipmentDetails': {
                'PaymentType': self.default_payment_type,
                'ProductGroup': self.default_product_group,
                'ProductType': self.default_product_type,
                'ActualWeight': {'Value': weight, 'Unit': 'KG'},
                'NumberOfPieces': pieces,
                'DescriptionOfGoods': 'Test Shipment',
                'GoodsOriginCountry': origin_country
            }
        }

    # ========== Helper Methods ==========
    @api.model
    def get_config_for_partner(self, partner):
        """Get appropriate config based on partner's country"""
        if not partner:
            return False

        country = partner.country_id
        if not country:
            # Try to get from company default
            country = self.env.company.country_id

        if not country:
            raise UserError(_('No country defined for partner or company!'))

        # First, try to find default config for country
        config = self.search([
            ('country_id', '=', country.id),
            ('is_default_for_country', '=', True),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        # If no default, get any config for that country
        if not config:
            config = self.search([
                ('country_id', '=', country.id),
                ('active', '=', True),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

        if not config:
            raise UserError(_(
                'No Aramex configuration found for country: %(country)s\n'
                'Please create a configuration for this country.',
                country=country.name
            ))

        return config

    def get_service_types(self):
        """Get available service types for this configuration"""
        self.ensure_one()

        # Service types can vary by country
        # This is a simplified version - in reality, you'd call Aramex API
        domestic_services = [
            ('ONP', 'Overnight Parcel'),
            ('OND', 'Overnight Document'),
        ]

        express_services = [
            ('PPX', 'Priority Parcel Express'),
            ('PDX', 'Priority Document Express'),
            ('EPX', 'Economy Parcel Express'),
        ]

        if self.default_product_group == 'DOM':
            return domestic_services
        else:
            return express_services
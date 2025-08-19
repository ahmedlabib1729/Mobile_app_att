# -*- coding: utf-8 -*-
import requests
import json
import logging
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class IWConfig(models.Model):
    _name = 'iw.config'
    _description = 'IW Express Configuration'
    _rec_name = 'display_name'
    _order = 'sequence, id'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='e.g. IW Kuwait, IW Saudi, IW UAE'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # API Settings
    api_url = fields.Char(
        string='API URL',
        required=True,
        default='https://dev-b2b.iwexpress.com:5001/iwexpress/iwe-integration-service',
        help='IW Express API base URL'
    )

    api_token = fields.Char(
        string='API Authorization Token',
        required=True,
        help='Basic authorization token for API authentication'
    )

    customer_code = fields.Char(
        string='Customer Code',
        required=True,
        help='Your customer code in IW Express system'
    )

    # Service Settings
    default_service_type = fields.Selection([
        ('PREMIUM', 'Premium'),
        ('INTERNATIONAL', 'International'),
        ('DELIVERY', 'Delivery'),
    ], string='Default Service Type', default='PREMIUM', required=True)

    default_load_type = fields.Selection([
        ('DOCUMENT', 'Document'),
        ('NON-DOCUMENT', 'Non-Document'),
    ], string='Default Load Type', default='NON-DOCUMENT', required=True)

    # Country Settings
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
        help='Country this configuration is for'
    )

    country_code = fields.Char(
        string='Country Code',
        related='country_id.code',
        store=True
    )

    is_default_for_country = fields.Boolean(
        string='Default for Country',
        help='Use this configuration by default for this country'
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Default Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    # Additional Settings
    auto_print_label = fields.Boolean(
        string='Auto Print Label',
        default=True,
        help='Automatically retrieve and attach shipping label after creation'
    )

    dimension_unit = fields.Selection([
        ('CM', 'Centimeter'),
        ('IN', 'Inch'),
        ('MM', 'Millimeter'),
        ('M', 'Meter'),
    ], string='Dimension Unit', default='CM', required=True)

    weight_unit = fields.Selection([
        ('KG', 'Kilogram'),
        ('GM', 'Gram'),
        ('LB', 'Pound'),
        ('OZ', 'Ounce'),
    ], string='Weight Unit', default='KG', required=True)

    # Webhook Settings
    enable_webhook = fields.Boolean(
        string='Enable Webhook',
        default=False,
        help='Enable webhook for automatic status updates'
    )

    webhook_url = fields.Char(
        string='Webhook URL',
        help='URL where IW Express will send status updates'
    )

    # Debug
    debug_mode = fields.Boolean(
        string='Debug Mode',
        default=False,
        help='Enable detailed logging for troubleshooting'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Notes
    note = fields.Text(string='Notes')

    @api.depends('name', 'country_id')
    def _compute_display_name(self):
        for record in self:
            if record.country_id:
                record.display_name = f"{record.name} ({record.country_id.name})"
            else:
                record.display_name = record.name or 'New'

    @api.constrains('country_id', 'is_default_for_country')
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
                        'There is already a default IW configuration for %(country)s!\n'
                        'Configuration: %(config)s',
                        country=record.country_id.name,
                        config=existing.display_name
                    ))

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
                'No IW configuration found for country: %(country)s\n'
                'Please create a configuration for this country.',
                country=country.name
            ))

        return config

    def _get_headers(self):
        """Get API headers with authentication"""
        self.ensure_one()

        headers = {
            'Authorization': f'Basic {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if self.debug_mode:
            _logger.info(f"IW Headers: {headers}")

        return headers

    def test_connection(self):
        """Test API connection"""
        self.ensure_one()

        try:
            # Test with a simple POST to the main endpoint with minimal data
            test_data = {
                "customer_code": self.customer_code,
                "service_type_id": self.default_service_type,
                "consignment_type": "FORWARD",
                "load_type": self.default_load_type,
                "customer_reference_number": "TEST_CONNECTION_" + fields.Datetime.now().strftime('%Y%m%d%H%M%S'),
                "num_pieces": 1,
                "weight": 1,
                "weight_unit": self.weight_unit,
                "dimension_unit": self.dimension_unit,
                "declared_value": 100,
                "description": "Test Connection",
                "currency": self.currency_id.name,
                "origin_details": {
                    "name": "Test Sender",
                    "phone": "+1234567890",
                    "address_line_1": "Test Address",
                    "city": "Test City",
                    "country": self.country_id.name,
                    "state": "Test State",
                    "pincode": "12345"
                },
                "destination_details": {
                    "name": "Test Receiver",
                    "phone": "+0987654321",
                    "address_line_1": "Test Address 2",
                    "city": "Test City 2",
                    "country": self.country_id.name,
                    "state": "Test State",
                    "pincode": "54321"
                },
                "pieces_detail": [{
                    "declared_value": 100,
                    "description": "Test Item",
                    "weight": 1,
                    "length": 10,
                    "width": 10,
                    "height": 10,
                    "quantity": "1"
                }]
            }

            # Try to validate the connection without actually creating a shipment
            # First, let's just test if we can reach the API
            headers = self._get_headers()

            if self.debug_mode:
                _logger.info(f"IW Test Headers: {headers}")
                _logger.info(f"IW Test URL: {self.api_url}")

            # Simple test - just check if we get a proper response structure
            # We'll use a GET request to the base URL or a health check endpoint if available
            test_url = self.api_url.rstrip('/')

            # First try a simple GET to see if API is reachable
            try:
                response = requests.get(
                    test_url,
                    headers=headers,
                    timeout=10
                )

                if self.debug_mode:
                    _logger.info(f"IW Base URL Test - Status: {response.status_code}")
                    _logger.info(f"IW Base URL Test - Response: {response.text[:200]}")

                # If we get any response (even error), the connection works
                if response.status_code > 0:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'message': _('Connection test successful! API is reachable.'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }

            except requests.exceptions.ConnectionError:
                raise UserError(
                    _('Cannot connect to IW Express API. Please check the URL and your internet connection.'))
            except requests.exceptions.Timeout:
                raise UserError(_('Connection timeout. The API server is not responding.'))
            except Exception as e:
                # If GET fails, try other approach
                if self.debug_mode:
                    _logger.warning(f"GET test failed: {str(e)}, trying alternative test")

                # Alternative: Test with the main endpoint but with invalid data to check auth
                test_url = f"{self.api_url}/softdata/upload"
                invalid_data = {"test": "connection"}

                try:
                    response = requests.post(
                        test_url,
                        headers=headers,
                        json=invalid_data,
                        timeout=10
                    )

                    if self.debug_mode:
                        _logger.info(f"IW POST Test - Status: {response.status_code}")
                        _logger.info(f"IW POST Test - Response: {response.text[:200]}")

                    # 401 = Auth failed, 400 = Bad request (but auth worked!)
                    # Both mean we can connect
                    if response.status_code == 401:
                        raise UserError(_('Authentication failed! Please check your API token.'))
                    elif response.status_code in [400, 422]:  # Bad request but authenticated
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Success'),
                                'message': _('Connection and authentication successful!'),
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                    elif response.status_code == 200:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _('Success'),
                                'message': _('Connection test successful!'),
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                    else:
                        raise UserError(_(
                            'Unexpected response from API!\n'
                            'Status: %(status)s\n'
                            'Response: %(response)s',
                            status=response.status_code,
                            response=response.text[:500]
                        ))

                except Exception as e2:
                    raise UserError(_(
                        'Connection test failed:\n%(error)s',
                        error=str(e2)
                    ))

        except UserError:
            raise
        except Exception as e:
            raise UserError(_(
                'Connection test failed:\n%(error)s\n\n'
                'Please check:\n'
                '1. API URL is correct\n'
                '2. API Token is valid\n'
                '3. Your internet connection\n'
                '4. The API service is running',
                error=str(e)
            ))

    def _log_debug(self, message, data=None):
        """Log debug information"""
        if self.debug_mode:
            log_message = f"IW Express: {message}"
            if data:
                log_message += f"\nData: {json.dumps(data, indent=2)}"
            _logger.info(log_message)

    def _make_api_request(self, endpoint, method='GET', data=None, params=None, is_label=False):
        """Make API request with error handling"""
        self.ensure_one()

        base_url = self.api_url.rstrip('/')
        # Make sure endpoint doesn't start with /
        endpoint = endpoint.lstrip('/')
        url = f"{base_url}/{endpoint}"
        headers = self._get_headers()

        if self.debug_mode:
            self._log_debug(f'API Request: {method} {endpoint}', {
                'full_url': url,
                'base_url': base_url,
                'endpoint': endpoint,
                'params': params,
                'data': data
            })

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if self.debug_mode:
                self._log_debug(f'API Response: {method} {endpoint}', {
                    'status': response.status_code,
                    'headers': dict(response.headers),
                    'response': response.text[:1000] if response.text else 'Empty response'
                })

            # Check for success status codes
            if response.status_code not in [200, 201, 202]:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {json.dumps(error_data, indent=2)}"
                except:
                    error_msg += f": {response.text}"

                raise UserError(_(
                    'IW API Error:\n'
                    'Endpoint: %(endpoint)s\n'
                    'Status: %(status)s\n'
                    'Error: %(error)s',
                    endpoint=endpoint,
                    status=response.status_code,
                    error=error_msg
                ))

            # Handle label PDF response
            if is_label:
                return response.content

            # Parse JSON response
            if response.text:
                try:
                    result = response.json()

                    if self.debug_mode:
                        self._log_debug(f'API Response Parsed: {method} {endpoint}', result)

                    return result

                except json.JSONDecodeError as e:
                    # Check if it's a plain text response (like consignment reference)
                    text_response = response.text.strip()
                    if text_response and response.status_code == 200:
                        # For consignment creation, the response might be just the reference number
                        if 'softdata/upload' in endpoint and text_response:
                            if self.debug_mode:
                                self._log_debug(f'API Response (Plain Text): {method} {endpoint}',
                                                {'consignment_ref': text_response})
                            return {'consignment_reference': text_response}

                    _logger.error(f"IW: Failed to parse JSON response: {e}")
                    _logger.error(f"IW: Response text: {response.text}")

                    # Return as text response
                    if response.text.strip():
                        return {'response_text': response.text.strip()}
                    else:
                        return {}
            else:
                return {}

        except requests.exceptions.RequestException as e:
            self._log_debug(f'API Error: {endpoint}', {'error': str(e)})
            raise UserError(_(
                'IW API Error:\n'
                'Endpoint: %(endpoint)s\n'
                'Error: %(error)s',
                endpoint=endpoint,
                error=str(e)
            ))
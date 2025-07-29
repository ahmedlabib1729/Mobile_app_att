# -*- coding: utf-8 -*-
import requests
import json
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PorterConfig(models.Model):
    _name = 'porter.config'
    _description = 'Porter Express Configuration'
    _rec_name = 'display_name'
    _order = 'sequence, id'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='e.g. Porter Kuwait, Porter UAE, Porter Saudi'
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

    # Country Configuration
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

    # API Settings
    api_url = fields.Char(
        string='API URL',
        required=True,
        default='https://stage-api.porterex.com/api/CustomerShipment',
        help='Porter Express API endpoint URL'
    )

    api_email = fields.Char(
        string='API Email',
        required=True,
        help='Email for API authentication'
    )

    api_password = fields.Char(
        string='API Password',
        required=True,
        help='Password for API authentication'
    )

    # Token Management
    access_token = fields.Char(
        string='Access Token',
        readonly=True
    )

    token_expiry = fields.Datetime(
        string='Token Expiry',
        readonly=True
    )

    # Settings
    default_product_code = fields.Selection([
        ('DE', 'Delivery Express'),
        ('SD', 'Same Day'),
        ('ND', 'Next Day'),
    ], string='Default Product Code', default='DE', required=True)

    auto_create_pickup = fields.Boolean(
        string='Auto Create Pickup',
        default=True
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Default Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    debug_mode = fields.Boolean(
        string='Debug Mode',
        default=False
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
                        'There is already a default Porter configuration for %(country)s!\n'
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
                'No Porter configuration found for country: %(country)s\n'
                'Please create a configuration for this country.',
                country=country.name
            ))

        return config



    def _get_headers(self):
        """Get API headers with authentication"""
        self.ensure_one()

        # Check if token needs refresh or doesn't exist
        need_auth = False
        if not self.access_token:
            need_auth = True
            _logger.info("Porter: No access token found, authenticating...")
        elif not self.token_expiry:
            need_auth = True
            _logger.info("Porter: No token expiry found, authenticating...")
        elif fields.Datetime.now() >= self.token_expiry:
            need_auth = True
            _logger.info("Porter: Token expired, re-authenticating...")

        if need_auth:
            self._authenticate()

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        if self.debug_mode:
            _logger.info(f"Porter Headers: {headers}")

        return headers

    def _authenticate(self):
        """Authenticate and get access token"""
        self.ensure_one()

        # تأكد من عدم وجود / في نهاية الـ URL
        base_url = self.api_url.rstrip('/')
        auth_url = f"{base_url}/Authenticate"

        payload = {
            "email": self.api_email,
            "password": self.api_password
        }

        if self.debug_mode:
            _logger.info(f"Porter Auth URL: {auth_url}")
            _logger.info(f"Porter Auth Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                auth_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if self.debug_mode:
                _logger.info(f"Porter Auth Response Status: {response.status_code}")
                _logger.info(f"Porter Auth Response: {response.text}")

            if response.status_code == 200:
                data = response.json()

                # Porter API returns the token directly
                access_token = data.get('access_token') or data.get('token') or data.get('Token')

                if not access_token:
                    raise UserError(_(
                        'No access token in response!\n'
                        'Response: %(response)s',
                        response=json.dumps(data, indent=2)
                    ))

                # حفظ التوكن
                self.sudo().write({
                    'access_token': access_token,
                    'token_expiry': fields.Datetime.now() + timedelta(hours=23)  # Token valid for 24 hours
                })

                _logger.info("Porter: Authentication successful!")

                if self.debug_mode:
                    self._log_debug('Authentication successful', {
                        'token': access_token[:20] + '...' if len(access_token) > 20 else access_token
                    })

            else:
                error_msg = f"Authentication failed!\nStatus: {response.status_code}\n"
                try:
                    error_data = response.json()
                    error_msg += f"Error: {json.dumps(error_data, indent=2)}"
                except:
                    error_msg += f"Response: {response.text}"

                raise UserError(_(error_msg))

        except requests.exceptions.RequestException as e:
            raise UserError(_(
                'Connection error during authentication:\n%(error)s',
                error=str(e)
            ))

    def test_connection(self):
        """Test API connection"""
        self.ensure_one()

        try:
            # Force re-authentication
            self.access_token = False
            self._authenticate()

            # Try to get cities as a test
            base_url = self.api_url.rstrip('/')
            test_url = f"{base_url}/GetCities"
            headers = self._get_headers()

            if self.debug_mode:
                _logger.info(f"Porter Test URL: {test_url}")

            response = requests.get(
                test_url,
                headers=headers,
                params={'id': 'KW'},
                timeout=30
            )

            if self.debug_mode:
                _logger.info(f"Porter Test Response Status: {response.status_code}")
                _logger.info(f"Porter Test Response: {response.text[:500]}")  # First 500 chars

            if response.status_code == 200:
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
                    'API test failed!\n'
                    'Status: %(status)s\n'
                    'Response: %(response)s',
                    status=response.status_code,
                    response=response.text[:500]
                ))

        except Exception as e:
            raise UserError(_(
                'Connection test failed:\n%(error)s',
                error=str(e)
            ))

    def _log_debug(self, message, data=None):
        """Log debug information"""
        if self.debug_mode:
            log_message = f"Porter Express: {message}"
            if data:
                log_message += f"\nData: {json.dumps(data, indent=2)}"
            _logger.info(log_message)

    def _make_api_request(self, endpoint, method='GET', data=None, params=None):
        """Make API request with error handling"""
        self.ensure_one()

        base_url = self.api_url.rstrip('/')
        url = f"{base_url}/{endpoint}"
        headers = self._get_headers()

        if self.debug_mode:
            self._log_debug(f'API Request: {method} {endpoint}', {
                'url': url,
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
                    'response': response.text[:1000] if response.text else 'Empty response'
                })

            # إذا كانت 401، حاول المصادقة مرة أخرى
            if response.status_code == 401:
                _logger.warning("Porter: Got 401, re-authenticating...")
                self.access_token = False
                self._authenticate()
                # أعد المحاولة مرة واحدة
                headers = self._get_headers()
                if method == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=30)

            # ================ أضف الكود هنا ================
            # معالجة خطأ 400
            if response.status_code == 400:
                _logger.error("=" * 60)
                _logger.error("PORTER API ERROR 400 - FULL DETAILS")
                _logger.error(f"Request URL: {url}")
                _logger.error(f"Request Headers: {json.dumps(dict(headers), indent=2)}")
                _logger.error(f"Request Body: {json.dumps(data, indent=2) if data else 'No body'}")
                _logger.error(f"Response Status: {response.status_code}")
                _logger.error(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
                _logger.error(f"Response Body: {response.text}")
                _logger.error("=" * 60)
            # ===============================================

            # Check for success status codes
            if response.status_code not in [200, 201, 202, 204]:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {json.dumps(error_data, indent=2)}"
                except:
                    error_msg += f": {response.text}"

                raise UserError(_(
                    'Porter API Error:\n'
                    'Endpoint: %(endpoint)s\n'
                    'Status: %(status)s\n'
                    'Error: %(error)s',
                    endpoint=endpoint,
                    status=response.status_code,
                    error=error_msg
                ))

            # Parse response
            if response.text:
                try:
                    result = response.json()

                    if self.debug_mode:
                        self._log_debug(f'API Response Parsed: {method} {endpoint}', result)

                    return result

                except json.JSONDecodeError as e:
                    _logger.error(f"Porter: Failed to parse JSON response: {e}")
                    _logger.error(f"Porter: Response text: {response.text}")

                    # Maybe it's a plain text response?
                    if response.text.strip():
                        return {'response_text': response.text.strip()}
                    else:
                        return {}
            else:
                return {}

        except requests.exceptions.RequestException as e:
            self._log_debug(f'API Error: {endpoint}', {'error': str(e)})
            raise UserError(_(
                'Porter API Error:\n'
                'Endpoint: %(endpoint)s\n'
                'Error: %(error)s',
                endpoint=endpoint,
                error=str(e)
            ))
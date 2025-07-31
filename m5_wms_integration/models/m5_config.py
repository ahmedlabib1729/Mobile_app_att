# -*- coding: utf-8 -*-
import requests
import json
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class M5Config(models.Model):
    _name = 'm5.config'
    _description = 'M5 WMS Configuration'
    _rec_name = 'display_name'
    _order = 'sequence, id'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='e.g. M5 WMS Main, M5 WMS Secondary'
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
        default='https://m5aznwms.com/api',
        help='M5 WMS API base URL'
    )

    email = fields.Char(
        string='API Email',
        required=True,
        help='Email for API authentication'
    )

    password = fields.Char(
        string='API Password',
        required=True,
        help='Password for API authentication'
    )

    # Token Management
    access_token = fields.Char(
        string='Access Token',
        readonly=True
    )

    client_id = fields.Char(
        string='Client ID',
        readonly=True
    )

    warehouse_id = fields.Char(
        string='M5 Warehouse ID',
        readonly=True
    )

    token_expiry = fields.Datetime(
        string='Token Expiry',
        readonly=True
    )

    # Settings
    auto_send_orders = fields.Boolean(
        string='Auto Send Orders',
        default=True,
        help='Automatically send orders to M5 WMS when delivery is validated'
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

    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name or 'New'

    def _get_headers(self):
        """Get API headers with authentication"""
        self.ensure_one()

        # Check if token needs refresh
        if not self.access_token or not self.token_expiry or fields.Datetime.now() >= self.token_expiry:
            self._authenticate()

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'device': 'api'  # من الـ Postman
        }

        if self.debug_mode:
            _logger.info(f"M5 Headers: {headers}")

        return headers

    def _authenticate(self):
        """Authenticate and get access token"""
        self.ensure_one()

        auth_url = f"{self.api_url}/auth/token"

        payload = {
            "email": self.email,
            "password": self.password
        }

        if self.debug_mode:
            _logger.info(f"M5 Auth URL: {auth_url}")
            _logger.info(f"M5 Auth Payload: {json.dumps(payload, indent=2)}")

        try:
            response = requests.post(
                auth_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if self.debug_mode:
                _logger.info(f"M5 Auth Response Status: {response.status_code}")
                _logger.info(f"M5 Auth Response: {response.text}")

            if response.status_code == 200:
                data = response.json()

                # Extract data from response
                self.sudo().write({
                    'access_token': data.get('token'),
                    'client_id': str(data.get('client_id', '')),
                    'warehouse_id': str(data.get('warehouse_id', '')),
                    'token_expiry': fields.Datetime.now() + timedelta(days=365)  # Token valid for 1 year
                })

                _logger.info("M5: Authentication successful!")

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

            if self.access_token:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _(
                            'Connection test successful!\n'
                            'Client ID: %(client)s\n'
                            'Warehouse ID: %(warehouse)s',
                            client=self.client_id,
                            warehouse=self.warehouse_id
                        ),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Authentication failed!'))

        except Exception as e:
            raise UserError(_(
                'Connection test failed:\n%(error)s',
                error=str(e)
            ))

    def _log_debug(self, message, data=None):
        """Log debug information"""
        if self.debug_mode:
            log_message = f"M5 WMS: {message}"
            if data:
                log_message += f"\nData: {json.dumps(data, indent=2)}"
            _logger.info(log_message)

    def _make_api_request(self, endpoint, method='GET', data=None, params=None):
        """Make API request with error handling"""
        self.ensure_one()

        url = f"{self.api_url}/{endpoint}"
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

            # Handle 401 - re-authenticate
            if response.status_code == 401:
                _logger.warning("M5: Got 401, re-authenticating...")
                self.access_token = False
                self._authenticate()
                # Retry once
                headers = self._get_headers()
                if method == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=30)

            # Check for success
            if response.status_code not in [200, 201]:
                error_msg = f"HTTP Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {json.dumps(error_data, indent=2)}"
                except:
                    error_msg += f": {response.text}"

                raise UserError(_(
                    'M5 API Error:\n'
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
                    return response.json()
                except json.JSONDecodeError:
                    return {'response_text': response.text}
            else:
                return {}

        except requests.exceptions.RequestException as e:
            raise UserError(_(
                'M5 API Error:\n'
                'Endpoint: %(endpoint)s\n'
                'Error: %(error)s',
                endpoint=endpoint,
                error=str(e)
            ))
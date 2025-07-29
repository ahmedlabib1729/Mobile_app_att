# -*- coding: utf-8 -*-
import requests
import json
import logging
import urllib3
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Disable SSL warnings for test environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_logger = logging.getLogger(__name__)


class EmiratesPostConfig(models.Model):
    _name = 'emirates.post.config'
    _description = 'Emirates Post Configuration'
    _rec_name = 'name'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        help='e.g. Emirates Post Production'
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
        default='https://osbtest.epg.gov.ae/ebs/genericapi',
        help='Emirates Post API endpoint URL'
    )

    account_no = fields.Char(
        string='Account Number',
        required=True,
        help='Emirates Post account number'
    )

    password = fields.Char(
        string='Password',
        required=True,
        help='Emirates Post password'
    )

    # Settings
    debug_mode = fields.Boolean(
        string='Debug Mode',
        default=False,
        help='Enable detailed logging'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    def _get_headers(self):
        """Get API headers"""
        self.ensure_one()
        return {
            'Content-Type': 'application/json',
            'AccountNo': self.account_no,
            'Password': self.password
        }

    def test_connection(self):
        """Test API connection"""
        self.ensure_one()

        try:
            # Test by getting emirates list
            url = f"{self.api_url.rstrip('/')}/lookups/rest/GetEmiratesDetails"
            headers = self._get_headers()

            if self.debug_mode:
                _logger.info(f"Testing connection to: {url}")
                _logger.info(f"Headers: {headers}")

            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                verify=False  # Skip SSL verification for test environment
            )

            if self.debug_mode:
                _logger.info(f"Response status: {response.status_code}")
                _logger.info(f"Response headers: {response.headers}")

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
            elif response.status_code == 520:
                # Server error - suggest alternative
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Server Unavailable'),
                        'message': _(
                            'Emirates Post test server is currently unavailable (Error 520).\n'
                            'This is common with their test environment.\n\n'
                            'You can:\n'
                            '1. Try again later\n'
                            '2. Contact Emirates Post for production credentials\n'
                            '3. Continue with mock data for testing'
                        ),
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            else:
                raise UserError(_(
                    'Connection test failed!\n'
                    'Status: %(status)s\n'
                    'Response: %(response)s',
                    status=response.status_code,
                    response=response.text[:500]
                ))

        except requests.exceptions.ConnectionError:
            raise UserError(_(
                'Cannot connect to Emirates Post server.\n'
                'Please check:\n'
                '1. Internet connection\n'
                '2. API URL is correct\n'
                '3. Server is accessible from your location'
            ))
        except requests.exceptions.Timeout:
            raise UserError(_('Connection timeout. The server took too long to respond.'))
        except Exception as e:
            raise UserError(_(
                'Connection test failed:\n%(error)s',
                error=str(e)
            ))

    def sync_emirates(self):
        """Sync emirates from API"""
        self.ensure_one()

        try:
            url = f"{self.api_url.rstrip('/')}/lookups/rest/GetEmiratesDetails"
            headers = self._get_headers()

            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                emirates_data = data.get('GetEmiratesDetailsResult', {}).get('EmirateBO', [])

                Emirate = self.env['emirates.post.emirate']
                created = updated = 0

                for emirate_data in emirates_data:
                    existing = Emirate.search([
                        ('emirate_id', '=', emirate_data['EmirateID'])
                    ], limit=1)

                    vals = {
                        'emirate_id': emirate_data['EmirateID'],
                        'name': emirate_data['EmirateName'],
                        'code': emirate_data['EmirateCode'],
                    }

                    if existing:
                        existing.write(vals)
                        updated += 1
                    else:
                        Emirate.create(vals)
                        created += 1

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _(
                            'Emirates synchronized!\n'
                            'Created: %(created)s\n'
                            'Updated: %(updated)s',
                            created=created,
                            updated=updated
                        ),
                        'type': 'success',
                        'sticky': True,
                    }
                }

            elif response.status_code == 520:
                # Server unavailable - use mock data
                return self._create_mock_emirates()

        except Exception as e:
            # If API fails, offer to create mock data
            return self._create_mock_emirates()

    def _create_mock_emirates(self):
        """Create mock emirates data for testing"""
        self.ensure_one()

        # Mock data based on the API response
        mock_emirates = [
            {'EmirateID': '2', 'EmirateName': 'Abu Dhabi', 'EmirateCode': 'AUH'},
            {'EmirateID': '4', 'EmirateName': 'Ajman', 'EmirateCode': 'AJM'},
            {'EmirateID': '12', 'EmirateName': 'Al Ain', 'EmirateCode': 'AIN'},
            {'EmirateID': '1', 'EmirateName': 'Dubai', 'EmirateCode': 'DXB'},
            {'EmirateID': '5', 'EmirateName': 'Fujairah', 'EmirateCode': 'FUJ'},
            {'EmirateID': '6', 'EmirateName': 'Ras Al Khaimah', 'EmirateCode': 'RAK'},
            {'EmirateID': '3', 'EmirateName': 'Sharjah', 'EmirateCode': 'SHJ'},
            {'EmirateID': '7', 'EmirateName': 'Umm Al Quwain', 'EmirateCode': 'UAQ'},
        ]

        Emirate = self.env['emirates.post.emirate']
        created = updated = 0

        for emirate_data in mock_emirates:
            existing = Emirate.search([
                ('emirate_id', '=', emirate_data['EmirateID'])
            ], limit=1)

            vals = {
                'emirate_id': emirate_data['EmirateID'],
                'name': emirate_data['EmirateName'],
                'code': emirate_data['EmirateCode'],
            }

            if existing:
                existing.write(vals)
                updated += 1
            else:
                Emirate.create(vals)
                created += 1

        # Check total emirates
        total_emirates = Emirate.search_count([])

        if created == 0 and updated == 0:
            # All emirates already exist
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Emirates Already Exist'),
                    'message': _(
                        'All %(total)s emirates are already in the system.\n'
                        'You can proceed with creating shipments.\n\n'
                        'Note: Using mock data for testing due to API unavailability.',
                        total=total_emirates
                    ),
                    'type': 'info',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mock Data Created'),
                    'message': _(
                        'Emirates Post API is unavailable.\n'
                        'Created: %(created)s emirates\n'
                        'Updated: %(updated)s emirates\n'
                        'Total: %(total)s emirates in system\n\n'
                        'Note: This is test data. For production, you need working API credentials.',
                        created=created,
                        updated=updated,
                        total=total_emirates
                    ),
                    'type': 'warning',
                    'sticky': True,
                }
            }

    def view_emirates(self):
        """Open emirates list view"""
        self.ensure_one()

        return {
            'name': _('Emirates'),
            'type': 'ir.actions.act_window',
            'res_model': 'emirates.post.emirate',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {'create': False}  # Prevent manual creation
        }
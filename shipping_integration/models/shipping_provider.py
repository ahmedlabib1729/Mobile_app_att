# shipping_integration/models/__init__.py
from . import shipping_provider
from . import shipping_request
from . import field_mapping
from . import sale_order

import logging, requests

_logger = logging.getLogger(__name__)

# shipping_integration/models/shipping_provider.py
from odoo import models, fields, api
import requests
import json
import base64
from datetime import datetime, timedelta


class ShippingProvider(models.Model):
    _name = 'shipping.provider'
    _description = 'Shipping Provider Configuration'

    name = fields.Char(string='Provider Name', required=True)
    code = fields.Char(string='Provider Code', required=True)
    base_url = fields.Char(string='Base URL', required=True)
    active = fields.Boolean(string='Active', default=True)

    # Authentication fields
    auth_type = fields.Selection([
        ('none', 'No Authentication'),
        ('basic', 'Basic Authentication'),
        ('bearer', 'Bearer Token'),
        ('api_key', 'API Key')
    ], string='Authentication Type', default='none', required=True)

    auth_username = fields.Char(string='Username/Email')
    auth_password = fields.Char(string='Password')
    auth_token = fields.Char(string='Static Token')
    auth_api_key = fields.Char(string='API Key')

    # Dynamic token management
    current_token = fields.Char(string='Current Token', readonly=True)
    token_expiry = fields.Datetime(string='Token Expiry', readonly=True)

    # Endpoints
    auth_endpoint = fields.Char(string='Authentication Endpoint')
    create_shipment_endpoint = fields.Char(string='Create Shipment Endpoint', required=True)
    get_label_endpoint = fields.Char(string='Get Label Endpoint')
    track_shipment_endpoint = fields.Char(string='Track Shipment Endpoint')
    cancel_shipment_endpoint = fields.Char(string='Cancel Shipment Endpoint')

    # Field mappings
    field_mapping_ids = fields.One2many('shipping.field.mapping', 'provider_id', string='Field Mappings')

    # Request/Response configuration
    request_content_type = fields.Selection([
        ('json', 'application/json'),
        ('xml', 'application/xml'),
        ('form', 'application/x-www-form-urlencoded')
    ], string='Request Content Type', default='json')

    response_type = fields.Selection([
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('text', 'Plain Text')
    ], string='Response Type', default='json')

    # Response paths
    tracking_number_path = fields.Char(string='Tracking Number Path',
                                       help='JSON path to tracking number in response. E.g., data.tracking_number')
    error_message_path = fields.Char(string='Error Message Path',
                                     help='JSON path to error message in response. E.g., error.message')

    @api.model
    def create(self, vals):
        """Override create to set up default mappings"""
        provider = super(ShippingProvider, self).create(vals)
        provider._create_default_mappings()
        return provider

    def _create_default_mappings(self):
        """Create default field mappings for common fields"""
        common_mappings = [
            ('order_reference', 'Order Reference', 'reference'),
            ('sender_name', 'Sender Name', 'company.name'),
            ('sender_phone', 'Sender Phone', 'company.phone'),
            ('sender_address', 'Sender Address', 'company.street'),
            ('receiver_name', 'Receiver Name', 'partner.name'),
            ('receiver_phone', 'Receiver Phone', 'partner.phone'),
            ('receiver_address', 'Receiver Address', 'partner.street'),
            ('weight', 'Weight', 'weight'),
            ('pieces_count', 'Number of Pieces', 'pieces_count'),
        ]

        for field_key, field_name, odoo_field in common_mappings:
            self.env['shipping.field.mapping'].create({
                'provider_id': self.id,
                'field_key': field_key,
                'field_name': field_name,
                'odoo_field': odoo_field,
                'provider_field_path': '',  # To be configured by user
                'is_required': True,
            })

    def authenticate(self):
        """Authenticate with the shipping provider"""
        self.ensure_one()

        if self.auth_type == 'none':
            return True

        if self.auth_type == 'basic':
            # Basic auth doesn't need separate authentication
            return True

        if self.auth_type == 'bearer':
            # Check if token is still valid
            if self.current_token and self.token_expiry:
                if fields.Datetime.now() < self.token_expiry:
                    return True

            # Authenticate to get new token
            headers = {'Content-Type': 'application/json'}  # Porter specifically needs this
            auth_data = {
                'email': self.auth_username,
                'password': self.auth_password
            }

            try:
                response = requests.post(
                    self.base_url + self.auth_endpoint,
                    json=auth_data,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    self.current_token = data.get('access_token') or data.get('token')
                    # Assume token is valid for 24 hours if not specified
                    self.token_expiry = fields.Datetime.now() + timedelta(hours=24)
                    return True
                else:
                    raise Exception(f"Authentication failed: {response.text}")

            except Exception as e:
                raise Exception(f"Authentication error: {str(e)}")

        return False

    def _prepare_headers(self):
        """Prepare request headers based on auth type"""
        # Fix content type mapping
        content_type_map = {
            'json': 'application/json',
            'xml': 'application/xml',
            'form': 'application/x-www-form-urlencoded'
        }

        headers = {'Content-Type': content_type_map.get(self.request_content_type, self.request_content_type)}

        if self.auth_type == 'basic':
            if self.auth_token:
                headers['Authorization'] = f'Basic {self.auth_token}'
            else:
                credentials = base64.b64encode(f'{self.auth_username}:{self.auth_password}'.encode()).decode()
                headers['Authorization'] = f'Basic {credentials}'

        elif self.auth_type == 'bearer':
            if not self.current_token:
                self.authenticate()
            headers['Authorization'] = f'Bearer {self.current_token}'

        elif self.auth_type == 'api_key':
            headers['X-API-Key'] = self.auth_api_key

        return headers

    def send_request(self, endpoint_type, data=None, method='POST', **kwargs):
        """Send request to shipping provider"""
        self.ensure_one()

        # Get endpoint
        endpoint_map = {
            'create': self.create_shipment_endpoint,
            'label': self.get_label_endpoint,
            'track': self.track_shipment_endpoint,
            'cancel': self.cancel_shipment_endpoint,
        }

        endpoint = endpoint_map.get(endpoint_type)
        if not endpoint:
            raise Exception(f"Endpoint {endpoint_type} not configured")

        # Replace placeholders in endpoint
        for key, value in kwargs.items():
            endpoint = endpoint.replace(f'{{{key}}}', str(value))

        url = self.base_url + endpoint
        headers = self._prepare_headers()

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if self.request_content_type == 'json':
                    response = requests.post(url, json=data, headers=headers)
                else:
                    response = requests.post(url, data=data, headers=headers)

            return self._parse_response(response)

        except Exception as e:
            raise Exception(f"Request error: {str(e)}")

    def _parse_response(self, response):
        """Parse response based on response type"""
        if response.status_code not in [200, 201]:
            error_msg = f"Request failed with status {response.status_code}"
            if self.error_message_path and self.response_type == 'json':
                try:
                    error_data = response.json()
                    error_msg = self._get_value_from_path(error_data, self.error_message_path) or error_msg
                except:
                    pass
            raise Exception(f"{error_msg}: {response.text}")

        if self.response_type == 'json':
            return response.json()
        elif self.response_type == 'xml':
            # TODO: Implement XML parsing
            return response.text
        else:
            return response.text

    def _get_value_from_path(self, data, path):
        """Get value from nested dictionary using dot notation"""
        if not path:
            return data

        keys = path.split('.')
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

        return value

    def create_shipment(self, sale_order):
        """Create shipment for Porter Express - Fixed version"""
        self.ensure_one()

        try:
            _logger.info(f"=== Creating Porter shipment for order: {sale_order.name} ===")

            # Initialize the complete Porter structure
            request_data = {
                "Reference2": sale_order.name or "REF001",
                "ProductCode": "DE",
                "BrandCode": None,
                "ShipmentDetail": {
                    "CodAmount": 0,
                    "CodCurrency": None,
                    "GoodsCost": 100.0,
                    "GoodsCostCurrencyCode": None,
                    "Description1": "GARMENTS AND ACCESSORIES",
                    "Description2": "",
                    "Notes1": "",
                    "Notes2": "",
                    "Notes3": "",
                    "Notes4": "",
                    "Pieces": 1,
                    "RoundTrip": False,
                    "ShipmentType": 1,
                    "Weight": 1.0,
                    "CustomFeesType": None,
                    "PayType": 0,
                    "IsMultiPiece": None,
                    "ParentShipmentNo": None,
                    "ConsolidationNo": None,
                    "IsConsolidationClosed": None,
                    "Length": None,
                    "Width": None,
                    "Height": None,
                    "MeasurementType": None,
                    "ProductCode":"test"
                },
                "ShipmentShipper": {
                    "AccountNo": None,
                    "Reference1": "",
                    "Address": {
                        "LocationName": "Store Location",
                        "FullAddress": "Store Full Address",
                        "Phone": "+96512345678",
                        "CellNo": "+96512345678",
                        "ContactPerson": "Sender Name",
                        "LandMark": "KW",
                        "EncryptedAreaId": "8a25920e-72f0-47f2-9de4-e4eeed140e00",
                        "CountryCode": None,
                        "CityName": None,
                        "AreaName": None
                    }
                },
                "ShipmentConsignee": {
                    "ConsigneeName": "Receiver Name",
                    "ConsigneeCompany": "",  # إصلاح: string فارغ بدل من False
                    "Remarks": "",
                    "NationalCivilId": "",
                    "NationalLocationIdentification": "",
                    "Email": "receiver@abc.com",
                    "Address": {
                        "LocationName": "Receiver Location Name",
                        "FullAddress": "Receiver Full Address",
                        "Phone": "+96512345678",
                        "CellNo": "+96512345678",
                        "LandMark": "Full Land Mark details if any",
                        "EncryptedAreaId": "8a25920e-72f0-47f2-9de4-e4eeed140e00",
                        "CountryCode": None,
                        "CityName": None,
                        "AreaName": None
                    }
                },
                "Collection": {
                    "PickupDate": "06-APR-2023",
                    "Notes": "Test Pickup note",
                    "CollectionAddress": {
                        "LocationName": "Collection Location Name",
                        "FullAddress": "Collection Full Address",
                        "Phone": "+96512345678",
                        "CellNo": "+96512345678",
                        "LandMark": "Collection Landmark details if any",
                        "EncryptedAreaId": "8a25920e-72f0-47f2-9de4-e4eeed140e00",
                        "CountryCode": None,
                        "CityName": None,
                        "AreaName": None
                    }
                },
                "Packages": [
                    {
                        "PackageDescription": "test package 1",
                        "ActualWeight": 1.5,
                        "Length": 0,
                        "Width": 0,
                        "Height": 0
                    }
                ]
            }

            # Apply field mappings to override defaults
            for mapping in self.field_mapping_ids.filtered('is_active'):
                if not mapping.provider_field_path:
                    continue

                value = mapping.get_value_from_order(sale_order)

                # تجاهل القيم الفارغة للحقول النصية المطلوبة
                if value is not None:
                    # Handle special cases for Packages array
                    if mapping.provider_field_path.startswith('Packages.0.'):
                        field_name = mapping.provider_field_path.split('.')[-1]
                        if field_name in request_data["Packages"][0]:
                            request_data["Packages"][0][field_name] = value
                    else:
                        # Use the helper method to set nested values
                        self._set_value_in_dict_safe(request_data, mapping.provider_field_path, value)

            # تطبيق إصلاحات إضافية للحقول الحساسة
            self._apply_porter_fixes(request_data, sale_order)

            _logger.info(f"=== Final Porter request data ===")
            _logger.info(f"{json.dumps(request_data, indent=2, default=str)}")

            # Send request
            response = self.send_request('create', request_data)

            # Extract tracking number
            tracking_number = None
            if self.tracking_number_path:
                tracking_number = self._get_value_from_path(response, self.tracking_number_path)

            _logger.info(f"=== Porter shipment created successfully ===")
            _logger.info(f"Tracking: {tracking_number}")

            return {
                'success': True,
                'tracking_number': tracking_number,
                'response': response
            }

        except Exception as e:
            _logger.error(f"=== Error creating Porter shipment ===")
            _logger.error(f"Error: {str(e)}")
            _logger.error(f"Order: {sale_order.name}")
            raise Exception(f"Porter shipment creation failed: {str(e)}")

    def _set_value_in_dict_safe(self, data_dict, path, value):
        """Set value in nested dictionary with proper type conversion"""
        if not path:
            return

        keys = path.split('.')
        current = data_dict

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]

        # إصلاح نوع البيانات بناء على الحقل
        if value is not None:
            # Boolean fields
            if isinstance(value, bool):
                if final_key in ['ConsigneeCompany', 'Remarks', 'NationalCivilId', 'NationalLocationIdentification']:
                    # تحويل Boolean إلى string فارغ للحقول النصية
                    value = "" if not value else str(value)
                else:
                    value = bool(value)

            # String fields - تأكد إنها string
            elif final_key in ['ConsigneeCompany', 'Remarks', 'NationalCivilId', 'NationalLocationIdentification',
                               'LocationName', 'FullAddress', 'Phone', 'CellNo', 'ContactPerson', 'LandMark']:
                value = str(value) if value else ""

            # Numeric fields
            elif final_key in ['Pieces', 'ShipmentType', 'PayType']:
                try:
                    value = int(float(str(value)))
                except:
                    value = 1 if final_key == 'Pieces' else 0
            elif final_key in ['Weight', 'GoodsCost', 'CodAmount', 'ActualWeight']:
                try:
                    value = float(str(value))
                except:
                    value = 1.0

        current[final_key] = value

    def _apply_porter_fixes(self, request_data, sale_order):
        """Apply Porter-specific fixes to request data"""

        # إصلاح الحقول الحساسة
        fixes = {
            # Root level
            "model": "CustomerShipment",
            "Reference2": sale_order.name or "REF001",
            "ProductCode": "DE",

            # ShipmentDetail
            "ShipmentDetail.Description1": "GARMENTS AND ACCESSORIES",
            "ShipmentDetail.Pieces": 1,
            "ShipmentDetail.Weight": 1.0,
            "ShipmentDetail.GoodsCost": 100.0,
            "ShipmentDetail.ShipmentType": 1,
            "ShipmentDetail.PayType": 0,
            "ShipmentDetail.RoundTrip": False,

            # ShipmentShipper
            "ShipmentShipper.Reference1": sale_order.name or "SHIP_REF_001",
            "ShipmentShipper.Address.LocationName": "Store Location",
            "ShipmentShipper.Address.FullAddress": "Store Full Address",
            "ShipmentShipper.Address.Phone": "+96512345678",
            "ShipmentShipper.Address.CellNo": "+96512345678",
            "ShipmentShipper.Address.ContactPerson": "Sender Name",
            "ShipmentShipper.Address.LandMark": "KW",
            "ShipmentShipper.Address.EncryptedAreaId": "8a25920e-72f0-47f2-9de4-e4eeed140e00",

            # ShipmentConsignee - تأكد من النوع الصحيح
            "ShipmentConsignee.ConsigneeName": "Receiver Name",
            "ShipmentConsignee.ConsigneeCompany": "",  # String فارغ
            "ShipmentConsignee.Remarks": "",  # String فارغ
            "ShipmentConsignee.NationalCivilId": "",  # String فارغ
            "ShipmentConsignee.NationalLocationIdentification": "",  # String فارغ
            "ShipmentConsignee.Email": "receiver@abc.com",
            "ShipmentConsignee.Address.LocationName": "Receiver Location Name",
            "ShipmentConsignee.Address.FullAddress": "Receiver Full Address",
            "ShipmentConsignee.Address.Phone": "+96512345678",
            "ShipmentConsignee.Address.CellNo": "+96512345678",
            "ShipmentConsignee.Address.LandMark": "Full Land Mark details if any",
            "ShipmentConsignee.Address.EncryptedAreaId": "8a25920e-72f0-47f2-9de4-e4eeed140e00",

            # Collection
            "Collection.PickupDate": "06-APR-2023",
            "Collection.Notes": "Test Pickup note",
            "Collection.CollectionAddress.LocationName": "Collection Location Name",
            "Collection.CollectionAddress.FullAddress": "Collection Full Address",
            "Collection.CollectionAddress.Phone": "+96512345678",
            "Collection.CollectionAddress.CellNo": "+96512345678",
            "Collection.CollectionAddress.LandMark": "Collection Landmark details if any",
            "Collection.CollectionAddress.EncryptedAreaId": "8a25920e-72f0-47f2-9de4-e4eeed140e00",
        }

        # تطبيق الإصلاحات
        for path, default_value in fixes.items():
            current_value = self._get_value_from_path(request_data, path)

            # إصلاح القيم الخاطئة
            if (current_value is None or
                    current_value == False or
                    (isinstance(current_value, str) and current_value.strip() == "")):
                self._set_value_in_dict_safe(request_data, path, default_value)

        # تأكد من وجود الحقول المطلوبة
        if not request_data.get("Packages") or len(request_data["Packages"]) == 0:
            request_data["Packages"] = [{
                "PackageDescription": "test package 1",
                "ActualWeight": 1.5,
                "Length": 0,
                "Width": 0,
                "Height": 0
            }]
    def _set_value_in_dict(self, data_dict, path, value):
        """Set value in nested dictionary using dot notation"""
        keys = path.split('.')
        current = data_dict

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value
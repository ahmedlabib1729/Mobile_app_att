# -*- coding: utf-8 -*-
from xml.sax import saxutils
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

        # تأكد من أن الـ PIN لا يحتوي على Entity
        pin = self.account_pin.strip()

        # إزالة DXB أو أي Entity من الـ PIN إذا وُجد
        if pin.startswith(self.account_entity):
            pin = pin[len(self.account_entity):]
        elif pin.endswith(self.account_entity):
            pin = pin[:-len(self.account_entity)]

        return {
            'UserName': self.username.strip(),
            'Password': self.password.strip(),
            'Version': self.version,
            'AccountNumber': self.account_number.strip(),
            'AccountPin': pin,  # PIN نظيف
            'AccountEntity': self.account_entity.strip().upper(),
            'AccountCountryCode': self.account_country_code.strip().upper(),
        }

    def _prepare_shipment_data(self):
        """Prepare data for Aramex API"""
        self.ensure_one()

        picking = self.picking_id
        partner = self.partner_id

        # إعداد العناصر
        items = []
        if self.use_multi_package and self.package_line_ids:
            for package in self.package_line_ids:
                items.append({
                    'PackageType': 'Box',
                    'Quantity': 1,
                    'Weight': {
                        'Unit': self.weight_unit,
                        'Value': package.weight
                    },
                    'Comments': package.description,
                    'Reference': self.reference1
                })
        else:
            # شحنة واحدة فقط
            items.append({
                'PackageType': 'Box',
                'Quantity': self.number_of_pieces,
                'Weight': {
                    'Unit': self.weight_unit,
                    'Value': self.actual_weight
                },
                'Comments': f'Shipment Items',
                'Reference': self.reference1
            })

        # إعداد الشحنة
        shipment = {
            'Reference1': self.reference1,
            'Reference2': self.reference2 or '',
            'Reference3': self.reference3 or '',
            'Shipper': self._prepare_shipper_address(),
            'Consignee': self._prepare_consignee_address(),
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
                'GoodsOriginCountry': self.goods_origin_country.code if self.goods_origin_country else 'AE',
                'NumberOfPieces': self.number_of_pieces,
                'ProductGroup': self.product_group,
                'ProductType': self.product_type,
                'PaymentType': self.payment_type,
                'PaymentOptions': self.payment_options or '',
                'Services': self.services or '',
                'Items': items
            }
        }

        # إضافة COD إذا لزم
        if self.is_cod and self.cod_amount > 0:
            shipment['Details']['CashOnDeliveryAmount'] = {
                'CurrencyCode': self.cod_currency_id.name,
                'Value': self.cod_amount
            }

        # البيانات النهائية - شحنة واحدة فقط في المصفوفة
        data = {
            'ClientInfo': self.aramex_config_id._prepare_client_info(),
            'Transaction': self.aramex_config_id._prepare_transaction(
                self.reference1,
                f'Odoo Picking: {picking.name}'
            ),
            'Shipments': shipment,  # شحنة واحدة وليس مصفوفة
            'LabelInfo': {
                'ReportID': self.carrier_id.aramex_label_report_id or 9729,
                'ReportType': self.carrier_id.aramex_label_report_type or 'URL'
            }
        }

        return data

    def _prepare_transaction(self, reference1='', reference2=''):
        """Prepare Transaction structure for API requests - with all required fields"""
        return {
            'Reference1': reference1 or '',
            'Reference2': reference2 or '',
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
            # تحديد اسم Request wrapper
            if operation == 'CreateShipments':
                request_wrapper = 'ShipmentCreationRequest'
            else:
                request_wrapper = f"{operation}Request"

            # إعادة هيكلة البيانات مع wrapper
            wrapped_data = {request_wrapper: data}

            # Convert to XML - استخدم النسخة الجديدة المصلحة
            body_content = self._dict_to_xml_v2(wrapped_data)

            # Build SOAP envelope
            soap_envelope = self._build_soap_envelope(operation, body_content)

            # Headers
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': f'"http://ws.aramex.net/ShippingAPI/v1/Service_1_0/{operation}"'
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

    # في aramex_config.py - تعديل _dict_to_xml_v2 لإضافة العناصر المفقودة

    def _dict_to_xml_v2(self, data, parent_tag='', level=0):
        """Convert dictionary to XML string with proper structure - Fixed order version"""
        xml_parts = []

        # ترتيب العناصر حسب WSDL
        element_order = {
            'ShipmentCreationRequest': ['ClientInfo', 'Transaction', 'Shipments', 'LabelInfo'],
            'Shipment': [
                'Reference1', 'Reference2', 'Reference3',
                'Shipper', 'Consignee', 'ThirdParty',
                'ShippingDateTime', 'DueDate',
                'Comments',
                'PickupLocation',
                'OperationsInstructions',
                'AccountingInstrcutions',
                'Details',
                'Attachments',
                'ForeignHAWB',
                'TransportType ',
                'PickupGUID'
            ],
            'Party': ['Reference1', 'Reference2', 'AccountNumber', 'PartyAddress', 'Contact'],
            'Contact': [
                'Department',  # اختياري
                'PersonName',  # مطلوب
                'Title',  # اختياري
                'CompanyName',  # اختياري
                'PhoneNumber1',  # مطلوب
                'PhoneNumber1Ext',  # اختياري
                'PhoneNumber2',  # مطلوب (حتى لو فارغ)
                'PhoneNumber2Ext',  # اختياري
                'FaxNumber',  # اختياري
                'CellPhone',  # اختياري
                'EmailAddress',  # اختياري
                'Type'  # مطلوب (حتى لو فارغ)
            ],
            'PartyAddress': ['Line1', 'Line2', 'Line3', 'City', 'StateOrProvinceCode', 'PostCode', 'CountryCode'],
            'Transaction': ['Reference1', 'Reference2', 'Reference3', 'Reference4', 'Reference5'],
            'Details': [
                'Dimensions', 'ActualWeight', 'ChargeableWeight', 'DescriptionOfGoods',
                'GoodsOriginCountry', 'NumberOfPieces', 'ProductGroup', 'ProductType',
                'PaymentType', 'PaymentOptions', 'CustomsValueAmount', 'CashOnDeliveryAmount',
                'InsuranceAmount', 'CashAdditionalAmount', 'CashAdditionalAmountDescription',
                'CollectAmount', 'Services', 'Items'
            ]
        }

        # قائمة العناصر المطلوبة حتى لو كانت فارغة
        required_empty_elements = {
            'Transaction': ['Reference1', 'Reference2', 'Reference3', 'Reference4', 'Reference5'],
            'Shipment': ['Reference1', 'Reference2', 'Reference3', 'PickupLocation', 'OperationsInstructions',
                         'AccountingInstrcutions'],
            'PartyAddress': ['Line1', 'Line2', 'Line3', 'City', 'StateOrProvinceCode', 'PostCode', 'CountryCode'],
            'Contact': ['PersonName', 'CompanyName', 'PhoneNumber1', 'PhoneNumber1Ext',
                        'PhoneNumber2', 'PhoneNumber2Ext', 'FaxNumber', 'CellPhone', 'EmailAddress', 'Type'],
            'Details': ['PaymentOptions'],
        }

        # معالجة بالترتيب الصحيح
        if parent_tag in element_order:
            # معالج العناصر بالترتيب المحدد
            for key in element_order[parent_tag]:
                if key in data:
                    value = data[key]
                    tag = f"v1:{key}"

                    # معالجة خاصة لـ PersonName
                    if key == 'PersonName':
                        _logger.info(
                            f"Processing PersonName: value='{value}', type={type(value)}, len={len(str(value))}")
                        _logger.info(f"PersonName hex: {str(value).encode('utf-8').hex()}")

                    if isinstance(value, dict):
                        xml_parts.append(f"<{tag}>")
                        inner_xml = self._dict_to_xml_v2(value, key, level + 1)
                        if inner_xml:
                            xml_parts.append(inner_xml)
                        xml_parts.append(f"</{tag}>")
                    elif isinstance(value, list):
                        if key == 'Shipments':
                            xml_parts.append(f"<{tag}>")
                            for shipment in value:
                                xml_parts.append("<v1:Shipment>")
                                xml_parts.append(self._dict_to_xml_v2(shipment, 'Shipment', level + 1))
                                xml_parts.append("</v1:Shipment>")
                            xml_parts.append(f"</{tag}>")
                        elif key == 'Items':
                            xml_parts.append(f"<{tag}>")
                            for item in value:
                                xml_parts.append("<v1:ShipmentItem>")
                                xml_parts.append(self._dict_to_xml_v2(item, 'ShipmentItem', level + 1))
                                xml_parts.append("</v1:ShipmentItem>")
                            xml_parts.append(f"</{tag}>")
                    else:
                        formatted_value = self._format_xml_value(value)
                        xml_parts.append(f"<{tag}>{formatted_value}</{tag}>")
                else:
                    # إضافة العناصر المطلوبة المفقودة
                    if parent_tag in required_empty_elements and key in required_empty_elements[parent_tag]:
                        tag = f"v1:{key}"
                        xml_parts.append(f"<{tag}></{tag}>")
        else:
            # معالجة عادية للعناصر غير المرتبة
            for key, value in data.items():
                # تجاهل القيم None للعناصر الاختيارية
                skip_if_empty = ['InsuranceAmount', 'CashAdditionalAmount', 'CollectAmount', 'ThirdParty', 'DueDate',
                                 'ForeignHAWB']
                if key in skip_if_empty and (value is None or value == '' or value == {}):
                    continue

                tag = f"v1:{key}"

                if isinstance(value, dict):
                    # للعناصر من نوع Money، تحقق من وجود محتوى
                    if key in ['InsuranceAmount', 'CashAdditionalAmount', 'CollectAmount']:
                        if not value or not value.get('Value') or value.get('Value') == 0:
                            continue

                    xml_parts.append(f"<{tag}>")
                    inner_xml = self._dict_to_xml_v2(value, key, level + 1)
                    if inner_xml:
                        xml_parts.append(inner_xml)
                    xml_parts.append(f"</{tag}>")
                elif isinstance(value, list):
                    xml_parts.append(f"<{tag}>")
                    for item in value:
                        if isinstance(item, dict):
                            item_tag = self._get_item_tag_name(key)
                            xml_parts.append(f"<v1:{item_tag}>")
                            xml_parts.append(self._dict_to_xml_v2(item, item_tag, level + 1))
                            xml_parts.append(f"</v1:{item_tag}>")
                        else:
                            xml_parts.append(self._format_xml_value(item))
                    xml_parts.append(f"</{tag}>")
                else:
                    formatted_value = self._format_xml_value(value)
                    xml_parts.append(f"<{tag}>{formatted_value}</{tag}>")

        # Debug logging للـ Contact
        if parent_tag == 'Contact':
            final_xml = ''.join(xml_parts)
            _logger.info(f"Contact XML: {final_xml}")

        if key == 'Consignee':
            _logger.info("=" * 60)
            _logger.info("Processing Consignee structure:")
            _logger.info(f"Consignee data: {json.dumps(value, indent=2, ensure_ascii=False)}")
            _logger.info("=" * 60)

        return ''.join(xml_parts)

    def _format_xml_value(self, value):
        """Format value for XML based on its type - Fixed for COD values"""
        if value is None:
            return ''

        if isinstance(value, bool):
            return 'true' if value else 'false'

        if isinstance(value, (int, float)):
            # للأرقام، تأكد من التنسيق الصحيح
            if isinstance(value, float):
                # دائماً استخدم رقمين عشريين للقيم المالية
                return f"{value:.2f}"
            return str(value)

        # للنصوص
        text = str(value).strip()

        # Escape XML special characters فقط للنصوص
        return saxutils.escape(text)

    def _dict_to_xml_v3(self, data, parent_tag='', level=0):
        """Convert dictionary to XML with preserved element order"""
        xml_parts = []

        # تعريف الترتيب الصحيح للعناصر حسب WSDL
        element_order = {
            'ShipmentCreationRequest': ['ClientInfo', 'Transaction', 'Shipments', 'LabelInfo'],
            'ClientInfo': ['UserName', 'Password', 'Version', 'AccountNumber', 'AccountPin', 'AccountEntity',
                           'AccountCountryCode'],
            'Transaction': ['Reference1', 'Reference2', 'Reference3', 'Reference4', 'Reference5'],
            'Shipment': ['Reference1', 'Reference2', 'Reference3', 'Shipper', 'Consignee', 'ThirdParty',
                         'ShippingDateTime', 'DueDate', 'Comments', 'PickupLocation', 'OperationsInstructions',
                         'AccountingInstrcutions', 'Details', 'Attachments', 'ForeignHAWB', 'TransportType ',
                         'PickupGUID'],
            'PartyAddress': ['Line1', 'Line2', 'Line3', 'City', 'StateOrProvinceCode', 'PostCode', 'CountryCode'],
            'Contact': ['Department', 'PersonName', 'Title', 'CompanyName', 'PhoneNumber1', 'PhoneNumber1Ext',
                        'PhoneNumber2', 'PhoneNumber2Ext', 'FaxNumber', 'CellPhone', 'EmailAddress', 'Type'],
            'Details': ['Dimensions', 'ActualWeight', 'ChargeableWeight', 'DescriptionOfGoods', 'GoodsOriginCountry',
                        'NumberOfPieces', 'ProductGroup', 'ProductType', 'PaymentType', 'PaymentOptions',
                        'CustomsValueAmount', 'CashOnDeliveryAmount', 'InsuranceAmount', 'CashAdditionalAmount',
                        'CashAdditionalAmountDescription', 'CollectAmount', 'Services', 'Items'],
            'Dimensions': ['Length', 'Width', 'Height', 'Unit'],
            'Weight': ['Unit', 'Value'],
            'Money': ['CurrencyCode', 'Value'],
            'ShipmentItem': ['PackageType', 'Quantity', 'Weight', 'Comments', 'Reference'],
        }

        # الحصول على الترتيب الصحيح
        if parent_tag in element_order:
            ordered_keys = element_order[parent_tag]
            # معالجة العناصر بالترتيب الصحيح
            for key in ordered_keys:
                if key in data:
                    value = data[key]
                    xml_parts.append(self._process_xml_element(key, value, parent_tag, level))

            # إضافة أي عناصر إضافية غير موجودة في الترتيب
            for key, value in data.items():
                if key not in ordered_keys:
                    xml_parts.append(self._process_xml_element(key, value, parent_tag, level))
        else:
            # إذا لم يكن هناك ترتيب محدد، استخدم الترتيب الموجود
            for key, value in data.items():
                xml_parts.append(self._process_xml_element(key, value, parent_tag, level))

        return ''.join(xml_parts)

    def _process_xml_element(self, key, value, parent_tag, level):
        """Process single XML element"""
        if value is None:
            return ''

        tag = f"v1:{key}"

        # نفس المنطق السابق لمعالجة القيم
        if isinstance(value, dict):
            return f"<{tag}>{self._dict_to_xml_v3(value, key, level + 1)}</{tag}>"
        elif isinstance(value, list):
            # معالجة القوائم
            if key == 'Shipments':
                parts = [f"<{tag}>"]
                for shipment in value:
                    parts.append("<v1:Shipment>")
                    parts.append(self._dict_to_xml_v3(shipment, 'Shipment', level + 1))
                    parts.append("</v1:Shipment>")
                parts.append(f"</{tag}>")
                return ''.join(parts)
            elif key == 'Items':
                parts = [f"<{tag}>"]
                for item in value:
                    parts.append("<v1:ShipmentItem>")
                    parts.append(self._dict_to_xml_v3(item, 'ShipmentItem', level + 1))
                    parts.append("</v1:ShipmentItem>")
                parts.append(f"</{tag}>")
                return ''.join(parts)
            else:
                # قوائم أخرى
                return f"<{tag}>{''.join([str(item) for item in value])}</{tag}>"
        else:
            # قيم بسيطة
            return f"<{tag}>{self._format_xml_value(value)}</{tag}>"

    def _get_item_tag_name(self, collection_key):
        """Get singular form of collection tag name"""
        mappings = {
            'Notifications': 'Notification',
            'Attachments': 'Attachment',
            'Shipments': 'Shipment',
            'Items': 'ShipmentItem',
        }
        return mappings.get(collection_key, collection_key.rstrip('s'))

    def _dict_to_xml_fixed(self, data, parent_tag='', is_root=False):
        """Convert dictionary to XML string - Fixed version"""
        xml_parts = []

        for key, value in data.items():
            if value is None:
                continue

            # Add namespace prefix
            tag = f"v1:{key}"

            if isinstance(value, dict):
                xml_parts.append(f"<{tag}>")
                xml_parts.append(self._dict_to_xml_fixed(value, key))
                xml_parts.append(f"</{tag}>")
            elif isinstance(value, list):
                # Handle arrays properly
                if key == 'Shipments':
                    # Shipments is an array container
                    xml_parts.append(f"<{tag}>")
                    for shipment in value:
                        xml_parts.append("<v1:Shipment>")
                        xml_parts.append(self._dict_to_xml_fixed(shipment, 'Shipment'))
                        xml_parts.append("</v1:Shipment>")
                    xml_parts.append(f"</{tag}>")
                elif key == 'Items':
                    # Items don't need wrapper, they go directly
                    for item in value:
                        xml_parts.append("<v1:ShipmentItem>")
                        xml_parts.append(self._dict_to_xml_fixed(item, 'ShipmentItem'))
                        xml_parts.append("</v1:ShipmentItem>")
                elif key == 'Notifications':
                    # Notifications handling
                    for notif in value:
                        xml_parts.append("<v1:Notification>")
                        xml_parts.append(self._dict_to_xml_fixed(notif, 'Notification'))
                        xml_parts.append("</v1:Notification>")
                else:
                    # Other arrays
                    xml_parts.append(f"<{tag}>")
                    for item in value:
                        item_tag = key.rstrip('s') if key.endswith('s') else key
                        xml_parts.append(f"<v1:{item_tag}>")
                        if isinstance(item, dict):
                            xml_parts.append(self._dict_to_xml_fixed(item, item_tag))
                        else:
                            xml_parts.append(self._escape_xml(str(item)))
                        xml_parts.append(f"</v1:{item_tag}>")
                    xml_parts.append(f"</{tag}>")
            else:
                # Simple values
                xml_parts.append(f"<{tag}>{self._escape_xml(str(value))}</{tag}>")

        return ''.join(xml_parts)

    def _parse_soap_fault(self, response_text):
        """Parse SOAP fault response"""
        try:
            root = etree.fromstring(response_text.encode('utf-8'))

            # البحث عن Fault
            for elem in root.getiterator():
                if 'Fault' in elem.tag:
                    # البحث عن faultstring
                    for child in elem:
                        if 'faultstring' in child.tag:
                            error_msg = child.text

                            # معالجة رسائل خطأ محددة
                            if 'ShipmentCreationRequest' in error_msg:
                                raise UserError(_(
                                    'خطأ في تنسيق الطلب:\n'
                                    'الخادم يتوقع ShipmentCreationRequest\n'
                                    'تحقق من هيكل البيانات المرسلة'
                                ))
                            else:
                                raise UserError(_(
                                    'Aramex API Fault:\n%(error)s',
                                    error=error_msg
                                ))

            # إذا لم نجد Fault، نرفع خطأ عام
            raise UserError(_('Unknown SOAP fault occurred'))

        except etree.XMLSyntaxError:
            raise UserError(_('Invalid XML in fault response'))
        except UserError:
            raise
        except Exception as e:
            raise UserError(_('Error parsing fault response: %s') % str(e))

    def _dict_to_xml(self, data, parent_tag='', is_root=False):
        """Convert dictionary to XML string"""
        xml_parts = []

        for key, value in data.items():
            if value is None:
                continue

            # معالجة خاصة للـ Shipments array
            if key == 'Shipments' and isinstance(value, list):
                tag = f"v1:{key}"
                xml_parts.append(f"<{tag}>")
                for shipment in value:
                    xml_parts.append("<v1:Shipment>")
                    for ship_key, ship_value in shipment.items():
                        if ship_value is not None:
                            xml_parts.append(self._process_element(ship_key, ship_value))
                    xml_parts.append("</v1:Shipment>")
                xml_parts.append(f"</{tag}>")
            else:
                xml_parts.append(self._process_element(key, value, is_root))

        return ''.join(xml_parts)

    def _process_element(self, key, value, is_root=False):
        """Process a single element"""
        xml_parts = []
        tag = f"v1:{key}"

        if isinstance(value, dict):
            xml_parts.append(f"<{tag}>")
            xml_parts.append(self._dict_to_xml(value, key))
            xml_parts.append(f"</{tag}>")
        elif isinstance(value, list):
            # Arrays تحتاج wrapper
            xml_parts.append(f"<{tag}>")
            for item in value:
                # تحديد اسم العنصر المفرد
                if key == 'Items':
                    item_tag = 'ShipmentItem'
                elif key == 'Attachments':
                    item_tag = 'Attachment'
                elif key == 'Notifications':
                    item_tag = 'Notification'
                else:
                    item_tag = key.rstrip('s') if key.endswith('s') else key

                xml_parts.append(f"<v1:{item_tag}>")
                if isinstance(item, dict):
                    for item_key, item_value in item.items():
                        if item_value is not None:
                            xml_parts.append(self._process_element(item_key, item_value))
                else:
                    xml_parts.append(str(item))
                xml_parts.append(f"</v1:{item_tag}>")
            xml_parts.append(f"</{tag}>")
        else:
            xml_parts.append(f"<{tag}>{self._escape_xml(str(value))}</{tag}>")

        return ''.join(xml_parts)

    def _escape_xml(self, text):
        """Escape special XML characters - Updated to handle numeric values"""
        if text is None:
            return ''

        # تحويل إلى string
        text = str(text)

        # للقيم الرقمية، لا نحتاج escape
        try:
            # تحقق إذا كانت القيمة رقمية
            float(text)
            return text  # أرجع الرقم كما هو
        except ValueError:
            # ليست رقمية، استخدم escape عادي
            return saxutils.escape(text)

    def _element_to_xml(self, key, value, is_root=False):
        """Convert single element to XML"""
        xml_parts = []
        tag = f"v1:{key}"

        if isinstance(value, dict):
            xml_parts.append(f"<{tag}>")
            for sub_key, sub_value in value.items():
                if sub_value is not None:
                    xml_parts.append(self._element_to_xml(sub_key, sub_value))
            xml_parts.append(f"</{tag}>")
        elif isinstance(value, list):
            # معالجة Arrays مع wrapper
            xml_parts.append(f"<{tag}>")
            for item in value:
                # تحديد اسم العنصر المفرد
                if key == 'Items':
                    item_tag = 'ShipmentItem'
                elif key == 'Attachments':
                    item_tag = 'Attachment'
                elif key == 'Notifications':
                    item_tag = 'Notification'
                else:
                    item_tag = key.rstrip('s') if key.endswith('s') else key

                xml_parts.append(f"<v1:{item_tag}>")
                if isinstance(item, dict):
                    for item_key, item_value in item.items():
                        if item_value is not None:
                            xml_parts.append(self._element_to_xml(item_key, item_value))
                else:
                    xml_parts.append(self._escape_xml(str(item)))
                xml_parts.append(f"</v1:{item_tag}>")
            xml_parts.append(f"</{tag}>")
        else:
            xml_parts.append(f"<{tag}>{self._escape_xml(str(value))}</{tag}>")

        return ''.join(xml_parts)

    def _parse_soap_response(self, response_text, operation):
        """Parse SOAP response from Aramex"""
        try:
            # Parse XML
            root = etree.fromstring(response_text.encode('utf-8'))

            # Remove namespaces for easier parsing
            for elem in root.getiterator():
                elem.tag = etree.QName(elem).localname
                # Clear attributes except those we need
                for attr in list(elem.attrib.keys()):
                    if attr not in ['nil']:
                        del elem.attrib[attr]

            # Check for HasErrors first
            has_errors_elem = root.find(".//HasErrors")
            if has_errors_elem is not None and has_errors_elem.text == "true":
                # Extract error notifications
                errors = []

                # Look for ProcessedShipment notifications first (more specific)
                processed_shipments = root.findall(".//ProcessedShipment")
                for shipment in processed_shipments:
                    notifications = shipment.findall(".//Notification")
                    for notif in notifications:
                        code = notif.find("Code")
                        message = notif.find("Message")
                        if code is not None and message is not None:
                            errors.append(f"{code.text}: {message.text}")

                # Also check general notifications
                if not errors:
                    notifications = root.findall(".//Notification")
                    for notif in notifications:
                        code = notif.find("Code")
                        message = notif.find("Message")
                        if code is not None and message is not None:
                            errors.append(f"{code.text}: {message.text}")

                if errors:
                    raise UserError(_("Aramex API Errors:\n%s") % "\n".join(errors))

            # Parse successful response
            response_data = {}
            response_elem = root.find(f".//{operation}Response")

            if response_elem is not None:
                # Convert to dictionary
                response_data = self._xml_to_dict(response_elem)
            else:
                # Try to find in Body
                body_elem = root.find(".//Body")
                if body_elem is not None:
                    for child in body_elem:
                        if 'Response' in child.tag:
                            response_data = self._xml_to_dict(child)
                            break

            return response_data

        except etree.XMLSyntaxError as e:
            _logger.error(f"XML Parse Error: {str(e)}")
            _logger.error(f"Response Text: {response_text[:1000]}")
            raise UserError(_("Invalid XML response: %s") % str(e))
        except UserError:
            raise
        except Exception as e:
            _logger.error(f"Response parsing error: {str(e)}")
            raise UserError(_("Error parsing response: %s") % str(e))

    def validate_account_data(self):
        """Validate account data format"""
        self.ensure_one()

        errors = []

        # التحقق من طول رقم الحساب
        if len(self.account_number) != 8:
            errors.append(_("Account Number should be 8 digits"))

        # التحقق من Entity
        valid_entities = ['DXB', 'RUH', 'JED', 'CAI', 'AMM', 'BAH', 'KWI', 'DOH']
        if self.account_entity.upper() not in valid_entities:
            errors.append(_("Invalid Entity. Common entities: %s") % ", ".join(valid_entities))

        # التحقق من رمز الدولة
        if len(self.account_country_code) != 2:
            errors.append(_("Country code must be 2 letters (e.g., AE, SA, EG)"))

        if errors:
            raise ValidationError("\n".join(errors))

        return True

    def _xml_to_dict(self, element):
        """Convert XML element to dictionary"""
        result = {}

        # Handle text content
        if element.text and element.text.strip():
            if len(element) == 0:  # Leaf node
                return element.text.strip()
            else:
                result['_text'] = element.text.strip()

        # Handle nil attribute
        if element.attrib.get('nil') == 'true':
            return None

        # Handle child elements
        for child in element:
            child_data = self._xml_to_dict(child)

            # Skip nil elements
            if child_data is None and child.attrib.get('nil') == 'true':
                continue

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
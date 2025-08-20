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

    products_summary = fields.Text(
        string='ملخص المنتجات',
        compute='_compute_products_summary',
        store=False
    )

    # ========== Compute Methods ==========

    @api.depends('picking_id', 'picking_id.move_ids')
    def _compute_products_summary(self):
        """حساب ملخص المنتجات للعرض"""
        for wizard in self:
            if wizard.picking_id:
                lines = []
                for move in wizard.picking_id.move_ids:
                    qty = move.quantity if wizard.picking_id.state == 'done' else move.product_uom_qty
                    if qty > 0:
                        product_name = move.product_id.name
                        if move.product_id.default_code:
                            product_name = f"[{move.product_id.default_code}] {product_name}"
                        lines.append(f"{int(qty)} X {product_name}")

                wizard.products_summary = '\n'.join(lines) if lines else 'No products'
            else:
                wizard.products_summary = ''

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

        # التحقق من البيانات المطلوبة
        if not self.partner_id.city:
            errors.append(_('Consignee city is required'))

        if not self.partner_id.country_id:
            errors.append(_('Consignee country is required'))

        if not (self.partner_id.phone or self.partner_id.mobile):
            errors.append(_('Consignee phone number is required'))

        # التحقق من القيمة المعلنة للشحنات الدولية
        if self.partner_id.country_id.code != 'AE':  # شحنة دولية
            if not self.customs_value_amount and not self.picking_id.sale_id:
                errors.append(_('Declared/Customs value is required for international shipments'))

        # التحقق من COD
        if self.is_cod:
            if self.cod_amount <= 0:
                errors.append(_('COD amount must be greater than 0'))
            if not self.cod_currency_id:
                errors.append(_('COD currency is required'))

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

    # في ملف aramex_delivery/wizards/aramex_shipment_wizard.py
    # استبدل دالة _prepare_shipment_data بهذه النسخة المصلحة

    def _prepare_shipment_data(self):
        """Prepare data for Aramex API - Fixed version"""
        self.ensure_one()

        picking = self.picking_id
        partner = self.partner_id

        # حساب القيمة المعلنة (Declared Value)
        declared_value = 0
        currency_code = 'AED'

        if hasattr(self, 'customs_value_amount') and self.customs_value_amount:
            declared_value = self.customs_value_amount
            currency_code = self.customs_value_currency.name if self.customs_value_currency else 'AED'
        elif picking.sale_id:
            declared_value = picking.sale_id.amount_untaxed
            currency_code = picking.sale_id.currency_id.name
        else:
            for move in picking.move_ids:
                qty = move.quantity if picking.state == 'done' else move.product_uom_qty
                if move.sale_line_id:
                    price = move.sale_line_id.price_unit
                else:
                    price = move.product_id.lst_price
                declared_value += qty * price
            currency_code = self.company_id.currency_id.name

        # إعداد وصف تفصيلي للمنتجات
        product_descriptions = []
        detailed_items_description = []

        for move in picking.move_ids:
            qty = move.quantity if picking.state == 'done' else move.product_uom_qty
            if qty > 0:
                product_name = move.product_id.name
                if move.product_id.default_code:
                    product_name = f"{move.product_id.default_code} - {product_name}"

                item_desc = f"{int(qty)} X {product_name}"
                detailed_items_description.append(item_desc)
                product_descriptions.append(product_name)

        # دمج الوصف التفصيلي
        full_description = ' + '.join(
            detailed_items_description) if detailed_items_description else self.description_of_goods

        # إعداد Description of Goods
        if product_descriptions:
            description_of_goods = ', '.join(product_descriptions[:3])
            if len(product_descriptions) > 3:
                description_of_goods += f' +{len(product_descriptions) - 3} more'
        else:
            description_of_goods = self.description_of_goods

        # إعداد Comments/Remarks
        remarks = []

        if detailed_items_description:
            remarks.append(full_description)

        if self.comments:
            remarks.append(self.comments)

        if self.is_cod and self.cod_amount > 0:
            remarks.append(f"COD: {self.cod_amount} {self.cod_currency_id.name if self.cod_currency_id else 'AED'}")

        final_remarks = ' | '.join(remarks) if remarks else ''

        # إعداد الخدمات
        services_list = []
        if self.services:
            services_list = [s.strip().upper() for s in self.services.split(',')]

        # إضافة خدمة COD تلقائياً إذا كانت مطلوبة
        if self.is_cod and self.cod_amount > 0:
            if 'CODS' not in services_list:
                services_list.append('CODS')

        # إعداد قائمة المنتجات (Items)
        items = []
        total_item_weight = 0

        for move in picking.move_ids:
            qty = move.quantity if picking.state == 'done' else move.product_uom_qty
            if qty > 0:
                item_description = move.product_id.name
                if move.product_id.default_code:
                    item_description = f"{move.product_id.default_code} - {item_description}"

                item_weight = (move.product_id.weight or 0.1) * qty
                total_item_weight += item_weight

                items.append({
                    'PackageType': 'Box',
                    'Quantity': int(qty),
                    'Weight': {
                        'Unit': self.weight_unit,
                        'Value': round(item_weight, 2)
                    },
                    'Comments': item_description[:50],
                    'Reference': move.product_id.default_code or self.reference1
                })

        # إذا لم توجد items أو كان الوزن مختلف
        if not items or abs(total_item_weight - self.actual_weight) > 0.1:
            items = [{
                'PackageType': 'Box',
                'Quantity': self.number_of_pieces,
                'Weight': {
                    'Unit': self.weight_unit,
                    'Value': round(self.actual_weight / self.number_of_pieces,
                                   2) if self.number_of_pieces > 0 else self.actual_weight
                },
                'Comments': full_description[:50] if detailed_items_description else self.description_of_goods[:50],
                'Reference': self.reference1
            }]

        # تحديد Payment Type و Payment Options للـ COD
        payment_type = self.payment_type
        payment_options = ''

        if self.is_cod and self.cod_amount > 0:
            payment_type = 'P'  # Prepaid للشحن
            payment_options = ''

        # إعداد Details dictionary أولاً
        details = {
            'Dimensions': {
                'Length': self.length or 0,
                'Width': self.width or 0,
                'Height': self.height or 0,
                'Unit': self.dimensions_unit or 'CM'
            },
            'ActualWeight': {
                'Unit': self.weight_unit,
                'Value': round(self.actual_weight, 2)
            },
            'ChargeableWeight': {
                'Unit': self.weight_unit,
                'Value': round(self.actual_weight, 2)
            },
            'DescriptionOfGoods': description_of_goods[:100],
            'GoodsOriginCountry': self.goods_origin_country.code if self.goods_origin_country else 'AE',
            'NumberOfPieces': self.number_of_pieces,
            'ProductGroup': self.product_group,
            'ProductType': self.product_type,
            'PaymentType': payment_type,
            'PaymentOptions': payment_options or '',
            'Services': ','.join(services_list) if services_list else '',
            'Items': items
        }

        # إضافة CustomsValueAmount إذا كانت موجودة
        if declared_value > 0:
            details['CustomsValueAmount'] = {
                'CurrencyCode': currency_code,
                'Value': round(declared_value, 2)
            }

        # إضافة CashOnDeliveryAmount إذا كانت موجودة
        if self.is_cod and self.cod_amount and float(self.cod_amount) > 0:
            details['CashOnDeliveryAmount'] = {
                'CurrencyCode': self.cod_currency_id.name if self.cod_currency_id else 'AED',
                'Value': round(float(self.cod_amount), 2)
            }

        # عدم إضافة InsuranceAmount إلا إذا كانت لها قيمة صحيحة
        if hasattr(self, 'insurance_amount') and self.insurance_amount and self.insurance_amount > 0:
            if self.insurance_currency:
                details['InsuranceAmount'] = {
                    'CurrencyCode': self.insurance_currency.name,
                    'Value': round(self.insurance_amount, 2)
                }
        # إذا لم تكن هناك قيمة تأمين، لا نضيف InsuranceAmount نهائياً

        # عدم إضافة CashAdditionalAmount إلا إذا كانت لها قيمة
        if hasattr(self, 'cash_additional_amount') and self.cash_additional_amount and self.cash_additional_amount > 0:
            details['CashAdditionalAmount'] = {
                'CurrencyCode': self.cod_currency_id.name if self.cod_currency_id else 'AED',
                'Value': round(self.cash_additional_amount, 2)
            }
            if hasattr(self, 'cash_additional_amount_description'):
                details['CashAdditionalAmountDescription'] = self.cash_additional_amount_description or ''

        # عدم إضافة CollectAmount إلا إذا كانت لها قيمة
        if hasattr(self, 'collect_amount') and self.collect_amount and self.collect_amount > 0:
            details['CollectAmount'] = {
                'CurrencyCode': self.cod_currency_id.name if self.cod_currency_id else 'AED',
                'Value': round(self.collect_amount, 2)
            }

        # إعداد الشحنة الرئيسية
        shipment = {
            'Reference1': self.reference1,
            'Reference2': self.reference2 or '',
            'Reference3': self.reference3 or '',
            'Shipper': self._prepare_shipper_address(),
            'Consignee': self._prepare_consignee_address(),
            'ShippingDateTime': self.shipping_datetime.strftime('%Y-%m-%dT%H:%M:%S'),
            'Comments': final_remarks[:500] if final_remarks else '',
            'PickupLocation': self.pickup_location or '',
            'OperationsInstructions': '',
            'AccountingInstrcutions': '',  # مع الخطأ المطبعي في WSDL
            'Details': details
        }

        # إضافة Due Date إذا كانت محددة
        if self.due_date:
            shipment['DueDate'] = self.due_date.strftime('%Y-%m-%dT%H:%M:%S')

        # إضافة Foreign HAWB إذا كان موجوداً
        if self.foreign_hawb:
            shipment['ForeignHAWB'] = self.foreign_hawb

        # البيانات النهائية للطلب
        data = {
            'ClientInfo': self.aramex_config_id._prepare_client_info(),
            'Transaction': self.aramex_config_id._prepare_transaction(
                self.reference1,
                f'Odoo Picking: {picking.name}'
            ),
            'Shipments': [shipment],  # Array من الشحنات
            'LabelInfo': {
                'ReportID': self.carrier_id.aramex_label_report_id or 9729,
                'ReportType': self.carrier_id.aramex_label_report_type or 'URL'
            }
        }

        # Debug logging
        if self.aramex_config_id.debug_mode:
            _logger.info("=" * 60)
            _logger.info("Prepared Shipment Data:")
            _logger.info(json.dumps(data, indent=2, default=str, ensure_ascii=False))
            _logger.info("=" * 60)

        return data



    def _clean_phone_number(self, phone, remove_country_code=True, country_code=None):
        """
        تنظيف رقم الهاتف لـ Aramex
        Aramex يريد الرقم المحلي فقط بدون كود الدولة

        Args:
            phone: رقم الهاتف الأصلي
            remove_country_code: إزالة كود الدولة (افتراضي True لـ Aramex)
            country_code: كود الدولة للمساعدة في التنظيف

        Returns:
            رقم نظيف بدون كود الدولة
        """
        if not phone:
            return ''

        # تحويل لـ string
        phone = str(phone)

        # إزالة كل الرموز غير الأرقام
        cleaned = ''.join(filter(str.isdigit, phone))

        # إزالة 00 من البداية
        if cleaned.startswith('00'):
            cleaned = cleaned[2:]

        # تحديد كود الدولة
        if not country_code and self.partner_id and self.partner_id.country_id:
            country_code = self.partner_id.country_id.code

        # إزالة أكواد الدول الشائعة
        country_prefixes = {
            '971': 'AE',  # الإمارات
            '966': 'SA',  # السعودية
            '20': 'EG',  # مصر
            '965': 'KW',  # الكويت
            '974': 'QA',  # قطر
            '973': 'BH',  # البحرين
            '968': 'OM',  # عمان
            '962': 'JO',  # الأردن
            '961': 'LB',  # لبنان
            '212': 'MA',  # المغرب
            '216': 'TN',  # تونس
            '213': 'DZ',  # الجزائر
        }

        if remove_country_code:
            # إزالة كود الدولة من البداية
            for prefix, code in country_prefixes.items():
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix):]
                    break

            # إزالة 0 من البداية إذا وجد (للأرقام المحلية)
            if cleaned.startswith('0'):
                cleaned = cleaned[1:]

        return cleaned

    # في ملف aramex_delivery/wizards/aramex_shipment_wizard.py
    # عدّل دالة _prepare_shipper_address لإضافة Sale Order في Reference1

    def _prepare_shipper_address(self):
        """Prepare shipper address data with Sale Order reference"""

        # الحصول على رقم Sale Order
        sale_order_ref = ''
        if self.picking_id and self.picking_id.sale_id:
            sale_order_ref = self.picking_id.sale_id.name  # مثلاً: SO12345

        if self.use_warehouse_address:
            warehouse = self.picking_id.picking_type_id.warehouse_id
            if warehouse and warehouse.partner_id:
                partner = warehouse.partner_id
            else:
                partner = self.company_id.partner_id

            shipper_name = warehouse.name if warehouse else self.company_id.name
            shipper_company = self.company_id.name
            shipper_phone = self._clean_phone_number(
                partner.phone or partner.mobile or '0000000000',
                remove_country_code=True,
                country_code='AE'
            )
            shipper_email = partner.email or ''

            street_address = partner.street or 'Address'
            street2 = partner.street2 or ''
            city = partner.city or 'Dubai'
            state_code = partner.state_id.code if partner.state_id else ''
            zip_code = partner.zip or ''
            country_code = partner.country_id.code if partner.country_id else self.company_id.country_id.code or 'AE'
        else:
            shipper_name = self.shipper_name or 'Shipper'
            shipper_company = self.shipper_company or self.shipper_name or 'Company'
            shipper_phone = self._clean_phone_number(
                self.shipper_phone or '0000000000',
                remove_country_code=True,
                country_code='AE'
            )
            shipper_email = self.shipper_email or ''

            if self.shipper_address:
                address_lines = self.shipper_address.split('\n')
                street_address = address_lines[0] if len(address_lines) > 0 else 'Address'
                street2 = address_lines[1] if len(address_lines) > 1 else ''
                city = address_lines[2] if len(address_lines) > 2 else 'Dubai'
                state_code = ''
                zip_code = ''
            else:
                street_address = 'Address'
                street2 = ''
                city = 'Dubai'
                state_code = ''
                zip_code = ''

            country_code = self.company_id.country_id.code if self.company_id.country_id else 'AE'

        # بناء البيانات
        data = {
            'Reference1': sale_order_ref[:50],  # ← هنا! رقم Sale Order في Shipper Reference1
            'Reference2': '',  # يمكنك إضافة معلومات إضافية هنا إذا أردت
            'AccountNumber': self.aramex_config_id.account_number,
            'PartyAddress': {
                'Line1': street_address[:50],
                'Line2': street2[:50] if street2 else '',
                'Line3': '',
                'City': city[:50],
                'StateOrProvinceCode': state_code[:50] if state_code else '',
                'PostCode': self._validate_and_fix_postal_code(zip_code, country_code)[:20],
                'CountryCode': country_code
            },
            'Contact': {
                'Department': '',
                'PersonName': shipper_name[:50],
                'Title': '',
                'CompanyName': shipper_company[:50],
                'PhoneNumber1': shipper_phone or '0000000000',
                'PhoneNumber1Ext': '',
                'PhoneNumber2': '',
                'PhoneNumber2Ext': '',
                'FaxNumber': '',
                'CellPhone': shipper_phone or '0000000000',
                'EmailAddress': shipper_email[:50] if shipper_email else '',
                'Type': ''
            }
        }

        if self.aramex_config_id.debug_mode:
            _logger.info(f"Shipper Data with Sale Order Reference: {sale_order_ref}")
            _logger.info(json.dumps(data, indent=2))

        return data

    def _prepare_consignee_address(self):
        """Prepare consignee address data - FINAL FIX with CompanyName"""
        partner = self.partner_id

        # تنظيف أرقام الهاتف
        phone1 = self._clean_phone_number(
            partner.phone or partner.mobile or '0000000000',
            remove_country_code=True,
            country_code=partner.country_id.code if partner.country_id else 'AE'
        )

        cell_phone = self._clean_phone_number(
            partner.mobile or partner.phone or '0000000000',
            remove_country_code=True,
            country_code=partner.country_id.code if partner.country_id else 'AE'
        )

        # تنظيف الاسم
        consignee_name = partner.name or 'Customer'
        consignee_name = ' '.join(consignee_name.split())

        if not consignee_name or len(consignee_name.strip()) < 2:
            consignee_name = 'Customer'

        # تحديد اسم الشركة - مهم جداً!
        # إذا كان هناك parent company، استخدمها
        # وإلا، استخدم نفس اسم الشخص (حسب دليل Aramex: "Company or Person name")
        company_name = ''
        if partner.parent_id:
            company_name = partner.parent_id.name[:50]
        elif partner.is_company:
            company_name = partner.name[:50]
        else:
            # إذا كان فرد وليس شركة، ضع اسمه في CompanyName أيضاً
            # لأن Aramex يتطلب CompanyName دائماً
            company_name = consignee_name[:50]

        # Debug
        if self.aramex_config_id.debug_mode:
            _logger.info(f"Consignee Final Check:")
            _logger.info(f"  PersonName: '{consignee_name}'")
            _logger.info(f"  CompanyName: '{company_name}'")
            _logger.info(f"  Phone1: '{phone1}'")

        # بناء البيانات بالترتيب الصحيح
        data = {
            'Reference1': '',  # مطلوب أولاً حتى لو فارغ
            'Reference2': '',  # مطلوب ثانياً حتى لو فارغ
            'AccountNumber': '',  # مطلوب ثالثاً حتى لو فارغ
            'PartyAddress': {
                'Line1': (partner.street or 'Address')[:50],
                'Line2': (partner.street2 or '')[:50],
                'Line3': '',  # مطلوب فارغ
                'City': (partner.city or 'Dubai')[:50],
                'StateOrProvinceCode': (partner.state_id.code if partner.state_id else '')[:50],
                'PostCode': self._validate_and_fix_postal_code(
                    partner.zip,
                    partner.country_id.code if partner.country_id else 'AE'
                )[:20],
                'CountryCode': partner.country_id.code if partner.country_id else 'AE'
            },
            'Contact': {
                'Department': '',  # اختياري
                'PersonName': consignee_name[:50],  # مطلوب
                'Title': '',  # اختياري
                'CompanyName': company_name,  # مطلوب - لا يمكن أن يكون فارغ!
                'PhoneNumber1': phone1 or '0000000000',  # مطلوب
                'PhoneNumber1Ext': '',  # مطلوب فارغ
                'PhoneNumber2': '',  # مطلوب فارغ (يمكن أن يكون فارغ)
                'PhoneNumber2Ext': '',  # مطلوب فارغ
                'FaxNumber': '',  # مطلوب فارغ (يمكن أن يكون فارغ)
                'CellPhone': cell_phone or phone1 or '0000000000',  # مطلوب
                'EmailAddress': (partner.email[:50] if partner.email else '') or '',
                'Type': ''  # مطلوب فارغ
            }
        }

        if self.aramex_config_id.debug_mode:
            _logger.info("Final Consignee Data with CompanyName:")
            _logger.info(json.dumps(data, indent=2, ensure_ascii=False))

        return data
    def _validate_and_fix_postal_code(self, postal_code, country_code):
        """Validate and fix postal code based on country requirements"""
        if not postal_code:
            postal_code = ''

        postal_code = str(postal_code).strip()

        # قواعد خاصة لبعض الدول
        postal_requirements = {
            'AE': {'default': '00000', 'min_length': 5},  # الإمارات
            'SA': {'default': '00000', 'min_length': 5},  # السعودية
            'KW': {'default': '00000', 'min_length': 5},  # الكويت
            'QA': {'default': '00000', 'min_length': 5},  # قطر
            'BH': {'default': '0000', 'min_length': 4},  # البحرين
            'OM': {'default': '000', 'min_length': 3},  # عمان
            'EG': {'default': '00000', 'min_length': 5},  # مصر
        }

        requirements = postal_requirements.get(country_code, {'default': '00000', 'min_length': 5})

        # إذا كان الرمز البريدي فارغ أو قصير جداً
        if not postal_code or postal_code in ['0', '00', '000', '0000']:
            return requirements['default']

        # إذا كان الرمز البريدي يحتوي على أحرف غير رقمية في دول الخليج
        if country_code in ['AE', 'SA', 'KW', 'QA', 'BH', 'OM']:
            # احتفظ بالأرقام فقط
            numeric_postal = ''.join(filter(str.isdigit, postal_code))
            if numeric_postal and numeric_postal != '0':
                # أكمل بالأصفار إذا كان قصير
                while len(numeric_postal) < requirements['min_length']:
                    numeric_postal = '0' + numeric_postal  # أضف أصفار في البداية
                return numeric_postal[:requirements['min_length']]
            else:
                return requirements['default']

        return postal_code or requirements['default']

    def _process_shipment_response(self, response):
        """Process API response and create shipment record - FIXED"""
        self.ensure_one()

        # Check for errors
        has_errors = response.get('HasErrors', False)

        # معالجة HasErrors - قد يكون string أو boolean
        if isinstance(has_errors, str):
            has_errors = has_errors.lower() == 'true'

        if has_errors:
            # معالجة الأخطاء
            notifications = response.get('Notifications')
            if notifications:
                # تحويل لـ list إذا كان dict
                if isinstance(notifications, dict):
                    notifications = [notifications]
                elif notifications is None:
                    notifications = []

                error_messages = []
                for notif in notifications:
                    if notif:  # تحقق من أن notif ليس None
                        code = notif.get('Code', '')
                        message = notif.get('Message', '')
                        if code or message:
                            error_messages.append(f"{code}: {message}")

                if error_messages:
                    raise UserError(_(
                        'Aramex API returned errors:\n%s'
                    ) % '\n'.join(error_messages))

            # إذا لم تكن هناك رسائل خطأ محددة
            raise UserError(_('Aramex API returned an error but no specific message'))

        # معالجة الاستجابة الناجحة
        shipments = response.get('Shipments')
        if not shipments:
            raise UserError(_('No shipment data in response!'))

        # الحصول على بيانات الشحنة
        if isinstance(shipments, dict):
            # إذا كان Shipments dict، نبحث عن ProcessedShipment
            processed_shipment = shipments.get('ProcessedShipment')
            if not processed_shipment:
                raise UserError(_('No processed shipment in response!'))
            shipment_data = processed_shipment
        elif isinstance(shipments, list):
            # إذا كان list
            if len(shipments) == 0:
                raise UserError(_('Empty shipments list in response!'))
            shipment_data = shipments[0]
        else:
            shipment_data = shipments

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
            'cod_currency': self.cod_currency_id.id if self.is_cod and self.cod_currency_id else False,
            'customs_value_amount': self.customs_value_amount if self.customs_value_amount else 0,
            'customs_value_currency': self.customs_value_currency.id if self.customs_value_currency else False,
            'insurance_amount': self.insurance_amount if hasattr(self, 'insurance_amount') else 0,
            'insurance_currency': self.insurance_currency.id if hasattr(self,
                                                                        'insurance_currency') and self.insurance_currency else False,
            'foreign_hawb': self.foreign_hawb if self.foreign_hawb else False,
            'comments': self.comments if self.comments else '',
            'pickup_date': self.shipping_datetime.date() if self.shipping_datetime else fields.Date.today(),
            'state': 'confirmed',
            'company_id': self.company_id.id,
        }

        # Add shipper/consignee info
        # إعداد بيانات الشاحن
        shipper_data = self._prepare_shipper_address()
        shipment_vals.update({
            'shipper_name': shipper_data['Contact']['PersonName'],
            'shipper_company': shipper_data['Contact']['CompanyName'],
            'shipper_phone': shipper_data['Contact']['PhoneNumber1'],
            'shipper_email': shipper_data['Contact'].get('EmailAddress', ''),
            'shipper_address': f"{shipper_data['PartyAddress']['Line1']}\n{shipper_data['PartyAddress'].get('Line2', '')}\n{shipper_data['PartyAddress']['City']}, {shipper_data['PartyAddress']['CountryCode']}",
            'shipper_country_code': shipper_data['PartyAddress']['CountryCode'],
        })

        # إعداد بيانات المستلم
        consignee_data = self._prepare_consignee_address()
        shipment_vals.update({
            'consignee_name': consignee_data['Contact']['PersonName'],
            'consignee_company': consignee_data['Contact']['CompanyName'],
            'consignee_phone': consignee_data['Contact']['PhoneNumber1'],
            'consignee_email': consignee_data['Contact'].get('EmailAddress', ''),
            'consignee_address': f"{consignee_data['PartyAddress']['Line1']}\n{consignee_data['PartyAddress'].get('Line2', '')}\n{consignee_data['PartyAddress']['City']}, {consignee_data['PartyAddress']['CountryCode']}",
            'consignee_country_code': consignee_data['PartyAddress']['CountryCode'],
        })

        # Get label if available
        shipment_label = shipment_data.get('ShipmentLabel')
        if shipment_label:
            if isinstance(shipment_label, dict):
                if shipment_label.get('LabelFileContents'):
                    shipment_vals['label_pdf'] = shipment_label['LabelFileContents']
                    shipment_vals['label_filename'] = f'Aramex_Label_{awb_number}.pdf'
                if shipment_label.get('LabelURL'):
                    shipment_vals['label_url'] = shipment_label['LabelURL']

        # إضافة API response للـ debugging
        shipment_vals['api_response'] = str(response)[:5000] if self.aramex_config_id.debug_mode else ''

        # Create shipment
        aramex_shipment = self.env['aramex.shipment'].create(shipment_vals)

        # Link to picking
        self.picking_id.aramex_shipment_id = aramex_shipment

        # Add note to picking
        note_body = _(
            '<b>✅ Aramex shipment created successfully!</b><br/>'
            '<b>AWB Number:</b> %(awb)s<br/>'
            '<b>Service:</b> %(service)s<br/>'
            '<b>Weight:</b> %(weight).2f %(unit)s<br/>'
            '<b>Pieces:</b> %(pieces)d',
            awb=awb_number,
            service=dict(self._fields['product_type'].selection).get(self.product_type, self.product_type),
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

        if shipment_vals.get('label_url'):
            note_body += _(
                '<br/><b>Label URL:</b> <a href="%(url)s" target="_blank">Download Label</a>',
                url=shipment_vals['label_url']
            )

        self.picking_id.message_post(
            body=note_body,
            subject=_('Aramex Shipment Created'),
            message_type='notification'
        )

        # Show success message with label link
        success_message = _(
            '✅ Aramex shipment created successfully!\n'
            'AWB Number: %(awb)s\n',
            awb=awb_number
        )

        if shipment_vals.get('label_url'):
            success_message += _('\nLabel URL: %(url)s', url=shipment_vals['label_url'])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success! 🎉'),
                'message': success_message,
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
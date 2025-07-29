import json
import base64
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PorterShipmentWizard(models.TransientModel):
    _name = 'porter.shipment.wizard'
    _description = 'Porter Shipment Creation Wizard'

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
    reference2 = fields.Char(
        string='Reference',
        required=True,
        help='Your internal reference for this shipment'
    )

    # Service Details
    product_code = fields.Selection([
        ('DE', 'Delivery Express'),
        ('SD', 'Same Day'),
        ('ND', 'Next Day'),
    ], string='Service Type', required=True)

    # ========== إضافة حقول المنطقة الجديدة ==========
    partner_country_id = fields.Many2one(
        'res.country',
        string='Delivery Country',
        compute='_compute_partner_country',
        store=True
    )

    consignee_area_id = fields.Many2one(
        'porter.area',
        string='Delivery Area',
        required=True,
        domain="[('country_id', '=', partner_country_id), ('active', '=', True)]",
        help='Select the delivery area for the customer'
    )

    # Collection area (for pickup)
    collection_country_id = fields.Many2one(
        'res.country',
        string='Collection Country',
        compute='_compute_collection_country',
        store=True
    )

    collection_area_id = fields.Many2one(
        'porter.area',
        string='Collection Area',
        domain="[('country_id', '=', collection_country_id), ('active', '=', True)]",
        help='Select the collection area for pickup'
    )
    # ================================================

    # Package Information
    pieces = fields.Integer(
        string='Number of Pieces',
        default=1,
        required=True
    )

    weight = fields.Float(
        string='Total Weight (KG)',
        required=True,
        compute='_compute_weight',
        store=True,
        readonly=False
    )

    # Shipment Details
    description1 = fields.Char(
        string='Description',
        required=True,
        default='GENERAL GOODS'
    )

    description2 = fields.Char(string='Additional Description')

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

    # Pickup Information
    pickup_date = fields.Date(
        string='Pickup Date',
        required=True,
        default=lambda self: fields.Date.today()
    )

    auto_create_pickup = fields.Boolean(
        string='Create Pickup Request',
        default=True
    )

    # Collection Address
    use_warehouse_address = fields.Boolean(
        string='Use Warehouse Address',
        default=True
    )

    collection_name = fields.Char(string='Collection Location Name')
    collection_address = fields.Text(string='Collection Address')
    collection_phone = fields.Char(string='Collection Phone')

    # Multi-package support
    package_line_ids = fields.One2many(
        'porter.shipment.wizard.package',
        'wizard_id',
        string='Packages'
    )

    use_multi_package = fields.Boolean(string='Multiple Packages')

    # ========== Compute Methods للمناطق ==========
    @api.depends('partner_id', 'partner_id.country_id')
    def _compute_partner_country(self):
        """حساب دولة العميل"""
        for wizard in self:
            if wizard.partner_id and wizard.partner_id.country_id:
                wizard.partner_country_id = wizard.partner_id.country_id
            else:
                wizard.partner_country_id = False

    @api.depends('use_warehouse_address', 'picking_id.picking_type_id.warehouse_id.partner_id.country_id')
    def _compute_collection_country(self):
        """حساب دولة المخزن أو الشركة"""
        for wizard in self:
            if wizard.use_warehouse_address and wizard.picking_id.picking_type_id.warehouse_id:
                warehouse_partner = wizard.picking_id.picking_type_id.warehouse_id.partner_id
                if warehouse_partner and warehouse_partner.country_id:
                    wizard.collection_country_id = warehouse_partner.country_id
                else:
                    wizard.collection_country_id = wizard.env.company.country_id
            else:
                wizard.collection_country_id = wizard.env.company.country_id

    @api.onchange('partner_country_id')
    def _onchange_partner_country(self):
        """مسح المنطقة عند تغيير الدولة"""
        if self.partner_country_id:
            # البحث عن منطقة افتراضية للدولة
            default_area = self.env['porter.area'].search([
                ('country_id', '=', self.partner_country_id.id),
                ('active', '=', True)
            ], limit=1)
            if default_area:
                self.consignee_area_id = default_area
        else:
            self.consignee_area_id = False

    @api.onchange('collection_country_id', 'use_warehouse_address')
    def _onchange_collection_country(self):
        """مسح منطقة التجميع عند تغيير الدولة"""
        if self.collection_country_id:
            # البحث عن منطقة افتراضية للدولة
            default_area = self.env['porter.area'].search([
                ('country_id', '=', self.collection_country_id.id),
                ('active', '=', True)
            ], limit=1)
            if default_area:
                self.collection_area_id = default_area
        else:
            self.collection_area_id = False

    # ========================================

    @api.depends('picking_id', 'picking_id.sale_id', 'picking_id.sale_id.currency_id')
    def _compute_cod_currency(self):
        """حساب العملة من Sale Order"""
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sale_id:
                wizard.cod_currency_id = wizard.picking_id.sale_id.currency_id
            else:
                wizard.cod_currency_id = wizard.env.company.currency_id

    @api.model
    def default_get(self, fields_list):
        """Set default values"""
        res = super().default_get(fields_list)

        if self.env.context.get('default_picking_id'):
            picking = self.env['stock.picking'].browse(self.env.context['default_picking_id'])

            # Set reference
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            res['reference2'] = f"{picking.name}_{timestamp}"

            # Set service type from carrier
            if picking.carrier_id and picking.carrier_id.delivery_type == 'porter':
                res['product_code'] = picking.carrier_id.porter_product_code

            # Set collection address from warehouse
            if picking.picking_type_id.warehouse_id:
                warehouse = picking.picking_type_id.warehouse_id
                partner = warehouse.partner_id
                if partner:
                    res['collection_name'] = warehouse.name
                    res['collection_address'] = partner._display_address()
                    res['collection_phone'] = partner.phone or partner.mobile

            # تعيين العملة من Sale Order
            if picking.sale_id and picking.sale_id.currency_id:
                res['cod_currency_id'] = picking.sale_id.currency_id.id

            # ========== تعيين المنطقة الافتراضية ==========
            if picking.partner_id and picking.partner_id.country_id:
                # البحث عن منطقة افتراضية لدولة العميل
                default_area = self.env['porter.area'].search([
                    ('country_id', '=', picking.partner_id.country_id.id),
                    ('active', '=', True)
                ], limit=1)
                if default_area:
                    res['consignee_area_id'] = default_area.id
            # ==========================================

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

    @api.onchange('use_multi_package')
    def _onchange_use_multi_package(self):
        """Create package lines when enabling multi-package"""
        if self.use_multi_package and not self.package_line_ids:
            self.package_line_ids = [(0, 0, {
                'description': 'Package 1',
                'weight': self.weight,
            })]

    @api.onchange('is_cod')
    def _onchange_is_cod(self):
        """Set COD amount from order total"""
        if self.is_cod and self.picking_id.sale_id:
            self.cod_amount = self.picking_id.sale_id.amount_total
            if self.picking_id.sale_id.currency_id:
                self.cod_currency_id = self.picking_id.sale_id.currency_id
        elif not self.is_cod:
            self.cod_amount = 0.0

    def _prepare_shipment_data(self):
        """Prepare data for Porter API"""
        self.ensure_one()

        picking = self.picking_id
        partner = self.partner_id

        # Get Porter config
        config = self.carrier_id.get_porter_config(partner)

        # ========== استخدام المناطق المختارة ==========
        # التحقق من وجود منطقة التسليم
        if not self.consignee_area_id:
            raise UserError(_('Please select a delivery area for the customer!'))

        consignee_area_id = self.consignee_area_id.encrypted_area_id

        # منطقة التجميع
        if self.auto_create_pickup and self.collection_area_id:
            collection_area_id = self.collection_area_id.encrypted_area_id
        else:
            # إذا لم يتم اختيار منطقة تجميع، استخدم نفس منطقة التسليم أو منطقة افتراضية
            collection_area_id = self._get_area_id(config.country_code)
        # ==========================================

        # Prepare shipper address
        if self.use_warehouse_address:
            warehouse = picking.picking_type_id.warehouse_id
            shipper_partner = warehouse.partner_id
            shipper_name = warehouse.name
        else:
            shipper_partner = self.env.company.partner_id
            shipper_name = self.env.company.name

        # تحضير المنتجات
        fulfillment_items = []
        missing_skus = []

        for move in picking.move_ids:
            product = move.product_id
            sku = product.default_code

            if not sku:
                missing_skus.append(product.name)
            else:
                if picking.state == 'done':
                    quantity = sum(move.move_line_ids.mapped('qty_done'))
                else:
                    quantity = move.product_uom_qty

                if quantity > 0:
                    fulfillment_items.append({
                        "Sku": sku,
                        "Quantity": int(quantity)
                    })

        if missing_skus:
            raise UserError(_(
                'المنتجات التالية ليس لها رمز SKU (Internal Reference):\n\n%s\n\n'
                'برجاء إضافة Internal Reference لهذه المنتجات أولاً.'
            ) % '\n'.join(['• ' + name for name in missing_skus]))

        if not fulfillment_items:
            raise UserError(_('لا توجد منتجات في أمر التسليم هذا!'))

        _logger.info(f"Porter Fulfillment Items: {fulfillment_items}")

        # تحضير قيمة البضائع
        goods_cost = 0
        goods_currency = self.env.company.currency_id

        if picking.sale_id:
            if picking.sale_id.currency_id != goods_currency:
                goods_cost = picking.sale_id.currency_id._convert(
                    sum(picking.sale_id.order_line.mapped('price_subtotal')),
                    goods_currency,
                    self.env.company,
                    fields.Date.today()
                )
            else:
                goods_cost = sum(picking.sale_id.order_line.mapped('price_subtotal'))

        # تحضير البيانات
        data = {
            "Reference2": self.reference2,
            "ProductCode": "DE",
            "BrandCode": None,
            "ShipmentDetail": {
                "CodAmount": float(self.cod_amount) if self.is_cod else 0,
                "CodCurrency": self.cod_currency_id.name if self.is_cod else None,
                "GoodsCost": float(goods_cost),
                "GoodsCostCurrencyCode": goods_currency.name,
                "Description1": self.description1,
                "Description2": self.description2 or "",
                "Notes1": self.notes or "",
                "Notes2": "",
                "Notes3": "",
                "Notes4": "",
                "Pieces": int(self.pieces),
                "RoundTrip": False,
                "ShipmentType": 1,
                "Weight": float(self.weight),
                "CustomFeesType": None,
                "PayType": 0,
                "IsMultiPiece": bool(self.use_multi_package),
                "ParentShipmentNo": None,
                "ConsolidationNo": None,
                "IsConsolidationClosed": None,
                "Length": None,
                "Width": None,
                "Height": None,
                "MeasurementType": None
            },
            "ShipmentShipper": {
                "AccountNo": None,
                "Reference1": picking.origin or "",
                "Address": {
                    "LocationName": shipper_name,
                    "FullAddress": self.collection_address if not self.use_warehouse_address else shipper_partner._display_address(),
                    "Phone": self.collection_phone if not self.use_warehouse_address else (
                            shipper_partner.phone or shipper_partner.mobile or "+96512345678"),
                    "CellNo": self.collection_phone if not self.use_warehouse_address else (
                            shipper_partner.mobile or shipper_partner.phone or "+96512345678"),
                    "ContactPerson": shipper_partner.name if self.use_warehouse_address else self.collection_name,
                    "LandMark": config.country_code,
                    "EncryptedAreaId": collection_area_id,  # استخدام منطقة التجميع المختارة
                    "CountryCode": None,
                    "CityName": None,
                    "AreaName": None
                }
            },
            "ShipmentConsignee": {
                "ConsigneeName": partner.name,
                "ConsigneeCompany": partner.parent_id.name if partner.parent_id else "",
                "Remarks": "",
                "NationalCivilId": partner.vat or "",
                "NationalLocationIdentification": "",
                "Email": partner.email or "",
                "Address": {
                    "LocationName": partner.name,
                    "FullAddress": partner._display_address(),
                    "Phone": partner.phone or partner.mobile or "+96512345678",
                    "CellNo": partner.mobile or partner.phone or "+96512345678",
                    "LandMark": "",
                    "EncryptedAreaId": consignee_area_id,  # استخدام منطقة التسليم المختارة
                    "CountryCode": None,
                    "CityName": None,
                    "AreaName": None
                }
            },
            "FulfilmentItems": fulfillment_items
        }

        # إضافة Collection إذا مطلوب
        if self.auto_create_pickup:
            data["Collection"] = {
                "PickupDate": self.pickup_date.strftime("%d-%b-%Y").upper(),
                "Notes": f"Pickup for {picking.name}",
                "CollectionAddress": data["ShipmentShipper"]["Address"].copy()
            }

        # إضافة Packages إذا متعدد
        if self.use_multi_package and self.package_line_ids:
            data["Packages"] = []
            for package in self.package_line_ids:
                data["Packages"].append({
                    "PackageDescription": package.description,
                    "ActualWeight": float(package.weight),
                    "Length": float(package.length or 0),
                    "Width": float(package.width or 0),
                    "Height": float(package.height or 0)
                })

        return data

    def action_create_shipment(self):
        """Create shipment via Porter API"""
        self.ensure_one()

        # Validate
        if self.weight <= 0:
            raise ValidationError(_('Weight must be greater than 0!'))

        if self.is_cod and self.cod_amount <= 0:
            raise ValidationError(_('COD amount must be greater than 0!'))

        # ========== التحقق من المنطقة ==========
        if not self.consignee_area_id:
            raise ValidationError(_('Please select a delivery area!'))
        # =====================================

        # Get config based on delivery address country
        partner = self.picking_id.partner_id
        try:
            config = self.carrier_id.get_porter_config(partner)
        except UserError as e:
            raise UserError(_(
                'Configuration Error:\n%(error)s\n\n'
                'Customer: %(customer)s\n'
                'Country: %(country)s',
                error=str(e),
                customer=partner.name,
                country=partner.country_id.name if partner.country_id else 'Not Set'
            ))

        if not config:
            raise UserError(_(
                'No Porter configuration found for country: %(country)s',
                country=partner.country_id.name if partner.country_id else 'Unknown'
            ))

        # Log which config is being used
        if config.debug_mode:
            _logger.info(f"Using Porter config: {config.display_name} for country: {config.country_id.name}")

        # Prepare data
        shipment_data = self._prepare_shipment_data()

        try:
            # Call API
            response = config._make_api_request(
                'Save',
                method='POST',
                data=shipment_data
            )

            # Log full response for debugging
            if config.debug_mode:
                _logger.info(f"Porter Save Response: {json.dumps(response, indent=2)}")

            # Extract AWB number
            awb_number = None
            pickup_no = None

            if isinstance(response, dict):
                awb_number = response.get('awbNo') or response.get('AWBNo') or response.get('awbNumber')
                pickup_no = response.get('pickupNo') or response.get('PickupNo')

                if not awb_number and response.get('data'):
                    if isinstance(response['data'], dict):
                        awb_number = response['data'].get('awbNo') or response['data'].get('AWBNo')
                    elif isinstance(response['data'], list) and response['data']:
                        awb_number = response['data'][0]

            if not awb_number:
                error_msg = _(
                    'No AWB number received from Porter!\n'
                    'Full Response:\n%(response)s',
                    response=json.dumps(response, indent=2) if isinstance(response, dict) else str(response)
                )

                if config.debug_mode:
                    raise UserError(error_msg)
                else:
                    raise UserError(_('No AWB number received from Porter! Enable debug mode to see full response.'))

            # Create shipment record with area information
            shipment_vals = {
                'name': awb_number,
                'reference2': self.reference2,
                'picking_id': self.picking_id.id,
                'product_code': self.product_code,
                'pieces': self.pieces,
                'weight': self.weight,
                'cod_amount': self.cod_amount if self.is_cod else 0,
                'cod_currency': self.cod_currency_id.id if self.is_cod else False,
                'pickup_date': self.pickup_date,
                'pickup_number': pickup_no,
                'state': 'confirmed',
                'company_id': self.picking_id.company_id.id,
                # ========== إضافة معلومات المنطقة ==========
                'consignee_area_id': self.consignee_area_id.id,
                'collection_area_id': self.collection_area_id.id if self.collection_area_id else False,
                # ==========================================
            }

            porter_shipment = self.env['porter.shipment'].create(shipment_vals)

            # Link to picking
            self.picking_id.porter_shipment_id = porter_shipment

            # Add detailed note to picking
            note_body = _(
                '<b>Porter Express shipment created successfully!</b><br/>'
                '<b>Configuration:</b> %(config)s<br/>'
                '<b>Country:</b> %(country)s<br/>'
                '<b>Delivery Area:</b> %(area)s<br/>'
                '<b>AWB:</b> %(awb)s<br/>',
                config=config.display_name,
                country=config.country_id.name,
                area=self.consignee_area_id.name,
                awb=awb_number
            )

            if pickup_no:
                note_body += _('<b>Pickup Number:</b> %(pickup)s<br/>', pickup=pickup_no)

            note_body += _(
                '<b>Reference:</b> %(ref)s<br/>'
                '<b>Service:</b> %(service)s<br/>'
                '<b>Weight:</b> %(weight).2f kg',
                ref=self.reference2,
                service=dict(self._fields['product_code'].selection).get(self.product_code),
                weight=self.weight
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

            # Try to get label immediately
            try:
                self.picking_id._get_porter_label()
            except Exception as e:
                _logger.warning(f"Failed to get label immediately: {str(e)}")

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _(
                        'Porter shipment created successfully!\n'
                        'AWB: %(awb)s\n'
                        'Country: %(country)s\n'
                        'Area: %(area)s',
                        awb=awb_number,
                        country=config.country_id.name,
                        area=self.consignee_area_id.name
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
            _logger.error(f"Porter shipment creation failed: {str(e)}")
            _logger.error(f"Traceback: {traceback.format_exc()}")

            error_msg = str(e)

            if 'SKU' in error_msg or 'sku' in error_msg or 'Sku' in error_msg:
                raise UserError(_(
                    'خطأ في رمز المنتج (SKU)!\n\n'
                    'تأكد من أن Internal Reference للمنتجات يطابق الأكواد المسجلة في Porter.\n\n'
                    'المنتجات في هذه الشحنة:\n%(products)s\n\n'
                    'تفاصيل الخطأ:\n%(error)s',
                    products='\n'.join([
                        f'• {move.product_id.name}: SKU = {move.product_id.default_code or "غير محدد"}'
                        for move in self.picking_id.move_ids
                    ]),
                    error=error_msg
                ))

            raise UserError(_(
                'Failed to create shipment:\n%(error)s\n\n'
                'Configuration: %(config)s\n'
                'Country: %(country)s',
                error=str(e),
                config=config.display_name if config else 'N/A',
                country=config.country_id.name if config and config.country_id else 'N/A'
            ))

    def _generate_unique_reference(self):
        """Generate unique reference with timestamp"""
        base_ref = self.picking_id.name
        timestamp = datetime.now().strftime('%H%M%S')
        return f"{base_ref}_{timestamp}"

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        """Update reference when picking changes"""
        if self.picking_id:
            self.reference2 = self._generate_unique_reference()

    def _get_area_id(self, country_code, city=None):
        """Get area ID for the country"""
        area = self.env['porter.area'].search([
            ('country_id.code', '=', country_code),
            ('active', '=', True)
        ], limit=1)

        if area:
            return area.encrypted_area_id
        else:
            raise UserError(_(
                'No Porter areas configured for country: %s\n'
                'Please add areas in Porter Express > Areas',
                country_code
            ))


class PorterShipmentWizardPackage(models.TransientModel):
    _name = 'porter.shipment.wizard.package'
    _description = 'Porter Shipment Package Line'

    wizard_id = fields.Many2one('porter.shipment.wizard', required=True, ondelete='cascade')

    description = fields.Char(string='Description', required=True)
    weight = fields.Float(string='Weight (KG)', required=True, default=1.0)
    length = fields.Float(string='Length (cm)')
    width = fields.Float(string='Width (cm)')
    height = fields.Float(string='Height (cm)')
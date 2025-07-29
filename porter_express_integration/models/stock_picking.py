# -*- coding: utf-8 -*-
import json
import base64
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    porter_shipment_id = fields.Many2one(
        'porter.shipment',
        string='Porter Shipment',
        readonly=True,
        copy=False
    )

    porter_awb = fields.Char(
        string='Porter AWB',
        related='porter_shipment_id.name',
        store=True
    )

    porter_tracking_url = fields.Char(
        string='Porter Tracking URL',
        related='porter_shipment_id.tracking_url'
    )

    porter_label_pdf = fields.Binary(
        string='Porter Label',
        related='porter_shipment_id.label_pdf'
    )

    # إضافة الحقل الناقص
    porter_label_filename = fields.Char(
        string='Porter Label Filename',
        related='porter_shipment_id.label_filename'
    )

    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier',
        compute='_compute_carrier_id',
        store=True
    )

    is_porter_carrier = fields.Boolean(
        compute='_compute_is_porter_carrier',
        store=True
    )

    @api.depends('sale_id.carrier_id')
    def _compute_carrier_id(self):
        """Get carrier from sale order"""
        for picking in self:
            if picking.sale_id and picking.sale_id.carrier_id:
                picking.carrier_id = picking.sale_id.carrier_id
            else:
                picking.carrier_id = False

    @api.depends('carrier_id', 'carrier_id.delivery_type')
    def _compute_is_porter_carrier(self):
        for picking in self:
            picking.is_porter_carrier = picking.carrier_id and picking.carrier_id.delivery_type == 'porter'

    def action_create_porter_shipment(self):
        """Open wizard to create Porter shipment"""
        self.ensure_one()

        if not self.carrier_id or self.carrier_id.delivery_type != 'porter':
            raise UserError(_('Please select Porter Express as delivery method in the related sale order.'))

        if self.porter_shipment_id:
            raise UserError(_('Porter shipment already created for this delivery.'))

        missing_sku_products = []
        for move in self.move_ids:
            if not move.product_id.default_code:
                missing_sku_products.append(move.product_id.name)

        if missing_sku_products:
            raise UserError(_(
                'لا يمكن إنشاء شحنة Porter!\n\n'
                'المنتجات التالية تحتاج Internal Reference:\n%s\n\n'
                'اذهب إلى بيانات المنتج وأضف Internal Reference أولاً.'
            ) % '\n'.join(['• ' + name for name in missing_sku_products]))

        # فتح Wizard
        return {
            'name': _('Create Porter Shipment'),
            'type': 'ir.actions.act_window',
            'res_model': 'porter.shipment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_carrier_id': self.carrier_id.id,
            }
        }

    def action_print_porter_label(self):
        """Print Porter shipping label"""
        self.ensure_one()

        if not self.porter_shipment_id:
            raise UserError(_('No Porter shipment found.'))

        if not self.porter_label_pdf:
            # جلب الـ Label من API
            self._get_porter_label()

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.porter_shipment_id._name}/{self.porter_shipment_id.id}/label_pdf/Porter_Label_{self.porter_awb}.pdf?download=true',
            'target': 'self',
        }

    def action_track_porter_shipment(self):
        """Track Porter shipment"""
        self.ensure_one()

        if not self.porter_tracking_url:
            raise UserError(_('No tracking URL available.'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.porter_tracking_url,
            'target': '_blank',
        }

    def action_cancel_porter_shipment(self):
        """Cancel Porter shipment"""
        self.ensure_one()

        if not self.porter_shipment_id:
            raise UserError(_('No Porter shipment to cancel.'))

        if self.porter_shipment_id.state not in ['draft', 'confirmed']:
            raise UserError(_('Cannot cancel shipment in current state.'))

        # استدعاء API للإلغاء
        config = self.carrier_id.porter_config_id

        try:
            response_data = config._make_api_request(
                'CancelShipment',
                method='POST',
                data={'awbno': self.porter_awb}
            )

            # تحديث الحالة
            self.porter_shipment_id.state = 'cancelled'

            # إضافة ملاحظة في chatter
            self.message_post(
                body=_('Porter shipment cancelled. AWB: %s') % self.porter_awb,
                subject=_('Shipment Cancelled')
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Porter shipment cancelled successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_('Failed to cancel shipment: %s') % str(e))

    def _get_porter_label(self):
        """Get label from Porter API"""
        self.ensure_one()

        if not self.porter_shipment_id or not self.carrier_id:
            return

        config = self.carrier_id.porter_config_id

        try:
            response_data = config._make_api_request(
                'GetLabelPDF',
                method='POST',
                data={
                    'awbno': self.porter_awb,
                    'ref2': self.porter_shipment_id.reference2
                }
            )

            if response_data.get('label'):
                # حفظ PDF
                pdf_content = base64.b64decode(response_data['label'])
                self.porter_shipment_id.write({
                    'label_pdf': base64.b64encode(pdf_content),
                    'label_filename': f'Porter_Label_{self.porter_awb}.pdf'
                })

        except Exception as e:
            raise UserError(_('Failed to get label: %s') % str(e))

    @api.model
    def _cron_update_porter_tracking(self):
        """Cron job to update Porter tracking status"""
        pickings = self.search([
            ('porter_shipment_id', '!=', False),
            ('porter_shipment_id.state', 'not in', ['delivered', 'cancelled']),
            ('state', '=', 'done')
        ])

        for picking in pickings:
            picking._update_porter_tracking()

    def _update_porter_tracking(self):
        """Update tracking information from Porter API"""
        self.ensure_one()

        if not self.porter_shipment_id or not self.carrier_id:
            return

        config = self.carrier_id.porter_config_id

        try:
            response_data = config._make_api_request(
                'GetTrackingDetails',
                params={'awbno': self.porter_awb}
            )

            # تحديث حالة الشحنة حسب الرد
            # هذا مثال - قد تحتاج لتعديله حسب هيكل الرد الفعلي
            if response_data.get('status'):
                status_mapping = {
                    'DELIVERED': 'delivered',
                    'IN_TRANSIT': 'in_transit',
                    'CONFIRMED': 'confirmed',
                    'CANCELLED': 'cancelled',
                }

                new_state = status_mapping.get(
                    response_data['status'].upper(),
                    self.porter_shipment_id.state
                )

                if new_state != self.porter_shipment_id.state:
                    self.porter_shipment_id.state = new_state

                    # إضافة ملاحظة
                    self.message_post(
                        body=_('Porter shipment status updated to: %s') % new_state,
                        subject=_('Tracking Update')
                    )

                # تحديث تاريخ التسليم
                if new_state == 'delivered' and response_data.get('delivery_date'):
                    self.porter_shipment_id.delivery_date = response_data['delivery_date']

        except Exception as e:
            # Log error but don't raise - this is a background job
            self.message_post(
                body=_('Failed to update tracking: %s') % str(e),
                subject=_('Tracking Error')
            )
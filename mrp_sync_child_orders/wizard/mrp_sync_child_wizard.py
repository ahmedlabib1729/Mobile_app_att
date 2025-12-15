# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MrpSyncChildWizard(models.TransientModel):
    _name = 'mrp.sync.child.wizard'
    _description = 'Sync Child Manufacturing Orders Wizard'

    parent_mo_id = fields.Many2one(
        'mrp.production',
        string='Parent Manufacturing Order',
        required=True,
        readonly=True
    )

    original_qty = fields.Float(
        string='Original Quantity',
        readonly=True
    )

    qty_producing = fields.Float(
        string='Quantity Producing',
        required=True
    )

    sync_close = fields.Boolean(
        string='Close Child MOs with same quantity',
        default=True
    )

    sync_backorder = fields.Boolean(
        string='Create Backorder for remaining quantity',
        default=True
    )

    child_mo_line_ids = fields.One2many(
        'mrp.sync.child.wizard.line',
        'wizard_id',
        string='Child Manufacturing Orders',
    )

    def action_confirm(self):
        """Close parent and child MOs"""
        self.ensure_one()

        _logger.info("=" * 50)
        _logger.info("SYNC: Parent MO %s, qty: %s", self.parent_mo_id.name, self.qty_producing)

        # أولاً: قفل الأوامر الفرعية
        if self.sync_close:
            for line in self.child_mo_line_ids.filtered('selected'):
                child_mo = line.child_mo_id

                if child_mo.state in ['done', 'cancel']:
                    continue

                _logger.info("Closing child MO: %s with qty: %s", child_mo.name, line.new_qty)
                self._force_close_mo(child_mo, line.new_qty)

        # ثانياً: قفل الأمر الرئيسي
        _logger.info("Closing parent MO: %s", self.parent_mo_id.name)
        return self._close_parent_mo()

    def _force_close_mo(self, mo, qty):
        """Force close a manufacturing order with specific quantity using proper Odoo methods"""
        _logger.info("=" * 30)
        _logger.info("Closing MO %s with qty %s (original: %s)", mo.name, qty, mo.product_qty)
        _logger.info("MO state before: %s", mo.state)

        create_backorder = self.sync_backorder and qty < mo.product_qty
        _logger.info("Create backorder: %s", create_backorder)

        try:
            # 1. تعيين الكمية المنتجة
            mo.qty_producing = qty

            # 2. تعيين الكميات في الـ finished moves
            for move in mo.move_finished_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
                move.quantity = qty

            # 3. تعيين الكميات في الـ raw moves (بناءً على النسبة)
            if mo.product_qty:
                ratio = qty / mo.product_qty
                for move in mo.move_raw_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
                    move.quantity = move.product_uom_qty * ratio

            # 4. لو الـ MO في حالة confirmed، نعمل assign للمكونات
            if mo.state == 'confirmed':
                mo.action_assign()

            # 5. نستخدم button_mark_done - الطريقة الرسمية
            action = mo.with_context(skip_sync_wizard=True).button_mark_done()
            _logger.info("button_mark_done returned: %s", type(action).__name__)

            # 6. التعامل مع الـ Wizards - Loop حتى الـ MO يبقى Done
            max_iterations = 5  # حماية من infinite loop
            iteration = 0

            while isinstance(action, dict) and iteration < max_iterations:
                iteration += 1
                res_model = action.get('res_model')
                _logger.info("Iteration %s - Wizard: %s", iteration, res_model)

                # Consumption Warning Wizard - بيحذر إن الاستهلاك مختلف
                if res_model == 'mrp.consumption.warning':
                    _logger.info("Processing consumption warning wizard")

                    # نجيب الـ context من الـ action
                    ctx = action.get('context', {})

                    wiz = self.env['mrp.consumption.warning'].with_context(**ctx).create({
                        'mrp_production_ids': [(6, 0, [mo.id])]
                    })

                    # action_confirm بتكمل بالاستهلاك الحالي
                    action = wiz.action_confirm()
                    _logger.info("After consumption warning, state: %s", mo.state)

                    # لو مفيش action جديد، نستدعي button_mark_done تاني
                    if mo.state != 'done' and not isinstance(action, dict):
                        _logger.info("Calling button_mark_done after consumption warning...")
                        action = mo.with_context(skip_sync_wizard=True).button_mark_done()

                    continue

                # Immediate Production Wizard - بيسأل عن المكونات
                elif res_model == 'mrp.immediate.production':
                    _logger.info("Processing immediate production wizard")

                    # نجيب الـ context من الـ action
                    ctx = action.get('context', {})
                    ctx['active_id'] = mo.id
                    ctx['active_ids'] = [mo.id]

                    wiz = self.env['mrp.immediate.production'].with_context(**ctx).create({})

                    # process بتستهلك المكونات
                    action = wiz.process()
                    _logger.info("After immediate wizard, state: %s", mo.state)

                    # لو لسه مش done، نستدعي button_mark_done تاني
                    if mo.state != 'done' and not isinstance(action, dict):
                        _logger.info("Calling button_mark_done again...")
                        action = mo.with_context(skip_sync_wizard=True).button_mark_done()

                    continue

                # Backorder Wizard - بيسأل عن الكمية المتبقية
                elif res_model == 'mrp.production.backorder':
                    _logger.info("Processing backorder wizard")

                    # نجيب الـ context من الـ action
                    ctx = action.get('context', {})

                    # نضيف الـ MO للـ context
                    ctx['button_mark_done_production_ids'] = [mo.id]

                    backorder_wiz = self.env['mrp.production.backorder'].with_context(**ctx).create({
                        'mrp_production_ids': [(6, 0, [mo.id])]
                    })

                    if create_backorder:
                        _logger.info("Creating backorder via wizard")
                        action = backorder_wiz.action_backorder()
                    else:
                        _logger.info("Closing without backorder via wizard")
                        action = backorder_wiz.action_close_mo()

                    continue

                else:
                    # wizard تاني مش معروف
                    _logger.warning("Unknown wizard: %s", res_model)
                    break

            _logger.info("MO %s FINAL state: %s", mo.name, mo.state)

            # 7. التحقق من نجاح العملية
            if mo.state == 'done':
                _logger.info("SUCCESS: MO %s closed properly with stock moves", mo.name)
            else:
                _logger.warning("MO %s state is %s, not done!", mo.name, mo.state)

        except Exception as e:
            _logger.error("Error closing MO %s: %s", mo.name, str(e))
            import traceback
            _logger.error(traceback.format_exc())

        _logger.info("=" * 30)

    def _force_done_state(self, mo, qty, create_backorder=True):
        """Fallback method - should not be used normally"""
        _logger.warning("Using fallback _force_done_state for MO %s - this may cause stock issues!", mo.name)
        # نستدعي الطريقة الصحيحة
        self._force_close_mo(mo, qty)

    def _close_parent_mo(self):
        """Close the parent manufacturing order"""
        parent_mo = self.parent_mo_id
        parent_mo.qty_producing = self.qty_producing
        return parent_mo.with_context(skip_sync_wizard=True).button_mark_done()

    def action_skip(self):
        """Skip syncing and just close parent MO"""
        return self._close_parent_mo()

    def action_cancel(self):
        """Cancel and return to MO"""
        return {'type': 'ir.actions.act_window_close'}


class MrpSyncChildWizardLine(models.TransientModel):
    _name = 'mrp.sync.child.wizard.line'
    _description = 'Sync Child Manufacturing Orders Wizard Line'

    wizard_id = fields.Many2one(
        'mrp.sync.child.wizard',
        required=True,
        ondelete='cascade'
    )

    selected = fields.Boolean(
        string='Sync',
        default=True
    )

    child_mo_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        required=True,
        readonly=True
    )

    child_mo_name = fields.Char(
        related='child_mo_id.name',
        string='Reference'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True
    )

    original_qty = fields.Float(
        string='Original Qty',
        readonly=True
    )

    new_qty = fields.Float(
        string='New Qty'
    )

    state = fields.Selection(
        related='child_mo_id.state',
        string='Status'
    )


class MrpSyncCancelWizard(models.TransientModel):
    _name = 'mrp.sync.cancel.wizard'
    _description = 'Cancel Child Manufacturing Orders Wizard'

    parent_mo_ids = fields.Many2many(
        'mrp.production',
        'mrp_sync_cancel_parent_rel',
        'wizard_id',
        'mo_id',
        string='Parent Manufacturing Orders'
    )

    child_mo_ids = fields.Many2many(
        'mrp.production',
        'mrp_sync_cancel_child_rel',
        'wizard_id',
        'mo_id',
        string='Child Manufacturing Orders',
        readonly=True
    )

    cancel_children = fields.Boolean(
        string='Cancel Child MOs',
        default=True
    )

    def action_confirm(self):
        """Cancel parent and optionally children"""
        if self.cancel_children and self.child_mo_ids:
            self.child_mo_ids.with_context(skip_sync_wizard=True).action_cancel()
        return self.parent_mo_ids.with_context(skip_sync_wizard=True).action_cancel()

    def action_skip(self):
        """Cancel only parent MOs"""
        return self.parent_mo_ids.with_context(skip_sync_wizard=True).action_cancel()
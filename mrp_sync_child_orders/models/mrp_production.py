# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # =========================================================================
    # FIELDS
    # =========================================================================

    # الـ Root MO - أصل كل الأوامر المرتبطة
    root_production_id = fields.Many2one(
        'mrp.production',
        string='Root Manufacturing Order',
        help='The original/root manufacturing order that started this production chain',
        index=True,
        copy=True,  # مهم - عشان الـ backorder يورث الـ root
    )

    child_mo_ids = fields.One2many(
        'mrp.production',
        'parent_mo_id',
        string='Child Manufacturing Orders',
        help='Manufacturing orders created for components of this order'
    )

    parent_mo_id = fields.Many2one(
        'mrp.production',
        string='Parent Manufacturing Order',
        compute='_compute_parent_mo_id',
        store=True,
        help='The parent manufacturing order that triggered this order'
    )

    child_mo_count = fields.Integer(
        string='Child MO Count',
        compute='_compute_child_mo_count'
    )

    has_child_mos = fields.Boolean(
        string='Has Child MOs',
        compute='_compute_child_mo_count'
    )

    is_child_mo = fields.Boolean(
        string='Is Child MO',
        compute='_compute_is_child_mo',
        store=True
    )

    # =========================================================================
    # COMPUTE METHODS
    # =========================================================================

    @api.depends('origin')
    def _compute_parent_mo_id(self):
        """Find the parent MO based on origin field"""
        for production in self:
            parent_mo = False
            if production.origin:
                # البحث عن أمر التصنيع الرئيسي من خلال الـ origin
                parent_mo = self.env['mrp.production'].search([
                    ('name', '=', production.origin),
                    ('id', '!=', production.id)
                ], limit=1)

                # لو مفيش، نبحث من خلال الـ procurement_group_id
                if not parent_mo and production.procurement_group_id:
                    parent_mo = self.env['mrp.production'].search([
                        ('procurement_group_id', '=', production.procurement_group_id.id),
                        ('id', '!=', production.id),
                        ('product_id.bom_ids.bom_line_ids.product_id', '=', production.product_id.id)
                    ], limit=1)

            production.parent_mo_id = parent_mo.id if parent_mo else False

    @api.depends('origin', 'procurement_group_id')
    def _compute_is_child_mo(self):
        """Check if this MO is a child of another MO"""
        for production in self:
            is_child = False
            if production.origin:
                # التحقق من وجود أمر تصنيع بهذا الاسم
                parent_exists = self.env['mrp.production'].search_count([
                    ('name', '=', production.origin)
                ])
                is_child = parent_exists > 0
            production.is_child_mo = is_child

    def _compute_child_mo_count(self):
        """Compute count of child manufacturing orders"""
        for production in self:
            child_mos = production._get_child_mos()
            production.child_mo_count = len(child_mos)
            production.has_child_mos = len(child_mos) > 0

    # =========================================================================
    # MODEL METHODS
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set root_production_id"""
        records = super().create(vals_list)

        for record in records:
            if not record.root_production_id:
                # لو ده MO جديد من Sales Order أو Manual
                # نشوف لو فيه Parent MO
                if record.origin:
                    parent_mo = self.env['mrp.production'].search([
                        ('name', '=', record.origin)
                    ], limit=1)

                    if parent_mo:
                        # لو الـ Parent عنده root، نستخدمه
                        # لو لأ، الـ Parent هو الـ root
                        root = parent_mo.root_production_id or parent_mo
                        record.root_production_id = root.id
                    else:
                        # مفيش parent MO، يبقى ده الـ root
                        record.root_production_id = record.id
                else:
                    # مفيش origin، يبقى ده الـ root
                    record.root_production_id = record.id

        return records

    def copy(self, default=None):
        """Override copy to ensure root_production_id is inherited for backorders"""
        default = default or {}

        # لو مفيش root_production_id في الـ default، نورثه من الـ original
        if 'root_production_id' not in default:
            # نستخدم الـ root بتاع الـ original، أو الـ original نفسه لو مفيش
            default['root_production_id'] = self.root_production_id.id or self.id

        return super().copy(default)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_child_mos(self):
        """Get all child manufacturing orders for this MO including backorders"""
        self.ensure_one()

        child_mos = self.env['mrp.production']

        # الطريقة 1: البحث من خلال root_production_id
        if self.root_production_id:
            # كل الـ MOs اللي ليها نفس الـ root
            same_family = self.env['mrp.production'].search([
                ('root_production_id', '=', self.root_production_id.id),
                ('id', '!=', self.id),
                ('state', 'not in', ['done', 'cancel'])
            ])

            # نستبعد الـ Parent MO لو موجود
            for mo in same_family:
                # نتأكد إن ده مش parent لينا
                if mo.name != self.origin:
                    child_mos |= mo

        # الطريقة 2: البحث من خلال origin (للـ MOs القديمة)
        child_mos |= self.env['mrp.production'].search([
            ('origin', '=', self.name),
            ('id', '!=', self.id),
            ('state', 'not in', ['done', 'cancel'])
        ])

        # الطريقة 3: البحث من خلال procurement_group_id
        if self.procurement_group_id:
            same_group = self.env['mrp.production'].search([
                ('procurement_group_id', '=', self.procurement_group_id.id),
                ('id', '!=', self.id),
                ('state', 'not in', ['done', 'cancel']),
                ('id', 'not in', child_mos.ids)
            ])

            for mo in same_group:
                if mo.name != self.origin:
                    child_mos |= mo

        # الطريقة 4: البحث عن الـ backorders بتاعت الـ children
        # لو أنا backorder (اسمي فيه -)، أدور على backorders تانية
        if '-' in self.name:
            base_name = self.name.rsplit('-', 1)[0]  # MO/00038-001 -> MO/00038

            # أجيب الـ original MO
            original_mo = self.env['mrp.production'].search([
                ('name', '=', base_name)
            ], limit=1)

            if original_mo:
                # أجيب الـ children بتوع الـ original
                original_children = original_mo._get_original_children()

                for child in original_children:
                    # أدور على الـ backorders بتاعت كل child
                    child_backorders = self.env['mrp.production'].search([
                        ('name', 'like', child.name + '-'),
                        ('state', 'not in', ['done', 'cancel']),
                        ('id', 'not in', child_mos.ids)
                    ])
                    child_mos |= child_backorders

        return child_mos

    def _get_original_children(self):
        """Get the original child MOs (not backorders)"""
        self.ensure_one()
        return self.env['mrp.production'].search([
            ('origin', '=', self.name),
            ('name', 'not like', '%-'),  # استبعاد الـ backorders
        ])

    def _get_all_related_mos(self):
        """Get all related MOs (children and their children recursively)"""
        self.ensure_one()
        all_mos = self.env['mrp.production']

        def get_children_recursive(mo):
            children = mo._get_child_mos()
            for child in children:
                all_mos |= child
                get_children_recursive(child)

        get_children_recursive(self)
        return all_mos

    # =========================================================================
    # OVERRIDE METHODS
    # =========================================================================

    def button_mark_done(self):
        """Override to show sync wizard when closing parent MO with children"""
        # لو الـ recordset فاضي أو فيه أكتر من record، نكمل عادي
        if len(self) != 1:
            return super().button_mark_done()

        # التحقق من السياق - لو جاي من الـ wizard نتخطى
        if self.env.context.get('skip_sync_wizard'):
            return super().button_mark_done()

        # البحث عن الأوامر الفرعية
        child_mos = self._get_child_mos()

        # لو فيه أوامر فرعية وفيه فرق في الكمية
        if child_mos:
            # حساب الكمية المنتجة
            qty_producing = self.qty_producing or self.product_qty

            # التحقق من وجود فرق يستدعي إظهار الـ Wizard
            show_wizard = False
            for child_mo in child_mos:
                if child_mo.product_qty != qty_producing or child_mo.state not in ['done', 'cancel']:
                    show_wizard = True
                    break

            if show_wizard:
                # إنشاء الـ Wizard مع الـ Lines مباشرة
                wizard_lines = []
                for child_mo in child_mos:
                    if child_mo.id and child_mo.product_id:
                        wizard_lines.append((0, 0, {
                            'child_mo_id': child_mo.id,
                            'product_id': child_mo.product_id.id,
                            'original_qty': child_mo.product_qty,
                            'new_qty': qty_producing,
                            'selected': True,
                        }))

                if not wizard_lines:
                    # لو مفيش lines صالحة، نكمل عادي
                    return super().button_mark_done()

                wizard = self.env['mrp.sync.child.wizard'].create({
                    'parent_mo_id': self.id,
                    'qty_producing': qty_producing,
                    'original_qty': self.product_qty,
                    'child_mo_line_ids': wizard_lines,
                })

                # فتح الـ Wizard
                return {
                    'name': _('Sync Child Manufacturing Orders'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.sync.child.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new',
                }

        # لو مفيش أوامر فرعية، نكمل عادي
        return super().button_mark_done()

    def action_cancel(self):
        """Override to ask about cancelling child MOs"""
        # التحقق من السياق - لو جاي من الـ wizard نتخطى
        if self.env.context.get('skip_sync_wizard'):
            return super().action_cancel()

        # البحث عن الأوامر الفرعية
        child_mos = self.env['mrp.production']
        for production in self:
            child_mos |= production._get_child_mos()

        if child_mos:
            # إنشاء الـ Wizard مباشرة
            wizard = self.env['mrp.sync.cancel.wizard'].create({
                'parent_mo_ids': [(6, 0, self.ids)],
                'child_mo_ids': [(6, 0, child_mos.ids)],
            })

            return {
                'name': _('Cancel Child Manufacturing Orders?'),
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.sync.cancel.wizard',
                'view_mode': 'form',
                'res_id': wizard.id,
                'target': 'new',
            }

        return super().action_cancel()

    # =========================================================================
    # ACTION METHODS
    # =========================================================================

    def action_view_child_mos(self):
        """Action to view child manufacturing orders"""
        self.ensure_one()
        child_mos = self._get_child_mos()

        action = {
            'name': _('Child Manufacturing Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('id', 'in', child_mos.ids)],
            'context': {'default_origin': self.name}
        }

        if len(child_mos) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = child_mos.id

        return action

    def action_view_parent_mo(self):
        """Action to view parent manufacturing order"""
        self.ensure_one()
        if self.parent_mo_id:
            return {
                'name': _('Parent Manufacturing Order'),
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'view_mode': 'form',
                'res_id': self.parent_mo_id.id,
            }
        return False
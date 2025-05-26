# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ClubParent(models.Model):
    _name = 'club.parent'
    _description = 'ولي الأمر'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='اسم ولي الأمر', required=True, tracking=True)

    address = fields.Text(string='العنوان', tracking=True)

    mobile = fields.Char(string='رقم الموبايل', required=True, tracking=True)

    email = fields.Char(string='البريد الإلكتروني', tracking=True)

    player_ids = fields.One2many(
        'club.player',
        'parent_id',
        string='الأبناء'
    )

    children_count = fields.Integer(
        string='عدد الأبناء',
        compute='_compute_children_count',
        store=True
    )

    total_children_fees = fields.Monetary(
        string='إجمالي رسوم الأبناء',
        compute='_compute_total_children_fees',
        store=True,
        currency_field='currency_id',
        help='إجمالي رسوم الاشتراك لجميع الأبناء'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='العملة',
        related='company_id.currency_id',
        readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
    )

    active = fields.Boolean(string='نشط', default=True)

    @api.depends('player_ids')
    def _compute_children_count(self):
        for record in self:
            record.children_count = len(record.player_ids)

    @api.depends('player_ids.total_fees')
    def _compute_total_children_fees(self):
        for record in self:
            record.total_children_fees = sum(child.total_fees for child in record.player_ids)

    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'الأبناء',
            'view_mode': 'list,form',
            'res_model': 'club.player',
            'domain': [('parent_id', '=', self.id)],
            'context': {'default_parent_id': self.id}
        }
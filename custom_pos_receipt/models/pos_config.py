# -*- coding: utf-8 -*-
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    receipt_footer_text = fields.Text(
        string='Receipt Footer',
        translate=True,
        default='Thank you for your visit! | شكراً لزيارتكم',
        help='Custom text to display at the bottom of receipts'
    )
    
    show_receipt_line_numbers = fields.Boolean(
        string='Show Line Numbers',
        default=True,
        help='Display line numbers on receipt items'
    )
    
    show_receipt_barcode = fields.Boolean(
        string='Show Receipt Barcode',
        default=True,
        help='Display barcode on receipt'
    )

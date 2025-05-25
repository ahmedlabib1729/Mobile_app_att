from odoo import fields, models, api


class Picking(models.Model):
    _inherit = 'stock.picking'
    # project_id = fields.Many2one("project.project", string="Project")

    def button_validate(self):
        res = super(Picking, self).button_validate()
        moves = self.env['account.move'].sudo().search([('move_type', '=', 'entry'), ('state', '=', 'posted')])[0]
        for rec in self.move_ids_without_package:
            for move in moves.line_ids:
                if move.debit > 0 and move.account_id.account_type == 'expense_direct_cost':
                    move.analytic_distribution = rec.analytic_distribution
                    print('moveeeeeeee ===> ', move.name)

        return res

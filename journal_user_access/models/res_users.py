from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_journal_ids = fields.Many2many(
        'account.journal',
        'journal_users_rel',
        'user_id',
        'journal_id',
        string='Allowed Journals',
        compute='_compute_allowed_journals'
    )

    journal_count = fields.Integer(
        string='Journal Count',
        compute='_compute_allowed_journals'
    )
    @api.depends('groups_id')
    def _compute_allowed_journals(self):
        for user in self:
            if user.has_group('account.group_account_manager'):
                journals = self.env['account.journal'].search([])
            else:
                journals = self.env['account.journal'].search([
                    '|',
                    ('restrict_access', '=', False),
                    ('allowed_user_ids', 'in', user.id)
                ])
            user.allowed_journal_ids = journals
            user.journal_count = len(journals)
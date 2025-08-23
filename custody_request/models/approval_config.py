from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustodyApprovalConfig(models.Model):
    _name = 'custody.approval.config'
    _description = 'Custody Approval Configuration'
    _order = 'company_id, sequence'

    name = fields.Char(
        string='Stage Name',
        required=True,
        help='Name of the approval stage'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        required=True,
        help='Order of approval stages'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True,
        help='Department responsible for this approval stage'
    )

    user_ids = fields.Many2many(
        'res.users',
        'custody_approval_config_users_rel',
        'config_id',
        'user_id',
        string='Approvers',
        required=True,
        help='Users who can approve at this stage'
    )

    @api.constrains('sequence', 'company_id', 'department_id')
    def _check_unique_sequence(self):
        for record in self:
            domain = [
                ('company_id', '=', record.company_id.id),
                ('department_id', '=', record.department_id.id),
                ('sequence', '=', record.sequence),
                ('id', '!=', record.id)
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    f'Sequence {record.sequence} already exists for {record.department_id.name}! Each approval stage must have a unique sequence number.')

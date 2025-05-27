from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class MaintenanceDeposit(models.Model):
    _inherit = 'ownership.contract'
    _description = 'maintenance deposit'

    total_maintenance = fields.Float('Total Maintenance')
    m_adv_pay = fields.Integer(string='Adv. Payment %', help="Advance payment percent ex. 5")
    m_month_count = fields.Integer(string='Inst. Plan Duration months')
    m_inst_count = fields.Integer(string='Installments count', )
    m_account_income_id = fields.Many2one('account.account', 'Income Account', )
    m_analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', )
    m_cheque = fields.Char(string='1st Cheque #')
    m_cheque_bank_id = fields.Many2one('res.bank', string='Cheques Bank')
    m_cheque_account_id = fields.Many2one('account.account', string='Cheques Account')
    m_journal_id = fields.Many2one('account.journal', string='Cheque Journal')
    maintenance_deposit_ids = fields.One2many(comodel_name='loan.line.rs.own', inverse_name='contract_id')
    m_is_create = fields.Boolean(' ')

    @api.onchange('m_adv_pay','m_month_count','m_inst_count')
    def remove_lines(self):
        if self.state == 'draft':
            self.maintenance_deposit_ids = [(6, 0, [])]

    @api.onchange('cheque')
    def validate_chq_no(self):
        if self.cheque and not self.cheque.isnumeric():
            raise UserError('Cheque number must be digits only')

    def calc_deposit_lines(self):
        for rec in self:
            if rec.maintenance_deposit_ids:
                raise UserError('You Already Calculated...')
            self.env['loan.line.rs.own'].create({
                'contract_id': rec.id,
                'date': rec.date_payment,
                'name': "Adv Payment "+ str(rec.m_adv_pay)+' %',
                'amount': rec.total_maintenance * rec.m_adv_pay/100,
            })
        month = 0
        count = 1
        amount_diff = rec.total_maintenance - (rec.total_maintenance * rec.m_adv_pay/100)
        for iter in range(0, rec.m_inst_count):
            self.env['loan.line.rs.own'].create({
                'contract_id': rec.id,
                'date': rec.date_payment + relativedelta(months=+month),
                'name': "Deposit #"+ str(count),
                'amount': amount_diff / rec.m_inst_count,
            })
            month += round(rec.m_month_count)
            count +=1

    def calc_cheques(self):
        if not self.maintenance_deposit_ids:
            raise UserError(_('Create Maintenance Deposit lines first'))
        if not self.m_journal_id:
            raise UserError(_('Please enter Select Journal'))
        if not self.m_journal_id.cheque_recieve:
            raise UserError(_('Please enter Select cheque Journal'))
        journal = self.m_journal_id
        if not journal:
            raise UserError(_('Please create a cheques wallet journal!'))
        if not self.m_cheque:
            raise UserError(_('Please enter 1st cheque # '))
        for rec in self:
            amls = []
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_('Please set receivable account for partner!'))
            if not rec.m_cheque_bank_id:
                raise UserError(_('Please set Cheque Bank '))

            for line in rec.maintenance_deposit_ids:
                bank = rec.m_cheque_bank_id
                if line.name != 'Advance Payment':
                    payment = self.env['account.payment'].create({
                        'ref': rec.name,
                        'journal_id': journal.id,
                        'ownership_id': rec.id,
                        'partner_id': rec.partner_id.id,
                        'cheque_no': str(int(rec.m_cheque) + rec.maintenance_deposit_ids.ids.index(line.id)),
                        'cheque_bank': bank and bank.id or False,
                        'cheque_date': line.date,
                        'date': line.date,
                        'effective_date': line.date,
                        'amount': line.amount,
                        'type_cheq': 'recieve_chq',
                        'is_cheque': 1,
                    })
                    payment.action_post()
                    # rec.m_is_create = True
                    line.cheque_payment = payment.id
        # payment.action_post()
        # rec.m_is_create = True
        line.cheque_payment = payment.id


class MaintenanceDeposit(models.Model):
    _inherit = 'loan.line.rs.own'

    # m_is_create = fields.Boolean(' ')
    contract_id = fields.Many2one('ownership.contract')
    due_date = fields.Date()
    name2 = fields.Char()
    name = fields.Char()
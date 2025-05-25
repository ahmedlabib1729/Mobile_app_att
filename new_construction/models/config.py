from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class Company(models.Model):
    _inherit = "res.company"

    ks_middle_journal_owner = fields.Many2one('account.journal', string="Middle account Recieve ")
    ks_middle_account_sup = fields.Many2one('account.journal', string="Middle account send")
    tender_related = fields.Boolean(string="Tender Module")

    def write(self,vals):
        res=super(Company, self).write(vals)
        if 'tender_related' in vals:
            if vals['tender_related'] ==True:
                xml_records = self.env['ir.model.data']._xmlid_to_res_id('base.module_tender_contract')

                if xml_records:
                    res_id = xml_records
                    app_id  =  self.env['ir.module.module'].search([('id','=',res_id)])
                    app_id.button_immediate_install()
                else:
                    raise ValidationError("Please Contact with admin to add tender contract module")
        return res



class KSResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ks_middle_journal_owner = fields.Many2one('account.journal', string="Owner Journal",
                                        related='company_id.ks_middle_journal_owner', readonly=False)
    ks_middle_account_sup = fields.Many2one('account.journal', string="sub contractor",
                                             related='company_id.ks_middle_account_sup', readonly=False)
    tender_related = fields.Boolean(string="Tender Module",related='company_id.tender_related', readonly=False)

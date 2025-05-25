from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime


class JOBCOST(models.Model):
    _inherit = 'construction.job.cost'
    wbs_line_id = fields.Many2one("wbs.item.line", copy=False)
    wbs_id = fields.Many2one("wbs.item", copy=False)

    # @api.constrains('qty')
    # def check_qty_wbs(self):
    #     for rec in self:
    #         job_cost_ids = self.env['construction.job.cost'].sudo().search(
    #             [('tender_id', '=', rec.tender_id.id), ('techical_type', '=', True)])
    #         total_qty = sum(job_cost_ids.mapped('qty'))
    #         if rec.tender_id.qty < total_qty:
    #             raise ValidationError("Total Qty at tender must be greater than or equal wbs Qty")


class WBS_Item(models.Model):
    _name = "wbs.item"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    name = fields.Many2one('project.project', required=True, string="Project")
    partner_id = fields.Many2one("res.partner")
    item_ids = fields.One2many("wbs.item.line", "wbs_id", string="Lines")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancel')], string="State",
                             default='draft')
    job_cost_count=fields.Integer(compute='compute_job_cost_count')



    def action_confirm(self):
        self.state = 'confirm'
        for rec in self.item_ids:
            rec.state=self.state

    def action_cancel(self):
        self.state = 'cancel'
        for rec in self.item_ids:
            rec.state = self.state
    def compute_job_cost_count(self):
        for rec in self:
            rec.job_cost_count = 0
            if rec.id:
                job_cost_ids = self.env['construction.job.cost'].sudo().search([('wbs_id', '=', rec.id)])
                rec.job_cost_count = len(job_cost_ids)
    def view_job_techical(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Techical Estimation ',
            'view_mode': 'tree,form',
            'res_model': 'construction.job.cost',
            'domain': [('wbs_id', '=', self.id)],
            'target': 'current',
            'context': {'default_wbs_id': self.id,'default_techical_type':True}

        }


class WBS_lines(models.Model):
    _name = "wbs.item.line"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Many2one("wbs.name")
    wbs_id = fields.Many2one("wbs.item")
    project_id = fields.Many2one(related='wbs_id.name', string="Project")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    job_cost_count = fields.Integer(compute='compute_job_cost_count')
    is_created = fields.Boolean()
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancel')], string="State",
                             default='draft')

    @api.constrains('wbs_id')
    def check_wbs_id_confirm(self):
        for rec in self:
            if rec.wbs_id.state!='draft':
                raise ValidationError("You Cann't add at wbs confirmed")

    def compute_job_cost_count(self):
        for rec in self:
            rec.job_cost_count = 0
            if rec.id:
                job_cost_ids = self.env['construction.job.cost'].sudo().search([('wbs_line_id', '=', rec.id)])
                rec.job_cost_count = len(job_cost_ids)

    def create_job_cost(self):
        self.job_cost_count = 0
        job_cost_ids = self.env['construction.job.cost'].sudo().search(
            [('techical_type', '=', False), ('project_id', '=', self.project_id.id), ('state', '=', 'quotation')])

        if job_cost_ids:
            for rec in job_cost_ids:
                new = rec.sudo().copy()
                qty = self.get_remind_qty(rec.tender_id, self.wbs_id)
                new.qty = qty
                self.project_id.duplicte_job_cost(new, rec)

                new.techical_type = True
                new.wbs_line_id = self.id
                new.wbs_id = self.wbs_id.id
                self.job_cost_count += 1
        else:
            contract_id = self.env['construction.contract'].search([('project_id','=',self.project_id.id)])
            for con in contract_id:
                for rec in con.lines_id:
                    partner_id =self.wbs_id.partner_id.id if self.wbs_id.partner_id else ''
                    if con.partner_id_2:
                        partner_id=con.partner_id_2.id

                    other_job_ids = self.env['construction.job.cost'].sudo().search([('code','=',rec.code),('item','=',rec.item.id),('wbs_line_id.wbs_id','=',self.wbs_id.id)])
                    other_qty = sum(other_job_ids.mapped('qty'))


                    if rec.display_type==False:
                        self.job_cost_count += 1
                        self.env['construction.job.cost'].sudo().create({
                            # 'name': 'Job Cost/' + rec.code,
                            'project_id': self.wbs_id.name.id,
                            'partner_id': partner_id,
                            'code': rec.code,
                            'item': rec.item.id,
                            'description': rec.name,
                            'uom_id': rec.uom_id.id,
                            'qty': rec.qty-other_qty,

                            'notes': rec.notes,
                            'related_job': rec.related_job.id,
                            'version_num': 1,
                            'version': "V/" + str(1).zfill(5),
                            'wbs_line_id':self.id
                        }
                        )

        self.is_created = True

    def get_remind_qty(self, tender, wbs):
        wbs = self.env['construction.job.cost'].sudo().search([('tender_id', '=', tender.id), ('wbs_id', '=', wbs.id)])
        return tender.qty - sum(wbs.mapped('qty'))

    def view_job_techical(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Techical Estimation ',
            'view_mode': 'tree,form',
            'res_model': 'construction.job.cost',
            'domain': [('wbs_line_id', '=', self.id)],
            'target': 'current',
            'context':{'default_wbs_line_id':self.id,'default_techical_type':True}

        }

    def unlink(self):
        for rec in self:
            job_ids = self.env['construction.job.cost'].sudo().search([('wbs_line_id', '=', rec.id), \
                                                                       ('wbs_id', '=', rec.wbs_id.id),('state','!=','draft')])

            if job_ids:
                raise ValidationError("You Can't Delete ")
            job_ids = self.env['construction.job.cost'].sudo().search([('tender_id', '=', rec.id), \
                                                                       ('wbs_id', '=', rec.wbs_id.id),
                                                                       ('state', '!=', 'draft')])
            for job  in job_ids:
                job.unlink()
            res=super(WBS_lines, self).unlink()
            return res



class wbs_name(models.Model):
    _name = "wbs.name"
    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

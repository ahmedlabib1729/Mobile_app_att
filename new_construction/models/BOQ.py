from odoo import fields, models, api

import itertools
class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'
    boq_id = fields.Many2one('res.boq')
class ModelName(models.Model):
    _name = "res.boq"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Description'
    project_id = fields.Many2one("project.project")
    project_number = fields.Char(related='project_id.project_number', tracking=True)
    name = fields.Char(related='project_id.name', tracking=True)
    partner_id = fields.Many2one(related='project_id.partner_id', string="Customer")

    consultant = fields.Many2many(related='project_id.consultant', string="Consultant", tracking=True)
    analytic_account = fields.Many2one(related='project_id.analytic_account')
    date_from = fields.Date(related='project_id.date_from', string="Project Start Date", tracking=True)
    date_to = fields.Date(related='project_id.date_to', string="Project End Date", tracking=True)
    lines = fields.One2many(comodel_name='res.boq.lines', inverse_name='boq_id', string='', required=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    count_purchase = fields.Integer(compute='get_count_purchase')

    def get_count_purchase(self):
        for rec in self:
            rec.count_purchase=0
            if rec.id:
                purchas_id =self.env['purchase.request'].search([('boq_id','=',rec.id)])
                rec.count_purchase=len(purchas_id)

    def view_purchase_request(self):
        # view = self.env.ref('tender.mutli_edit_tender_view_tree')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Request Purchase ',
            'view_mode': 'tree,form',
            # 'view_id': view.id,
            'res_model': 'purchase.request',
            'domain': [('boq_id', '=', self.id)],
            'context': {'default_project_id': self.project_id.id},
            'target': 'current',


        }
    def create_purchase_request(self):
        line_ids=[]
        for rec in self.lines:
            line_ids.append((0,0,{
                'product_id':rec.product_id.id,
                'product_qty':rec.qty_pr,
                'product_uom_id':rec.uom_id.id,
            }))
        purchase_req_id = self.env['purchase.request'].create(
            {
                'boq_id':self.id,
                'project_id':self.project_id.id,
            }
        )
        purchase_req_id.line_ids=line_ids

    def refersh(self):
        for rec in self.lines:
            rec.sudo().unlink()
        lines = []
        materials_ids = self.env['construction.material'].sudo().search([('job_id.project_id', '=', self.project_id.id)])
        product_ids=[]
        for rec in materials_ids:
            product_ids.append({
                'id':rec.product_id.id,
                'product_id': rec.product_id,
                'uom_id': rec.uom_id.id,
                'uom': rec.uom_id,
                 'description': rec.description,
            })

        product_ids = sorted(product_ids, key=lambda i: (i['id'],i['uom_id']))
        i = 0
        docs=[]
        for key, group in itertools.groupby(product_ids, key=lambda x: (x['id'])):
            description=pro=uom=''

            for item in group:

                pro = item['product_id']
                uom = item['uom']
                description = item['description']

            docs.append({
                'description': description,
                'product_id': pro,
                'uom_id': uom
            })
        print("====================888888888888",docs)

        for rec in docs:

            self.env['res.boq.lines'].create({
                'product_id': rec['product_id'].id,
                'description': rec['description'],
                'uom_id': rec['uom_id'].id,
                'qty_pr': self.get_qty_pr(self.project_id, rec['product_id']),
                'qty_wbs': self.get_qty_wbs(self.project_id, rec['product_id']),
                'qty_po': self.get_qty_po(self.project_id, rec['product_id']),
                'qty_receipt': self.get_qty_receipt(self.project_id, rec['product_id']),
                'qty_deliverd': self.get_qty_deliverd(self.project_id, rec['product_id']),
                'qty_out': self.get_qty_out(self.project_id, rec['product_id']),
                'qty_onhand': self.get_qty_onhand(self.project_id, rec['product_id']),
                'price_avg': self.get_price_avg(self.project_id, rec['product_id']),
                'price_break': self.get_price_break(self.project_id, rec['product_id']),
                'price_last_po': self.get_price_last_po(self.project_id, rec['product_id']),
                'qty_current': self.get_qty_current(self.project_id, rec['product_id']),
                'boq_id':self.id,
                'remaining_1':self.get_qty_pr(self.project_id, rec['product_id'])-self.get_qty_receipt(self.project_id, rec['product_id']),
                'remaining_2':self.get_qty_pr(self.project_id, rec['product_id'])- (self.get_qty_receipt(self.project_id, rec['product_id'])+self.get_qty_deliverd(self.project_id, rec['product_id'])),

            })

    def get_qty_current(self, project, product_id):

            picking_ids = self.env['stock.picking'].sudo().search(
                [('picking_type_id.code', '=', 'outgoing'), ('state', '=', 'assigned'), ('project_id', '=', project.id)])
            total = 0
            for rec in picking_ids.move_ids_without_package:
                if rec.product_id.id == product_id.id:
                    total += rec.forecast_availability
            return total
    def get_price_last_po(self, project, product_id):
        purchase_order_ids = self.env['purchase.order.line'].sudo().search([
            ('order_id.project_id', '=', project.id), \
            ('product_id', '=', product_id.id), ('order_id.state', '=', 'purchase')],order='id desc',limit=1)
        # total_qty = sum(purchase_order_ids.mapped('product_qty'))

        if purchase_order_ids:
            # total_price = sum(purchase_order_ids.mapped('price_unit'))

            return purchase_order_ids.price_unit

    def get_price_break(self, project, product_id):
        job_id = self.env['construction.job.cost'].sudo().search([('techical_type','=',True),('project_id', '=', project.id), ('wbs_id', '!=', False)])
        total = 0
        for rec in job_id.material_ids:
            if rec.product_id.id == product_id.id:
                total += rec.cost_subtotal

        return total
    def get_price_avg(self, project, product_id):
        purchase_order_ids = self.env['purchase.order.line'].sudo().search([
            ('order_id.project_id', '=', project.id), \
            ('product_id', '=', product_id.id), ('order_id.state', '=', 'purchase')])
        total_qty = sum(purchase_order_ids.mapped('product_qty'))

        if total_qty>0:
            total_price = sum(purchase_order_ids.mapped('price_unit'))

            print("==222222222222===",total_price,total_qty)


            return total_price / total_qty
        else:
            return 0

    def get_qty_onhand(self, project, product_id):
        return product_id.qty_available

    def get_qty_out(self, project, product_id):
        picking_ids = self.env['stock.picking'].sudo().search(
            [('picking_type_id.code', '=', 'outgoing'), ('project_id', '=', project.id), ('state', '=', 'done')])
        total = 0
        for rec in picking_ids.move_ids_without_package:
            if rec.product_id.id == product_id.id:
                total += rec.quantity_done
        return total

    def get_qty_deliverd(self, project, product_id):
        picking_ids = self.env['stock.picking'].sudo().search(
            [('picking_type_id.code', '=', 'outgoing'), ('project_id', '=', project.id), ('state', '=', 'assigned')])
        total = 0
        for rec in picking_ids.move_ids_without_package:
            if rec.product_id.id == product_id.id:
                total += rec.product_uom_qty
        return total

    def get_qty_receipt(self, project, product_id):
        picking_ids = self.env['stock.picking'].sudo().search(
            [
                ('picking_type_id.code', '=', 'incoming'),
                ('project_id', '=', project.id), ('state', '=', 'done')])
        total = 0
        for rec in picking_ids.move_ids_without_package:
            if rec.product_id.id == product_id.id:
                total += rec.quantity_done
        return total

    def get_qty_po(self, project, product_id):
        purchase_order_ids = self.env['purchase.order.line'].sudo().search([('order_id.project_id', '=', project.id),('product_id', '=', product_id.id), ('order_id.state', '=', 'purchase')])
        total = sum(purchase_order_ids.mapped('product_qty'))
        return total

    def get_qty_wbs(self, project, product_id):
        job_id = self.env['construction.job.cost'].sudo().search([('techical_type','=',True),('project_id', '=', project.id), ('wbs_id', '!=', False)])
        total = 0
        for rec in job_id.material_ids:
            if rec.product_id.id == product_id.id:
                total += rec.total_qty

        return total

    def get_qty_pr(self, project, product_id):
        purchase_order_ids = self.env['purchase.request.line'].sudo().search([
            ('request_id.project_id', '=', project.id),
            ('product_id', '=', product_id.id), ('request_id.state', '=', 'done')], order='id desc')
        total_qty = sum(purchase_order_ids.mapped('product_qty'))
        return total_qty




class BOQlines(models.Model):
    _name = "res.boq.lines"
    boq_id = fields.Many2one(comodel_name="res.boq")
    product_id = fields.Many2one("product.product", string="Product", readonly=True \
                                 , domain=[('material', '=', True)])
    description = fields.Char("Description")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
    qty_pr = fields.Float("BR_DO_quintity", readonly=True)
    qty_wbs = fields.Float("WBS Quanitity", readonly=True)
    qty_po = fields.Float("Order Quantity(PO confirm)", readonly=True)
    qty_receipt = fields.Float("Receipt quantity ", readonly=True)
    qty_deliverd = fields.Float("waitting Delivered", readonly=True)
    remaining_1 = fields.Float("Remaining_1", readonly=True)
    remaining_2 = fields.Float("Remaining_1", readonly=True)
    qty_out = fields.Float("الكمية المنصرفة", readonly=True)
    qty_onhand = fields.Float("quantity Onhand ", readonly=True)
    price_avg = fields.Float("Avg Purchase price", readonly=True)
    price_break = fields.Float("Break down cost", readonly=True)
    price_last_po = fields.Float("Last Purchase price", readonly=True)
    qty_current = fields.Float("Reserved quantity", readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

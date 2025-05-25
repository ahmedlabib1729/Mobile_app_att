from odoo import fields, models, api


class Wizard(models.Model):
    _name = "template.items"
    template_id = fields.Many2one("construction.engineer")
    items_ids= fields.Many2many(
         'product.item',"product_items","item","id")

    @api.onchange('template_id','items_ids')
    def _onchange_template_id(self):
        ids=[]
        if self.template_id.contract_id:

            contract_ids = self.env['construction.contract'].search(['|', ('id', '=', self.template_id.contract_id.id),
                                                                     ('partial_contract', '=',
                                                                      self.template_id.contract_id.id)])

            for rec in contract_ids.lines_id:
                ids.append(rec.item.id)

        domain = {'items_ids': [('id', 'in', ids)]}

        return {'domain': domain}
    def get_remind_qty(self, tender):
        lines = self.env['construction.engineer.lines'].search(
            [('contract_line_id', '=', tender), ('parent_id.state', '!=', 'cancel')])

        qty = sum(lines.mapped('qty'))
        return qty

    def action_save(self):
        ids=[]
        # contract_ids.append(self.template_id.contract_id.id)
        contract_ids = self.env['construction.contract'].search(['|',('id','=',self.template_id.contract_id.id),('partial_contract','=',self.template_id.contract_id.id)])
        # for rec in self:
        #     contract_ids.append(rec.id)
        contract_id_line = self.env['construction.contract.line'].sudo().search(
            [('contract_id', 'in',contract_ids.ids) \
                , ('item', 'in', self.items_ids.ids)])
        print('stage_ids',contract_ids.stage_ids)
        for st in contract_ids.stage_ids:
            # self.create_engineer_tem(self.project_id, rec.stage_id, tem_id, rec.prec)
            contract_id = self.env['construction.contract.line'].sudo().search(
                [('contract_id', '=', st.contract_id.id) \
                    , ('item', 'in', self.items_ids.ids)])

            print('contract_id', contract_id)
            for rec in contract_id:
                if not rec.stage_line_ids and not rec.display_type:
                    m_qty = self.get_remind_qty(rec.id)
                    if m_qty == 0:
                        m_qty = rec.qty
                    prec=st.prec
                    new_line = self.env['construction.engineer.lines'].create({
                        'parent_id': self.template_id.id,
                        'tender_id': rec.tender_id if rec.tender_id else '',
                        'stage_id': st.stage_id.id,
                        'remind_qty': abs(m_qty - ((rec.qty * prec) / 100)),
                        # 'qty': (rec.qty * prec) / 100,
                        'tender_qty': rec.qty,

                        'contract_line_id': rec.id,
                        'item': rec.item.id,
                        'other_prec': prec,
                        'uom_id': rec.uom_id.id,
                        'related_job': rec.related_job.id if rec.related_job else '',
                        'name': rec.name

                    })

                elif rec.display_type and not rec.stage_line_ids:
                    self.env['construction.engineer.lines'].create({
                        'parent_id': self.template_id.id,
                        'display_type': rec.display_type,
                        'name': rec.name,

                    })
        for rec in contract_id_line:
            print("==========================",rec.contract_id)
            print('stage_line_ids', rec.stage_line_ids)
            if rec.stage_line_ids:

                for st in rec.stage_line_ids:

                    main_stage_id = self.env['contract.stage.line'].search(
                        [('contract_id', '=', rec.contract_id.id), ('stage_id', '=', st.id)])
                    other_prec = st.prec
                    # if main_stage_id:
                    #     other_prec = main_stage_id.prec

                    m_qty = self.get_remind_qty(rec.id)
                    if m_qty == 0:
                        m_qty = rec.qty

                    self.env['construction.engineer.lines'].create({
                        'parent_id': self.template_id.id,
                        # 'tender_id': rec.tender_id if rec.tender_id else '',
                        'stage_id': st.stage_id.id,
                        'remind_qty': abs(m_qty - ((rec.qty * other_prec) / 100)),
                        # 'qty': (rec.qty * st.prec) / 100,
                        'tender_qty': rec.qty,
                        'contract_line_id': rec.id,
                        'item': rec.item.id,
                        'uom_id': rec.uom_id.id,
                        'other_prec': other_prec,
                        'related_job': rec.related_job.id if rec.related_job else '',
                        'name': rec.name

                    })
            # else:
            #     m_qty = self.get_remind_qty(rec.id)
            #     if m_qty == 0:
            #         m_qty = rec.qty
            #     self.env['construction.engineer.lines'].create({
            #         'parent_id': self.template_id.id,
            #         'remind_qty': abs(m_qty - ((rec.qty * 100) / 100)),
            #
            #         'tender_qty': rec.qty,
            #         'contract_line_id': rec.id,
            #         'item': rec.item.id,
            #         'uom_id': rec.uom_id.id,
            #         'other_prec': 100,
            #         'related_job': rec.related_job.id if rec.related_job else '',
            #         'name': rec.name
            #
            #     })
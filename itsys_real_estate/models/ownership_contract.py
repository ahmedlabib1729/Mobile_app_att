from datetime import datetime, timedelta
import time
import calendar
from odoo import api, fields, models
from odoo.tools.translate import _
from datetime import datetime, date, timedelta as td
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta as rd
import math
from dateutil.relativedelta import relativedelta



import logging

_logger = logging.getLogger(__name__)


class ownership_contract(models.Model):
    _name = "ownership.contract"
    _description = "Ownership Contract"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].get('ownership.contract')
        new_id = super(ownership_contract, self).create(vals)
        return new_id

    @api.model
    def _get_default_currency(self):
        return self.env.company.currency_id.id


    interest_rate = fields.Float(string='Interest Rate (%)', digits='Product Price')
    loan_amount = fields.Float(string='Loan Amount', digits='Product Price')
    mortgage_insurance = fields.Float(string='Mortgage Insurance', digits='Product Price')
    home_insurance = fields.Float(string='Home Insurance', digits='Product Price')
    hoa = fields.Float(string='HOA', digits='Product Price')
    property_tax = fields.Float(string='Property Tax', digits='Product Price')
    principal_interest = fields.Float(string='Principal & Interest', digits='Product Price')
    monthly_payment = fields.Float(string='Monthly Payment', digits='Product Price')
    advance_payment = fields.Float(string='Down Payment', digits='Product Price')
    advance_payment_percent = fields.Float(string='%', digits='Product Price')
    # pricing = fields.Integer('Home Pricing', related='building_unit.pricing', digits='Product Price', store=True)
    pricing = fields.Integer('Home Pricing', compute="compute_building_price", digits='Product Price')
    discount = fields.Boolean(tring='Discount ?', )
    discount_type = fields.Selection(string='Discount', selection=[
        ('fixed', 'Fixed'), ('percentage', 'Percentage')], default='fixed')
    discount_value = fields.Float("Discount Value")
    is_check = fields.Boolean()
    last_inst = fields.Float("Last installment")

    @api.onchange('building_unit', 'discount', 'discount_value', 'discount_type')
    @api.depends('building_unit', 'discount', 'discount_value', 'discount_type')
    def compute_building_price(self):
        for rec in self:
            if rec.discount is True:
                if rec.discount_type == 'fixed':
                    rec.pricing = rec.building_unit.pricing - rec.discount_value
                elif rec.discount_type == 'percentage':
                    rec.pricing = rec.building_unit.pricing - (rec.building_unit.pricing * (rec.discount_value / 100))

            else:
                rec.pricing = rec.building_unit.pricing

    currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
                                  string='Currency', default=_get_default_currency)
    entry_count = fields.Integer('Entry Count', compute='_entry_count')
    paid = fields.Float(compute='_check_amounts', string='Paid', store=True)
    balance = fields.Float(compute='_check_amounts', string='Balance', store=True)
    total_amount = fields.Float(compute='_check_amounts', string='Total Amount', store=True)
    total_npv = fields.Float(compute='_check_amounts', string='NPV', store=True)
    # ownership_contract Info
    name = fields.Char('Name', readonly=True)
    reservation_id = fields.Many2one('unit.reservation', 'Reservation')
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    date_payment = fields.Date('First Payment Date', required=True)
    # Building Info
    building = fields.Many2one('building', 'Building')
    no_of_floors = fields.Integer('# Floors')
    building_code = fields.Char('Code')
    # Building Unit Info
    building_unit = fields.Many2one('product.template', 'Building Unit',
                                    domain=[('is_property', '=', True), ('state', '=', 'free')], required=True)
    rplc_building_unit = fields.Many2one('product.template', 'New Building Unit',
                                         domain=[('is_property', '=', True), ('state', '=', 'free')])
    unit_code = fields.Char('Code')
    floor = fields.Char('Floor', )
    address = fields.Char('Address')
    origin = fields.Char('Source Document')
    template_id = fields.Many2one('installment.template', 'Payment Template', required=False)
    type = fields.Many2one('building.type', 'Building Unit Type')
    status = fields.Many2one('building.status', 'Building Unit Status')
    city = fields.Many2one('cities', 'City')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, )
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    building_area = fields.Integer('Building Unit Area m²', )
    loan_line = fields.One2many('loan.line.rs.own', 'loan_id')
    region = fields.Many2one('regions', 'Region')
    country = fields.Many2one('countries', 'Country')
    state = fields.Selection([('draft', 'Reservation'),
                              ('approval', 'Approval'),
                              ('confirmed', 'Contract'),
                              ('cancel', 'Canceled'),
                              ], 'State', default='draft')

    voucher_count = fields.Integer('Voucher Count', compute='_voucher_count')
    account_income = fields.Many2one('account.account', 'Income Account',
                                     default=lambda self: self.env['res.config.settings'].browse(
                                         self.env['res.config.settings'].search([])[-1].id).income_account.id if
                                     self.env['res.config.settings'].search([]) else "")
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account',
                                          default=lambda self: self.env['res.config.settings'].browse(
                                              self.env['res.config.settings'].search([])[-1].id).analytic_account.id if
                                          self.env['res.config.settings'].search([]) else "")
    old_contract = fields.Many2one('ownership.contract', 'Old Contract', )

    # Installments fields
    adv_pay = fields.Integer(string='Adv. Payment %', default=25, help="Advance payment percent ex. 25")
    handover_inst = fields.Integer(string='Handover installment %',
                                   help="Handover installment amount in percent ex. 10")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
                                 default=lambda self: self.env.company)

    # handover_inst = fields.Integer(string='Handover installment %', default=10, help="Handover installment amount in percent ex. 10")
    handover_seq = fields.Integer(string='Loan Sequence',
                                  help="Sequence of handover installment ex. 8th installment")
    # handover_seq = fields.Integer(string='Handover Sequence', default=8, help="Sequence of handover installment ex. 8th installment")

    yearly_inst = fields.Integer(string='yearly installment %',
                                 help="yearly installment amount in percent ex. 10")
    yearly_seq = fields.Integer(string='yearly Sequence', )
    month_count = fields.Integer(string='Inst. Plan Duration months', default=120,
                                 help="Installment Plan Duration or Total number of months \n ex. 120 months / 10 years")
    inst_count = fields.Integer(string='Installments count', default=40,
                                help="Total number of intallments \n ex. 40 means every 3 months for the 120 months plan")

    is_create = fields.Boolean()
    one_year_inst = fields.Boolean('Repeat yearly installments')
    year_inst_count = fields.Integer(string='Year Installments count')

    journal_id = fields.Many2one("account.journal")
    entry_count_payment = fields.Integer(compute='get_payments')
    counter_penalty = fields.Integer(string="Counter Penalty", required=False, compute="_compute_counter_penalty")

    def action_view_penalty_reservation(self):
        self.ensure_one()
        return {
            'name': _('Penalty'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('penalty_id', '=', self.id)],
            'target': 'current',
        }

    def _compute_counter_penalty(self):
        for rec in self:
            contracts = self.env['account.move'].sudo().search(
                [('penalty_id', '=', rec.id)])
            rec.counter_penalty = len(contracts)



    def get_payments(self):
        self.entry_count_payment = 0
        move_obj = self.env['account.payment']
        move_ids = move_obj.search([('ownership_id', 'in', self.ids)])
        self.entry_count_payment = len(move_ids)

    def replace_unit(self):
        adv_pay = (100 * self.paid) / self.rplc_building_unit.pricing
        vals = {
            'partner_id': self.partner_id.id,
            'building_unit': self.rplc_building_unit.id,
            'date_payment': fields.Date.today(),
            'old_contract': self.id,
            'month_count': self.month_count,
            'inst_count': self.inst_count,
            'adv_pay': adv_pay,
            'handover_inst': self.handover_inst,
            'handover_seq': self.handover_seq,
        }
        new_contract = self.env['ownership.contract'].create(vals)
        self.action_cancel()
        return {
            'name': _('Contracts'),
            'type': 'ir.actions.act_window',
            'res_id': new_contract.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ownership.contract',
        }

    @api.constrains('partner_id')
    def set_unit_reservation(self):
        self.building_unit.partner_id = self.partner_id
        self.building_unit.state = self.partner_id and 'reserved' or 'free'

    @api.onchange(
        'building_unit',
        'adv_pay',
        'month_count',
        'inst_count',
        'handover_inst',
        'yearly_inst', 'yearly_seq',
        'handover_seq',
    )
    @api.constrains(
        'building_unit',
        'adv_pay',
        'month_count',
        'inst_count',
        'handover_inst',
        'yearly_inst', 'yearly_seq',
        'handover_seq',
    )
    def update_lines(self):
        self.loan_line = None

    @api.constrains('loan_line')
    def constrain_on_total_loan(self):
        total = sum(self.loan_line.mapped("amount"))
        total = sum(self.loan_line.mapped("amount"))+self.handover_inst
        print("==================================", self.pricing, total)
        if self.pricing < total and abs(self.pricing - total) <= 1:
            last_line_id = self.env['loan.line.rs.own'].search([('loan_id', '=', self.id)], order='id desc',
                                                               limit=1)
            last_line_id.amount -= abs(self.pricing - total)
            return
        # if self.loan_line and self.is_check == True:
        #     if total and total != self.pricing:
        #         print('------', total, self.pricing,total-self.pricing)
        #         raise UserError("Please check Installments Total Payment Must be Equal to Home Pricing")

    def update_inst_lines(self):
        self.loan_line = None
        self._cr.commit()
        loan_lines = self.compute_installments()
        total_npv = sum(l[2]['npv'] for l in loan_lines)
        npv = (100 * total_npv) / self.pricing
        if npv < 10:
            raise UserError(f''' {npv}
            The Plan is invalid, Try to adjust it using below points:\n
            - Increase "Adv. Payment" or "Handover Inst." or "Inst. Count"\n
            - Reduce "Total # of Months" or "handover sequence"
            ''')
        else:
            self.loan_line = loan_lines

            self.is_check = True

    def compute_installments(self):
        changes = 0
        npv = float(self.env['ir.config_parameter'].sudo().get_param('itsys_real_estate.npv')) / 100
        # _logger.error(f'>>>>>>>>>>>>>>>> NPV: {npv}')
        inst_lines = []
        name = self.name or 'new'
        inst_count = self.inst_count or 0
        amount = self.pricing or 0
        start_date = self.date_payment or date.today()
        adv_pay = amount * (self.adv_pay / 100 or 0 / 100)
        adv_pay_int = int(adv_pay)
        if adv_pay > adv_pay_int:
            changes += adv_pay - adv_pay_int
            print('changes ', adv_pay - adv_pay_int)
            adv_pay = adv_pay_int

        handover_inst = amount * (self.handover_inst / 100 or 0 / 100)
        yearly_inst = amount * (self.yearly_inst / 100 or 0 / 100)
        yearly_seq = 0
        if self.yearly_seq > 0:
            if self.one_year_inst:
                yearly_seq = self.year_inst_count
            else:
                yearly_seq = int(self.inst_count / self.yearly_seq)
        else:
            yearly_seq = 0

        inst_count = self.inst_count  # > 0 and self.inst_count or 1
        month_count = self.month_count  # > 0 and self.month_count or 1
        rem_inst_amount = amount - adv_pay - handover_inst - (yearly_seq * yearly_inst) - self.last_inst

        g1_inst_amount = (rem_inst_amount) / round(inst_count)
        g2_inst_amount = (rem_inst_amount) / round(inst_count)
        if inst_count % 2 > 0:
            inst_count += 1
            # self.inst_count = inst_count
            # self._cr.commit()
        inst_months = round(month_count / inst_count)
        # self.inst_count = month_count / inst_months

        # if self.handover_seq > int(inst_count / 2):
        #     raise UserError(f"Handover Sequence max is {int(inst_count / 2)}.")
        # if self.handover_inst + self.adv_pay < 30:
        #     raise UserError('Adv. Payment + Handover Payment must be at least 30%')
        inst_lines.append(
            (0, 0, {
                'number': (name + ' / ' + 'advance payment'),
                'amount': adv_pay,
                'date': start_date,
                'name': 'Advance Payment',
                'npv': adv_pay,
            }),
        )

        # irng = range(1, int(inst_count)+1)

        repeat_year_inst = 0
        irng = range(1, int(self.inst_count) + 1)
        idate = ''
        for ili in irng:
            iseq = ili
            mns = iseq * inst_months
            idate = start_date + rd(months=mns)
            amount = 0
            name = f'Inst # {str(iseq)} / {mns} months'
            if iseq <= (len(irng)) + 1:
                amount = g1_inst_amount
            else:
                amount = g2_inst_amount
            print("D>D>>D", iseq, self.handover_seq)

            if handover_inst > 0:
                if iseq == self.handover_seq:
                    handover_inst_int = handover_inst
                    if handover_inst > handover_inst_int:
                        changes += handover_inst - handover_inst_int
                        print('changes ', handover_inst - handover_inst_int)
                        handover_inst = handover_inst_int

                    inst_lines.append(
                        (0, 0, {
                            'number': (self.name + ' / ' + str(iseq)),
                            'amount': handover_inst,
                            'date': idate,
                            'name': '(Loan )',
                            'npv': handover_inst,
                        }),
                    )

            if yearly_inst > 0:
                yearly_inst_int = int(yearly_inst)
                if yearly_inst > yearly_inst_int:
                    changes += yearly_inst - yearly_inst_int
                    print('changes ', yearly_inst - yearly_inst_int)
                    yearly_inst = yearly_inst_int

                if (iseq % self.yearly_seq) == 0 and repeat_year_inst != self.year_inst_count:
                    # amount = handover_inst
                    # name += ' (Handover)'
                    if self.one_year_inst and repeat_year_inst != self.year_inst_count:
                        repeat_year_inst += 1
                        inst_lines.append(
                            (0, 0, {
                                'number': (self.name + ' / ' + str(iseq)),
                                'amount': yearly_inst,
                                'date': idate,
                                'name': '(Yearly)',
                                'npv': inpv,
                            }),
                        )
                    elif not self.one_year_inst:
                        inst_lines.append(
                            (0, 0, {
                                'number': (self.name + ' / ' + str(iseq)),
                                'amount': yearly_inst,
                                'date': idate,
                                'name': '(Yearly)',
                                'npv': inpv,
                            }),
                        )

            inpv = amount / (1 + (npv / 12)) ** mns
            inpv_int = (inpv)
            if inpv > inpv_int:
                inpv = inpv_int
                print('changes inpv', inpv - inpv_int)

            amount_int = (amount)
            if amount > amount_int:
                changes += amount - amount_int
                print('changes ', amount - amount_int)
                amount = amount_int

            if int(self.inst_count) == iseq:
                amount += changes
                inpv += changes
                print('amount become ', (self.name + ' / ' + str(iseq)), amount, changes)
            inst_lines.append(
                (0, 0, {
                    'number': (self.name + ' / ' + str(iseq)),
                    'amount': amount,
                    'date': idate,
                    'name': name,
                    'npv': inpv,
                }),
            )
        idate = start_date + rd(months=mns)

        if handover_inst > 0:
            if self.handover_seq == self.inst_count + 1:
                handover_inst_int = handover_inst
                if handover_inst > handover_inst_int:
                    changes += handover_inst - handover_inst_int
                    print('changes ', handover_inst - handover_inst_int)
                    handover_inst = handover_inst_int

                inst_lines.append(
                    (0, 0, {
                        'number': (self.name + ' / ' + str(self.handover_seq)),
                        'amount': handover_inst,
                        'date': idate,
                        'name': '(Loan )',
                        'npv': handover_inst,
                    }),
                )

        if self.last_inst:
            inst_lines.append(
                (0, 0, {
                    'number': (self.name + ' / ' + 'Last Inst'),
                    'amount': self.last_inst,
                    'date': idate,
                    'name': "Last Inst",
                    'npv': self.last_inst,
                }),
            )
        return inst_lines

    def _prepare_lines(self, first_date):
        if self.template_id:
            ind = 1
            mon = self.template_id.duration_month
            yr = self.template_id.duration_year
            repetition = self.template_id.repetition_rate
            advance_percent = self.template_id.adv_payment_rate
            deduct = self.template_id.deduct
            if not first_date:
                raise UserError(_('Please select first payment date!'))
            # first_date=datetime.strptime(first_date, '%Y-%m-%d').date()
            adv_payment = pricing * float(advance_percent) / 100
            if mon > 12:
                x = mon / 12
                mon = (x * 12) + mon % 12
            mons = mon + (yr * 12)
            if adv_payment:
                loan_lines.append((0, 0,
                                   {'number': (self.name + ' - ' + str(ind)), 'amount': adv_payment, 'date': first_date,
                                    'name': _('Advance Payment')}))
                ind += 1
                if deduct:
                    pricing -= adv_payment
            loan_amount = (pricing / float(mons)) * repetition
            m = 0
            while m < mons:
                loan_lines.append((0, 0,
                                   {'number': (self.name + ' - ' + str(ind)), 'amount': loan_amount, 'date': first_date,
                                    'name': _('Loan Installment')}))
                ind += 1
                first_date = self.add_months(first_date, repetition)
                m += repetition
        return loan_lines

    def _entry_count(self):
        move_obj = self.env['account.move']
        move_ids = move_obj.search([('ownership_id', 'in', self.ids)])
        self.entry_count = len(move_ids)

    def view_payments(self):
        entries = []
        entry_obj = self.env['account.payment']
        entry_ids = entry_obj.search([('ownership_id', 'in', self.ids)])
        for obj in entry_ids: entries.append(obj.id)

        return {
            'name': _('Payment /cheques'),
            'domain': [('id', 'in', entries)],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'view_id': False,
            'target': 'current',
        }

    def view_entries(self):
        entries = []
        entry_obj = self.env['account.move']
        entry_ids = entry_obj.search([('ownership_id', 'in', self.ids)])
        for obj in entry_ids: entries.append(obj.id)

        return {
            'name': _('Journal Entries'),
            'domain': [('id', 'in', entries)],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'view_id': False,
            'target': 'current',
        }

    @api.depends('loan_line.npv', 'loan_line.amount', 'loan_line.total_paid_amount', 'loan_line')
    def _check_amounts(self):
        total_paid = 0
        total_npv = 0
        total = 0
        for rec in self:
            for line in self.loan_line:
                total_paid += line.total_paid_amount
                total += line.amount
                total_npv += line.npv

            price = rec.pricing or 1
            rec.paid = total_paid
            rec.balance = (total - total_paid)
            rec.total_amount = total
            rec.total_npv = (100 * total_npv) / price

    def _voucher_count(self):
        voucher_obj = self.env['account.payment']
        voucher_ids = voucher_obj.search([('real_estate_ref', '=', self.name)])
        self.voucher_count = len(voucher_ids)

    @api.onchange('interest_rate', 'pricing', 'advance_payment_percent', 'property_tax', 'hoa', 'advance_payment',
                  'home_insurance', 'mortgage_insurance')
    def onchange_mortgage(self):
        if self.pricing:
            monthly_int = self.interest_rate / 100 / 12
            self.advance_payment = self.pricing * self.advance_payment_percent / 100.0
            self.loan_amount = self.pricing - self.advance_payment
            d = (1 - ((1 + monthly_int) ** 360))

            if d:
                self.principal_interest = (self.loan_amount * monthly_int) / d
            self.monthly_payment = self.principal_interest + self.property_tax + self.hoa + self.home_insurance + self.mortgage_insurance

    def unlink(self):
        if self.state != 'draft':
            raise UserError(_('You can not delete a contract not in draft state'))
        else:
            if self.building_unit:
                self.building_unit.write({
                    'state': 'free',
                    'partner_id': False,
                })
        super(ownership_contract, self).unlink()

    def view_vouchers(self):
        vouchers = []
        voucher_obj = self.env['account.payment']
        voucher_ids = voucher_obj.search([('real_estate_ref', '=', self.name)])
        for obj in voucher_ids: vouchers.append(obj.id)

        return {
            'name': _('Receipts'),
            'domain': [('id', 'in', vouchers)],
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'view_id': False,
            'target': 'current',
        }

    def unit_status(self):
        return self.building_unit.state

    def approval(self):
        self.write({'state': 'approval'})

    installment_group = fields.Boolean(compute='calc_installment_group')

    def calc_installment_group(self):
        for r in self:
            if (self.env.user.has_group('itsys_real_estate.group_edit_installment')):
                r.installment_group = True
            else:
                r.installment_group = False


    def action_confirm(self):
        unit = self.building_unit
        unit.write({
            'state': 'sold',
            'partner_id': self.partner_id.id,
        })
        self.write({'state': 'confirmed'})
        self.generate_entries()

    def action_cancel(self):
        unit = self.building_unit
        unit.write({'state': 'free', 'partner_id': False, })
        self.generate_cancel_entries()
        self.write({'state': 'cancel'})
        for l in self.loan_line:
            payment = self.env['account.payment'].sudo().search([('ownership_line_id', '=', l.id)])
            if payment:
                payment.action_cancel()
        self.loan_line = [(5,0,0)]

    # @api.onchange('country')
    def onchange_country(self):
        if self.country:
            city_ids = self.env['cities'].search([('country_id', '=', self.country.id)])
            cities = []
            for u in city_ids: cities.append(u.id)

            return {'domain': {'city': [('id', 'in', cities)]}}

    # @api.onchange('city')
    def onchange_city(self):
        if self.city:
            region_ids = self.env['regions'].search([('city_id', '=', self.city.id)])
            regions = []
            for u in region_ids: regions.append(u.id)
            return {'value': {'country': self.city.country_id.id}, 'domain': {'region': [('id', 'in', regions)]}}

    # @api.onchange('region')
    def onchange_region(self):
        if self.region:
            building_ids = self.env['building'].search([('region_id', '=', self.region.id)])
            buildings = []
            for u in building_ids: buildings.append(u.id)
            return {'value': {'city': self.region.city_id.id}, 'domain': {'building': [('id', 'in', buildings)]}}

    # @api.onchange('building')
    def onchange_building(self):
        if self.building:
            units = self.env['product.template'].search(
                [('is_property', '=', True), ('building_id', '=', self.building.id), ('state', '=', 'free')])
            unit_ids = []
            for u in units: unit_ids.append(u.id)
            building_obj = self.env['building'].browse(self.building.id)
            code = building_obj.code
            no_of_floors = building_obj.no_of_floors
            region = building_obj.region_id.id
            if building_obj:
                return {'value': {'building_code': code,
                                  'region': region,
                                  'no_of_floors': no_of_floors},
                        'domain': {'building_unit': [('id', 'in', unit_ids)]}}

    def add_months(self, sourcedate, months):
        month = sourcedate.month - 1 + months
        year = int(sourcedate.year + month / 12)
        month = month % 12 + 1
        day = min(sourcedate.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    @api.onchange('building_unit')
    def onchange_unit(self):
        self.unit_code = self.building_unit.code
        self.floor = self.building_unit.floor
        self.pricing = self.building_unit.pricing
        self.type = self.building_unit.ptype
        self.address = self.building_unit.address
        self.status = self.building_unit.status
        self.building_area = self.building_unit.building_area
        self.building = self.building_unit.building_id.id
        self.region = self.building_unit.region_id.id
        self.country = self.building_unit.country_id.id
        self.city = self.building_unit.city_id.id

    @api.onchange('reservation_id')
    def onchange_reservation(self):
        self.building = self.reservation_id.building.id
        self.city = self.reservation_id.city.id
        self.region = self.reservation_id.region.id
        self.building_code = self.reservation_id.building_code
        self.partner_id = self.reservation_id.partner_id.id
        self.building_unit = self.reservation_id.building_unit.id
        self.unit_code = self.reservation_id.unit_code
        self.address = self.reservation_id.address
        self.floor = self.reservation_id.floor
        self.building_unit = self.reservation_id.building_unit.id
        self.pricing = self.reservation_id.pricing
        self.date_payment = self.reservation_id.date_payment
        self.template_id = self.reservation_id.template_id.id
        self.type = self.reservation_id.type
        self.status = self.reservation_id.status
        self.building_area = self.reservation_id.building_area
        if self.template_id:
            loan_lines = self._prepare_lines(self.date_payment)
            self.loan_line = loan_lines

    def create_move(self, rec, debit, credit, move, account):
        move_line_obj = self.env['account.move.line']
        move_line_obj.create({
            'name': rec.name,
            'partner_id': rec.partner_id.id,
            'account_id': account,
            'debit': debit,
            'credit': credit,
            'move_id': move,
        })

    cheque_no = fields.Char(string='1st Cheque #')
    # cheque_numbers = fields.Integer(string='Number OF Cheques')
    cheque_bank = fields.Many2one('res.bank', string='Cheques Bank')
    cheque_acc_id = fields.Many2one('account.account', string='Cheques Account')

    @api.onchange('cheque_no')
    def validate_chq_no(self):
        if self.cheque_no and not self.cheque_no.isnumeric():
            raise UserError('Cheque number must be digits only')

    def create_cheques(self):
        if not self.journal_id:
            raise UserError(_('Please enter Select Journal'))
        if not self.journal_id.cheque_recieve:
            raise UserError(_('Please enter Select cheque Journal'))

        # journal = self.env['account.journal'].search([('is_cheque', '=', True)], limit=1)
        journal = self.journal_id
        if not journal:
            raise UserError(_('Please create a cheques wallet journal!'))
        if not self.cheque_no:
            raise UserError(_('Please enter 1st cheque # '))
        # if not self.cheque_acc_id:
        #     self.cheque_acc_id = journal.default_account_id
        account_move_obj = self.env['account.move']

        for rec in self:
            amls = []
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_('Please set receivable account for partner!'))
            if not rec.cheque_bank:
                raise UserError(_('Please set Bank '))

            for line in rec.loan_line:
                bank = rec.cheque_bank
                if line.name != 'Advance Payment':
                    payment = self.env['account.payment'].create({
                        'ref': rec.name,
                        'journal_id': journal.id,
                        'ownership_id': rec.id,
                        'partner_id': rec.partner_id.id,
                        'cheque_no': str(int(rec.cheque_no) + rec.loan_line.ids.index(line.id)),
                        'cheque_bank': bank and bank.id or False,
                        'cheque_date': line.date,
                        'date': line.date,
                        'effective_date': line.date,
                        'amount': line.amount,
                        'type_cheq': 'recieve_chq',
                        'is_cheque': 1,

                    })
                    payment.action_post()
                    rec.is_create = True

            # am.action_post()

    def create_payment(self):
        if not self.journal_id:
            raise UserError(_('Please enter Select Journal'))
        if self.journal_id.cheque_cash:
            raise UserError(_('Please enter Select Cash Journal'))
        # journal = self.env['account.journal'].search([('is_cheque', '=', True)], limit=1)
        journal = self.journal_id
        if not journal:
            raise UserError(_('Please create a cheques wallet journal!'))

        # if not self.cheque_acc_id:
        #     self.cheque_acc_id = journal.default_account_id
        account_move_obj = self.env['account.move']

        for rec in self:
            amls = []
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_('Please set receivable account for partner!'))

            for line in rec.loan_line:
                bank = rec.cheque_bank
                if line.name != 'Advance Payment':
                    payment = self.env['account.payment'].create({
                        'ref': rec.name,
                        'journal_id': journal.id,
                        'ownership_id': rec.id,
                        'partner_id': rec.partner_id.id,

                        'date': line.date,
                        'amount': line.amount,

                    })
                    # payment.action_post()
                    rec.is_create = True

    def create_payment_cash(self):
        journal = self.env['account.journal'].search([('type', '=', 'cash')], limit=1)
        if not journal:
            raise UserError(_('Please create a cheques wallet journal!'))

        if not self.cheque_acc_id:
            self.cheque_acc_id = journal.default_account_id
        account_move_obj = self.env['account.move']

        for rec in self:
            amls = []
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_('Please set receivable account for partner!'))

            amount = 0
            for line in rec.loan_line:
                bank = rec.cheque_bank
                if line.name != 'Advance Payment':
                    amount += line.amount
            payment = self.env['account.payment'].create({
                'ref': rec.name,
                'journal_id': journal.id,
                'ownership_id': rec.id,
                'partner_id': rec.partner_id.id,

                'date': line.date,
                'amount': amount,

            })
            payment.action_post()
            rec.is_create = True

    def generate_entries(self):
        journal_pool = self.env['account.journal']
        journal = journal_pool.search([('type', '=', 'sale')], limit=1)
        if not journal:
            raise UserError(_('Please set sales accounting journal!'))
        account_move_obj = self.env['account.move']
        for rec in self:
            unit = rec.building_unit
            if not rec.account_income:
                rec.account_income = unit.property_account_income_id or unit.categ_id.property_account_income_categ_id

            amls = []
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_('Please set receivable account for partner!'))
            if not rec.account_income:
                raise UserError(_('Please set income account for this contract!'))

            for line in rec.loan_line:
                amls.append((0, 0, {
                    'name': line.name,
                    'partner_id': rec.partner_id.id,
                    'account_id': rec.partner_id.property_account_receivable_id.id,
                    'date_maturity': line.date,
                    'debit': round(line.amount, 2),
                    'credit': 0.0
                }))

            amls.append((0, 0, {
                'name': rec.name,
                'partner_id': rec.partner_id.id,
                'account_id': rec.account_income.id,
                'debit': 0.0,
                'credit': round(sum(a[2]['debit'] for a in amls), 2)
            }))

            am = account_move_obj.create({
                'ref': rec.name,
                'journal_id': journal.id,
                'ownership_id': rec.id,
                'line_ids': amls,
            })

            am.action_post()

    def generate_cancel_entries(self):
        # ToDo: reverse JE
        return True

    def create_activity(self, user_id, res_id, note):
        mail_activity_data_todo = self.env.ref('mail.mail_activity_data_todo').id
        model_id = self.env['ir.model']._get('ownership.contract').id
        activity = self.env['mail.activity']
        act_dct = {
            'activity_type_id': mail_activity_data_todo,
            'note': note,
            'user_id': user_id,
            'res_id': res_id,
            'res_model_id': model_id,
            'date_deadline': fields.Date.today(self)
        }
        activity.sudo().create(act_dct)
        return True

    def notify_based_on_reservation_date(self):
        for rec in self.env['ownership.contract'].sudo().search([('state', '=', 'draft')]):
            if rec.reservation_date:
                date = rec.reservation_date + rd(weeks=1)
                if date == datetime.now().date():
                    rec.action_cancel()
        for rec in self.env['ownership.contract'].sudo().search([('state', '=', 'confirmed')]):
            if rec.reservation_date:
                date = rec.reservation_date + rd(weeks=2)
                if date == datetime.now().date():
                    rec.create_activity(rec.create_uid.id, rec.id, "Please Attach Contract")

    penalty_amount_type = fields.Selection([('amount','Amount'),('percentage','Percentage')])
    penalty_amount = fields.Float()
    penalty_percentage = fields.Float('Penalty%')
    penalty_days = fields.Float()

    @api.model
    def calc_penalty(self):
        for rec in self.search([('state','=','confirmed')]):
            for l in rec.loan_line.filtered(lambda x:x.penalty_amount > 0 and not x.disable_penalty):
                if l.payment_id:
                    counter_days = (l.payment_date - l.date).days if l.date and l.payment_date and l.date< l.payment_date else 0
                else:
                    counter_days = (fields.Date.today() - l.date).days if l.date and l.date< fields.Date.today() else 0
                calculation = (counter_days - l.penalty_days) - (l.no_penaltys*l.penalty_days)
                if calculation > 0 and l.penalty_days>0:
                    journal = int(self.env['ir.config_parameter'].get_param('itsys_real_estate.penalty_journal'))
                    debit = int(self.env['ir.config_parameter'].get_param('itsys_real_estate.debit_penalty_account'))
                    credit = int(self.env['ir.config_parameter'].get_param('itsys_real_estate.credit_penalty_account'))
                    rate = math.ceil(calculation/l.penalty_days)
                    l.no_penaltys += rate
                    for i in range(1,rate+1):
                        move = self.env['account.move'].create({
                            'move_type': 'entry',
                            'partner_id': l.loan_id.partner_id.id,
                            'journal_id': journal,
                            'penalty_id': l.loan_id.id,
                            'date':l.date+relativedelta(days=l.penalty_days*i),
                            'line_ids': [
                                (0, 0, {
                                    'account_id': debit,
                                    'debit': l.penalty_amount,
                                    'partner_id': l.loan_id.partner_id.id,
                                    'name': l.loan_id.name,
                                    'installment_id': l.id,
                                    'credit': 0
                                }),
                                (0, 0, {
                                    'account_id': credit,
                                    'partner_id': l.loan_id.partner_id.id,
                                    'credit': l.penalty_amount,
                                    'name': l.loan_id.name,
                                    'installment_id': l.id,
                                    'debit': 0

                                }),
                            ],
                        })
                        move.action_post()

    @api.onchange('penalty_amount')
    def change_penalty_amount_installments(self):
        for r in self:
            r.loan_line.update({'penalty_amount':r.penalty_amount})

    @api.onchange('penalty_percentage')
    def change_penalty_percentage_installments(self):
        for rec in self:
            for l in rec.loan_line:
                l.penalty_amount = l.amount * rec.penalty_percentage


    @api.onchange('penalty_days')
    def change_penalty_days_installments(self):
        for r in self:
            r.loan_line.update({'penalty_days':r.penalty_days})


class loan_line_rs_own(models.Model):
    _name = 'loan.line.rs.own'
    _order = 'number'

    def view_payments(self):
        payments = self.env['account.payment'].sudo().search([('ownership_line_id', '=', self.id)]).ids
        return {
            'name': _('Vouchers'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payments)],
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }

    def _count_payment(self):
        for rec in self:
            payments = self.env['account.payment'].sudo().search([('ownership_line_id', '=', rec.id)]).ids
            rec.payment_count = len(payments)

    @api.model
    def create(self, vals):
        vals['number'] = self.env['ir.sequence'].get('loan.line.rs.own')
        new_id = super(loan_line_rs_own, self).create(vals)
        return new_id

    @api.depends('amount', 'total_paid_amount')
    def _check_amounts(self):
        for rec in self:
            rec.total_remaining_amount = rec.amount - rec.total_paid_amount

    cancelled = fields.Boolean('Cancelled')
    number = fields.Char('Number')

    contract_user_id = fields.Many2one(string='User', related='loan_id.user_id', store=True)
    contract_partner_id = fields.Many2one(string='Partner', related='loan_id.partner_id', store=True)
    contract_building = fields.Many2one(string="Building", related='loan_id.building', store=True)
    contract_building_unit = fields.Many2one(related='loan_id.building_unit', string="Building Unit", store=True,
                                             domain=[('is_property', '=', True)])
    contract_city = fields.Many2one(related='loan_id.city', string="City", store=True)
    contract_region = fields.Many2one(related='loan_id.region', string="Region", store=True)
    contract_country = fields.Many2one(related='loan_id.country', string="Country", store=True)
    date = fields.Date('Due Date')
    name = fields.Char('Name')
    empty_col = fields.Char(' ', readonly=True)
    disable_penalty = fields.Boolean(default=False,copy=False)

    amount = fields.Float('Payment', digits=(16, 4), )
    npv = fields.Float('NPV', digits=(16, 4), )
    total_paid_amount = fields.Float('Paid Amount', digits=(16, 4))
    total_remaining_amount = fields.Float(compute='_check_amounts', string='Due Amount', digits=(16, 4), store=True)
    payment_id = fields.Many2one('account.payment',compute='calc_payment')
    payment_date = fields.Date(compute='calc_payment')
    no_penaltys = fields.Integer()
    total_entry_amount = fields.Float(compute='calc_total_entry_amount')
    penalty_status = fields.Selection([('no_penalty','No Penalty'),('not_paid','Not Paid'),('partially_paid','Partially Paid'),('fully_paid','Fully Paid')],compute='calc_penalty_status', store=True)

    def calc_penalty_status(self):
        for r in self:
            r.penalty_status = 'no_penalty'
            entry = self.env['account.move.line'].search(
                [('installment_id', '=', r.id), ('move_id.state', '=', 'posted')]).mapped('move_id.paid')
            if r.amount == r.total_paid_amount and all(entry) and r.no_penaltys>0:
                r.penalty_status = 'fully_paid'
            elif (r.amount != r.total_paid_amount and all(entry) and r.no_penaltys>0) or (r.amount == r.total_paid_amount and any(entry) and r.no_penaltys>0):
                r.penalty_status = 'partially_paid'
            elif (entry!=[] and r.no_penaltys>0):
                r.penalty_status = 'not_paid'

    def calc_total_entry_amount(self):
        for r in self:
            entry = self.env['account.move.line'].search([('installment_id','=',r.id),('move_id.state','=','posted')]).mapped('move_id.amount_total_signed')
            r.total_entry_amount = sum(entry)

    def calc_payment(self):
        for r in self:
            entry_obj = self.env['account.payment']
            entry_ids = entry_obj.search([('ownership_line_id', 'in', r.ids)],limit=1,order='id desc')
            if entry_ids:
                r.payment_id = entry_ids.id
                r.payment_date = entry_ids.date
            else:
                r.payment_id = False
                r.payment_date = False



    loan_id = fields.Many2one('ownership.contract', '', ondelete='cascade', readonly=True)
    status = fields.Char('Status')
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.user.company_id.id)

    payment_count = fields.Integer(compute='_count_payment', string='# Counts')
    penalty_days = fields.Integer()
    # penalty_percentage = fields.Float()
    penalty_amount = fields.Float()
    penalty = fields.Boolean(default=False,copy=False)

    # def calc_penalty_days(self):
    #     for r in self:
    #         if r.date and r.date< fields.Date.today():
    #             r.penalty_days = (fields.Date.today() - r.date).days
    #         else:
    #             r.penalty_days =0

    # def create_penalty(self):
    #     journal = int(self.env['ir.config_parameter'].get_param('itsys_real_estate.penalty_journal'))
    #     debit = int(self.env['ir.config_parameter'].get_param('itsys_real_estate.debit_penalty_account'))
    #     credit = int(self.env['ir.config_parameter'].get_param('itsys_real_estate.credit_penalty_account'))
    #     move = self.env['account.move'].create({
    #         'move_type': 'entry',
    #         'partner_id': self.loan_id.partner_id.id,
    #         'journal_id': journal,
    #         'penalty_id': self.loan_id.id,
    #         'line_ids': [
    #             (0, 0, {
    #                 'account_id': debit,
    #                 'debit': self.penalty_amount,
    #                 'partner_id': self.loan_id.partner_id.id,
    #                 'name': self.loan_id.name,
    #                 'credit': 0
    #             }),
    #             (0, 0, {
    #                 'account_id': credit,
    #                 'partner_id': self.loan_id.partner_id.id,
    #                 'credit': self.penalty_amount,
    #                 'name': self.loan_id.name,
    #                 'debit': 0
    #
    #             }),
    #         ],
    #     })
    #     move.action_post()
    #     self.penalty = True
    #     return {
    #         'name': _('Penalty'),
    #         'view_mode': 'form',
    #         'res_model': 'account.move',
    #         'type': 'ir.actions.act_window',
    #         'res_id':move.id,
    #         'target': 'current',
    #     }


    # def calc_penalty_amount(self):
    #     for r in self:
    #         if (fields.Date.today()- r.date).days >= r.penalty_days and r.total_remaining_amount:
    #             r.penalty_amount = r.total_remaining_amount * r.penalty_percentage
    #         else:
    #             r.penalty_amount = 0

    def send_multiple_installments(self):
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference('itsys_real_estate',
                                                         'email_template_installment_notification')[1]
        template_res = self.env['mail.template']
        template = template_res.browse(template_id)
        template.send_mail(self.id, force_send=True)


class AccountMove(models.Model):
    _inherit = 'account.move'
    ownership_id = fields.Many2one('ownership.contract', 'Unit Contract', ondelete='cascade', readonly=True)
    penalty_id = fields.Many2one('ownership.contract')
    paid = fields.Boolean(default=False,copy=False,compute='calc_paid_flag',store=True)
    
    @api.depends('line_ids.matching_number')
    def calc_paid_flag(self):
        for rec in self:
            if any(pay.matching_number != False for pay in rec.line_ids):
                rec.paid = True
            else:
                rec.paid = False




class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    ownership_id = fields.Many2one(
        'ownership.contract', 'Unit Contract', related="move_id.ownership_id",
        ondelete='cascade', readonly=True, store=True,
    )

    unit_id = fields.Many2one(
        'product.template', 'Unit RS', related="move_id.ownership_id.building_unit",
        ondelete='cascade', readonly=True, store=True,
    )
    installment_id = fields.Many2one('loan.line.rs.own')

from odoo import api, fields, models 

class installment_template(models.Model):
    _name = "installment.template"
    _description = "Installment Template"
    _inherit = ['mail.thread']

    name= fields.Char('Name',  required=True)
    duration_month= fields.Integer('Month')        
    duration_year= fields.Integer('Year')        
    annual_raise= fields.Integer('Annual Raise %')        
    repetition_rate= fields.Integer('Repetition Rate (month)', default=1)        
    adv_payment_rate= fields.Integer('Advance Payment %')        
    deduct= fields.Boolean('Deducted from amount?')
    note= fields.Text('Note')
from odoo import api, fields, models

class City(models.Model):
    _name='real.city'
    name = fields.Char( string='City Name')

class Zone(models.Model):
    _name='real.zone'
    name = fields.Char( string='Zone Name')
    city_id= fields.Many2one(comodel_name='real.city',string='City',)

class Floor(models.Model):
    _name='real.floor'
    name = fields.Char( string=' Name')
    city_id= fields.Many2one(comodel_name='real.city',string='City',related='building_id.n_city_id',store=True,readonly=False)
    zone_id= fields.Many2one(comodel_name='real.zone',string='Zone',related='building_id.n_zone_id',store=True,readonly=False)
    building_id= fields.Many2one(comodel_name='building',string='Building',)
class Entrance(models.Model):
    _name='real.entrance'
    name = fields.Char( string='Name')
    building_id= fields.Many2one(comodel_name='building',string='Building',)
    city_id= fields.Many2one(comodel_name='real.city',string='City',related='building_id.n_city_id',store=True,readonly=False)
    zone_id= fields.Many2one(comodel_name='real.zone',string='Zone',related='building_id.n_zone_id',store=True,readonly=False)
    floor_id= fields.Many2one(comodel_name='real.floor',string='Floor',)

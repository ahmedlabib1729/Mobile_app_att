# -*- coding: utf-8 -*-
# from odoo import http


# class EmplCommission(http.Controller):
#     @http.route('/empl_commission/empl_commission', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/empl_commission/empl_commission/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('empl_commission.listing', {
#             'root': '/empl_commission/empl_commission',
#             'objects': http.request.env['empl_commission.empl_commission'].search([]),
#         })

#     @http.route('/empl_commission/empl_commission/objects/<model("empl_commission.empl_commission"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('empl_commission.object', {
#             'object': obj
#         })

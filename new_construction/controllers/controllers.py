# -*- coding: utf-8 -*-
# from odoo import http


# class NewConstruction(http.Controller):
#     @http.route('/new_construction/new_construction', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/new_construction/new_construction/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('new_construction.listing', {
#             'root': '/new_construction/new_construction',
#             'objects': http.request.env['new_construction.new_construction'].search([]),
#         })

#     @http.route('/new_construction/new_construction/objects/<model("new_construction.new_construction"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('new_construction.object', {
#             'object': obj
#         })

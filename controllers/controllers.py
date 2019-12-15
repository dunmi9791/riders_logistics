# -*- coding: utf-8 -*-
from odoo import http

# class RidersLogistics(http.Controller):
#     @http.route('/riders_logistics/riders_logistics/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/riders_logistics/riders_logistics/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('riders_logistics.listing', {
#             'root': '/riders_logistics/riders_logistics',
#             'objects': http.request.env['riders_logistics.riders_logistics'].search([]),
#         })

#     @http.route('/riders_logistics/riders_logistics/objects/<model("riders_logistics.riders_logistics"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('riders_logistics.object', {
#             'object': obj
#         })
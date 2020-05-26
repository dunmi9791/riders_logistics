# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.exceptions import AccessError, MissingError


class Deliveries(http.Controller):

    @http.route('/deliveries/list/', auth='user', website=True, methods=['GET'], type='http')
    def list(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        return http.request.render('riders_logistics.deliveries', {
            'objects': http.request.env['delivery.order'].search([('client_id.user_ids.id', '=', http.request.uid)]),
        })

    searchbar_sortings = {
        'date': {'label': _('Delivery Date'), 'order': 'date desc'},
        'name': {'label': _('Reference'), 'order': 'name desc'},
        'state': {'label': _('Status'), 'order': 'state'},
    }


class PortalAccount(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(PortalAccount, self)._prepare_portal_layout_values()
        delivery_count = request.env['delivery.order'].search_count([])
        values['deliveries_count'] = delivery_count
        return values

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = {
            'page_name': 'invoice',
            'invoice': invoice,
        }
        return self._get_page_view_values(invoice, access_token, values, 'my_invoices_history', False, **kwargs)

    @http.route(['/my/deliveries', '/my/deliveries/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_deliveries(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['delivery.order']
        commercial_partner = request.env.user.commercial_partner_id.id

        domain = [
            ('client_id', '=', commercial_partner)
        ]

        searchbar_sortings = {
                'date': {'label': _('Delivery Date'), 'order': 'date desc'},
                'duedate': {'label': _('Due Date'), 'order': 'date_due desc'},
                'name': {'label': _('Reference'), 'order': 'name desc'},
                'state': {'label': _('Status'), 'order': 'state'},
            }
            # default sort by order
        if not sortby:
                sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('delivery.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

            # count for pager
        delivery_count = AccountInvoice.search_count(domain)
            # pager
        pager = portal_pager(
            url="/my/deliveries",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=delivery_count,
            page=page,
            step=self._items_per_page
        )
            # content according to pager and archive selected
        deliveries = AccountInvoice.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_deliveries_history'] = deliveries.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': deliveries,
            'page_name': 'delivery',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/deliveries',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("riders_logistics.portal_my_deliveries", values)


# class CustomerPortal(http.Controller):
#
#     @http.route(['/my/records/portal', '/my/quotes/page/<int:page>'], type='http', auth="user", website=True)
#     def portal_my_records(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
#         print("IN PYTHON CONTROLLER")
#         data = {}
#         return http.request.render("riders_logistics.delivery", data)
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

# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import datetime
from datetime import date


class DeliveryOrder(models.Model):
    _name = 'delivery.order'
    _rec_name = 'order_no'
    _description = 'New Description'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    order_no = fields.Char(string="Order Number", required=False,
                           default=lambda self: self.env['ir.sequence'].next_by_code('increment_orderno'),
                           requires=False, readonly=True, )
    delivery_address = fields.Text(string="Delivery Address", required=True, )
    pickup_location = fields.Many2one(comodel_name="res.partner", string="Pickup Location", required=False, )
    height = fields.Float(string="Height (m)", required=False, )
    width = fields.Float(string="Width (m)", required=False, )
    length = fields.Float(string="Length (m)", required=False, )
    volume = fields.Float(string="Volume (m3)", required=False, )
    weight = fields.Float(string="Weight (kg)", required=False, )
    package_type = fields.Selection(string="Package Type", selection=[('carton', 'carton'), ('envelope', 'envelope'), ],
                                    required=False, )
    is_payment_on_delivery = fields.Boolean(string="Payment on delivery", )
    amount = fields.Float(string="Amount to collect", required=False, )
    state = fields.Selection(string="", selection=[('Requested', 'Awaiting Pickup'), ('picked', 'Picked Up'),
                                                   ('Processed', 'Out for Delivery'), ('Delivered', 'Delivered'),
                                                   ('Canceled', 'Canceled'), ], required=False, default='Requested',
                             track_visibility='onchange', )
    date = fields.Date(string="Date", required=False, default=fields.Date.today())
    consignee = fields.Char(string="Consignee Name", required=True,)
    additional_instruction = fields.Text(string="Additional Instructions", required=False, )
    client_id = fields.Many2one(comodel_name="res.partner", string="Client", required=True, )
    thirdparty_id = fields.Many2one(comodel_name="thirdparty.delivery", string="Third Party courier", required=False, )

    @api.multi
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('Requested', 'picked'),
                   ('Requested', 'Canceled'),
                   ('picked', 'Processed'),
                   ('picked', 'Canceled'),
                   ('Processed', 'Delivered'), ]
        return (old_state, new_state) in allowed

    @api.multi
    def change_state(self, new_state):
        for cash in self:
            if cash.is_allowed_transition(cash.state, new_state):
                cash.state = new_state
            else:
                msg = _('Moving from %s to %s is not allowed') % (cash.state, new_state)
                raise UserError(msg)

    @api.multi
    def authorise(self):
        self.change_state('picked')

    @api.multi
    def process(self):
        self.change_state('Processed')

    @api.multi
    def receive(self):
        self.change_state('Delivered')

    @api.multi
    def cancel(self):
        self.change_state('Canceled')


class Collections(models.Model):
    _name = 'amount.collection'
    _rec_name = 'name'
    _description = 'Amount collected on delivery'

    name = fields.Char()
    amount = fields.Float(string="Amount", required=False, )
    delivery_order_id = fields.Many2one(comodel_name="delivery.order", string="Delivery Order", required=False, )
    date = fields.Date(string="Date", required=False, )
    mode = fields.Selection(string="Mode of collection", selection=[('pos', 'POS'), ('cash', 'Cash'), ],
                            required=False, )
    client = fields.Char(string="Client", related="", required=False, readonly=True, )


class ThirdParty(models.Model):
    _name = 'thirdparty.delivery'
    _description = 'collection of bulk packages via third party'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection(string="", selection=[('draft', 'draft'),('packaged', 'Packaged'), ('sent', 'Sent'),
                                                   ('received', 'Received')], required=False, )
    delivery_ids = fields.Many2many(comodel_name="delivery.order", string="Packages",
                                   required=False, )
    
class DeliveryClients(models.Model):
    _name = 'delivery.clients'
    _rec_name = ''
    _description = 'New Description'
    _inherit = 'res.partner'

class ThirdCourier(models.Model):
    _name = 'thirdparty.courier'
    _rec_name = 'name'
    _description = 'New Description'

    name = fields.Char()


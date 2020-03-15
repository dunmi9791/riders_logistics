# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from datetime import date
import time


class DeliveryOrder(models.Model):
    _name = 'delivery.order'
    _rec_name = 'order_no'
    _description = 'Deliveries'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    order_no = fields.Char(string="Order Number", required=False,
                           default=lambda self: _('New'),
                           requires=False, readonly=True, )
    delivery_address = fields.Text(string="Delivery Address", required=True, )
    pickup_location = fields.Many2one(comodel_name="pickup.location", string="Pickup Location", required=False, )
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
    consignee = fields.Char(string="Consignee Name", required=True, )
    consignee_number = fields.Char(string="Consignee Mobile Number", required=True)
    additional_instruction = fields.Text(string="Additional Instructions", required=False, )
    states = fields.Many2one(comodel_name='states.nigeria', string='State')
    lga = fields.Many2one(comodel_name='local.governments', string='LGA')
    client_id = fields.Many2one(comodel_name="res.partner", string="Client", required=True, change_default=True,
                                index=True, track_visibility='always', track_sequence=1, )
    thirdparty_id = fields.Many2one(comodel_name="thirdparty.delivery", string="Third Party courier", required=False, )
    thirdparty_ids = fields.One2many(comodel_name="thirdparty.delivery", inverse_name="delivery_ids",
                                     string="Third Party Courier", required=False, )
    product_id = fields.Many2one(comodel="product.product", string="Service Type")
    charges = fields.One2many('delivery.charges', 'order_id', 'Charges', required=False)
    invoice = fields.Many2one(comodel_name="account.invoice")
    total_amount = fields.Float(string="Total Charge", compute="get_total")
    service_id = fields.Many2one(comodel_name="product.template", string="Service type")
    invoice_status = fields.Selection([
        ('upselling', 'Upselling Opportunity'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
    ], string='Invoice Status', invisible=1, )
    collected = fields.Boolean(string="Collected", default=True)
    sale_obj = fields.Many2one('sale.order', invisible=1)
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=False,
                                         states={'Requested': [('readonly', False)],
                                                 'Processed': [('readonly', False)]},
                                         help="Invoice address for current sales order.")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=False,
                                          states={'Requested': [('readonly', False)],
                                                  'Processed': [('readonly', False)]},
                                          help="Delivery address for current sales order.")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', oldname='payment_term')
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=False, readonly=True,
                                   states={'Requested': [('readonly', False)], 'Delivered': [('readonly', False)]},
                                   help="Pricelist for current sales order.")
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)

    # @api.onchange('client_id')
    # def onchange_client_id(self):
    #     for rec in self:
    #         return {'domain': {'pickup_location': [('client_id', '=', rec.client_id.id)]}}

    @api.onchange('states')
    def onchange_states(self):
        for rec in self:
            return {'domain': {'lga': [('state', '=', rec.states.id)]}}

    @api.multi
    @api.onchange('client_id')
    def onchange_client_id(self):
        for rec in self:
            return {'domain': {'pickup_location': [('client_id', '=', rec.client_id.id)]}}
        """
        Update the following fields when the partner is changed:
        - Pricelist
        - Payment terms
        - Invoice address
        - Delivery address
        """
        if not self.client_id:
            self.update({
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return

        addr = self.client_id.address_get(['delivery', 'invoice'])
        values = {
            'pricelist_id': self.client_id.property_product_pricelist and self.client_id.property_product_pricelist.id or False,
            'payment_term_id': self.client_id.property_payment_term_id and self.client_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'user_id': self.client_id.user_id.id or self.client_id.commercial_partner_id.user_id.id or self.env.uid
        }
        if self.env['ir.config_parameter'].sudo().get_param(
            'sale.use_sale_note') and self.env.user.company_id.sale_note:
            values['note'] = self.with_context(lang=self.client_id.lang).env.user.company_id.sale_note

        if self.client_id.team_id:
            values['team_id'] = self.client_id.team_id.id
        self.update(values)

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
        sale_obj = self.env['sale.order'].create({'partner_id': self.client_id.id,
                                                  'partner_invoice_id': self.client_id.id,
                                                  'partner_shipping_id': self.client_id.id,
                                                  'delivery_id': self.id})
        self.sale_obj = sale_obj
        self.env['sale.order.line'].create({'product_id': self.charges.product_id.id,
                                            'price_unit': self.charges.unit_cost,
                                            'order_id': sale_obj.id
                                            })
        if self.is_payment_on_delivery:
            self.collected = False

    @api.multi
    def receive(self):
        if self.is_payment_on_delivery:
            if self.collected:
                self.change_state('Delivered')
                if self.sale_obj.state in ['draft', 'sent']:
                    self.sale_obj.action_confirm()
                self.invoice_status = self.sale_obj.invoice_status
                # return {
                #     'name': 'Invoice Order',
                #     'view_type': 'form',
                #     'view_mode': 'form',
                #     'res_model': 'sale.advance.payment.inv',
                #     'type': 'ir.actions.act_window',
                #     'context': {'delivery_sale_obj': self.sale_obj.id},
                #     'target': 'new'
                # }
            else:
                raise ValidationError(
                    _('Collect Amount first'))
        else:
            self.change_state('Delivered')
            if self.sale_obj.state in ['draft', 'sent']:
                self.sale_obj.action_confirm()
            self.invoice_status = self.sale_obj.invoice_status

    @api.multi
    def cancel(self):
        self.change_state('Canceled')

    @api.multi
    @api.depends('charges')
    def get_total(self):
        total = 0
        for obj in self:
            for each in obj.charges:
                total += each.sub_total
            obj.total_amount = total

    @api.onchange('service_id')
    def _onchange_service(self):
        for rec in self:
            lines = [(5, 0, 0)]
            for line in self.service_id.product_variant_ids:
                val = {
                    'product_id': line.id,
                    'quantity': 1
                }
                lines.append((0, 0, val))
            rec.charges = lines

    @api.constrains('amount')
    def check_amount(self):
        for rec in self:
            if rec.is_payment_on_delivery:
                if rec.amount <= 1:
                    raise ValidationError(
                        _('Amount to collect has to be greater than Zero'))

    @api.model
    def create(self, vals):
        if vals.get('order_no', _('New')) == _('New'):
            vals['order_no'] = self.env['ir.sequence'].next_by_code('increment_orderno') or _('New')
        result = super(DeliveryOrder, self).create(vals)
        return result

    # @api.multi
    # def write(self, vals):
    #     if vals.get('state'):
    #         if vals.get('state') == 'Delivered':
    #             record = self.env['account.invoice']
    #             invoice_line = {
    #                 'product_id': self.charges.product_id.id,
    #                 'invoice_id': self.invoice.id,
    #                 'name': 'delivery charge',
    #                 'price_unit': self.charges.product_id.list_price,
    #                 'account_id': self.client_id.property_account_receivable_id.id,
    #             }
    #             invoice = {
    #                 'partner_id': self.client_id.id,
    #                 'date_invoice': self.date,
    #                 'type': 'out_invoice',
    #                 'state': 'draft',
    #                 'invoice_line_ids': [(0, 0, invoice_line)],
    #             }
    #             record.create(invoice)
    #             record.action_invoice_open()
    #             return super(DeliveryOrder, self).write(vals)
    #         else:
    #             return super(DeliveryOrder, self).write(vals)
    #     else:
    #         return super(DeliveryOrder, self).write(vals)
    #


class Collections(models.Model):
    _name = 'amount.collection'
    _rec_name = 'collection_no'
    _description = 'Amount collected on delivery'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    collection_no = fields.Char(string="Collection Number", required=False,
                                default=lambda self: _('New'),
                                requires=False, readonly=True, )
    amount = fields.Float(string="Amount Collected", required=False, )
    delivery_order_id = fields.Many2one(comodel_name="delivery.order", string="Delivery Order", required=False, )
    date = fields.Date(string="Date", required=False, default=fields.Date.today())
    mode = fields.Selection(string="Mode of collection", selection=[('pos', 'POS'), ('cash', 'Cash'), ],
                            required=False, )
    client = fields.Char(string="Client", related="delivery_order_id.client_id.name", required=False, readonly=True, )
    client_id = fields.Many2one(comodel_name="res.partner", )
    invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('to invoice', 'Waiting Bills'),
        ('invoiced', 'No Bill to Receive'),
    ], string='Billing Status', readonly=True, copy=False, default='no')

    amount_collect = fields.Float(string="Amount to collect", related="delivery_order_id.amount")
    state = fields.Selection(string="", selection=[('draft', 'Draft'), ('collect', 'Collected'),
                                                   ('confirm', 'Confirmed'), ('post', 'Posted'),
                                                   ('finalise', 'Finalised'), ],
                             default="draft", required=False, track_visibility="onchange")
    purchase_obj = fields.Many2one('purchase.order', invisible=1)

    @api.multi
    def is_allowed_transition(self, old_state, new_state):
        allowed = [('draft', 'collect'),
                   ('collect', 'confirm'),
                   ('confirm', 'post'),
                   ('post', 'finalise'), ]
        return (old_state, new_state) in allowed

    @api.multi
    def change_state(self, new_state):
        for collect in self:
            if collect.is_allowed_transition(collect.state, new_state):
                collect.state = new_state
            else:
                msg = _('Moving from %s to %s is not allowed') % (collect.state, new_state)
                raise UserError(msg)

    @api.multi
    def collect(self):
        self.change_state('collect')

    @api.multi
    def confirm(self):
        self.change_state('confirm')
        purchase_obj = self.env['purchase.order'].create({'partner_id': self.client_id.id,
                                                          'collection_id': self.id})
        self.purchase_obj = purchase_obj
        self.env['purchase.order.line'].create({'name': 'collection',
                                                'product_id': 2,
                                                'price_unit': self.amount,
                                                'product_qty': 1,
                                                'qty_received': 1,
                                                'order_id': purchase_obj.id,
                                                'product_uom': 1,
                                                'date_planned': time.strftime('%Y-%m-%d'),
                                                })

    @api.multi
    def post(self):
        self.change_state('post')
        if self.purchase_obj.state in ['draft', 'sent']:
            self.purchase_obj.button_confirm()
        self.invoice_status = self.purchase_obj.invoice_status

    @api.multi
    def bill(self):
        self.purchase_obj.create_invoice()
        self.change_state('finalise')

    _sql_constraints = [
        ('collection_unique', 'unique(delivery_order_id)', 'Collection already entered for this delivery')
    ]

    @api.model
    def create(self, vals):
        if vals.get('collection_no', _('New')) == _('New'):
            vals['collection_no'] = self.env['ir.sequence'].next_by_code('increment_collection') or _('New')
        result = super(Collections, self).create(vals)
        return result


class ThirdParty(models.Model):
    _name = 'thirdparty.delivery'
    _description = 'collection of bulk packages via third party'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection(string="", selection=[('draft', 'draft'), ('packaged', 'Packaged'), ('sent', 'Sent'),
                                                   ('received', 'Received')], required=False, default='draft')
    delivery_ids = fields.Many2many(comodel_name="delivery.order", string="Packages",
                                    required=False, )
    origin = fields.Many2one(comodel_name="location.delivery", string="Originating Location")
    destination = fields.Many2one(comodel_name="location.delivery", string="Destination")
    courier_id = fields.Many2one(comodel_name="thirdparty.courier", string="Third Party Courier", required=False, )
    waybill_no = fields.Char(string="Waybill No.")
    sent_by = fields.Many2one(comodel_name="res.users", string="Sent By")
    received_by = fields.Many2one(comodel_name="res.users", string="Received By")


class ThirdCourier(models.Model):
    _name = 'thirdparty.courier'
    _rec_name = 'name'
    _description = 'Third party couriers'

    name = fields.Char()


class Locations(models.Model):
    _name = 'location.delivery'
    _rec_name = 'name'
    _description = 'Locations'

    name = fields.Char()


class DeliveryCharges(models.Model):
    _name = 'delivery.charges'
    _rec_name = 'name'
    _description = 'Charges'

    name = fields.Char()
    product_id = fields.Many2one(comodel_name="product.product")
    quantity = fields.Float(string="Quantity")
    order_id = fields.Many2one(comodel_name="delivery.order", string="order", required=False, )
    unit_cost = fields.Float(string="Unit Cost", related="product_id.lst_price")
    sub_total = fields.Float(string="Total", compute="_get_total")

    @api.one
    @api.depends('unit_cost', 'quantity', )
    def _get_total(self):
        self.sub_total = self.unit_cost * self.quantity


class DeliveryManagementInvoice(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.multi
    def create_invoices(self):
        context = self._context
        if context.get('delivery_sale_obj'):
            sale_orders = self.env['sale.order'].browse(context.get('delivery_sale_obj'))
        else:
            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        if self.advance_payment_method == 'delivered':
            sale_orders.action_invoice_create()
        elif self.advance_payment_method == 'all':
            sale_orders.action_invoice_create(final=True)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env['product.product'].create(vals)
                self.env['ir.values'].sudo().set_default('sale.config.settings', 'deposit_product_id_setting',
                                                         self.product_id.id)

            sale_line_obj = self.env['sale.order.line']
            for order in sale_orders:
                if self.advance_payment_method == 'percentage':
                    amount = order.amount_untaxed * self.amount / 100
                else:
                    amount = self.amount
                if self.product_id.invoice_policy != 'order':
                    raise UserError(_(
                        'The product used to invoice a down payment should have an invoice policy set to "Ordered'
                        ' quantities". Please update your deposit product to be able to create a deposit invoice.'))
                if self.product_id.type != 'service':
                    raise UserError(_(
                        "The product used to invoice a down payment should be of type 'Service'. Please use another "
                        "product or update this product."))
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id)
                if order.fiscal_position_id and taxes:
                    tax_ids = order.fiscal_position_id.map_tax(taxes).ids
                else:
                    tax_ids = taxes.ids
                so_line = sale_line_obj.create({
                    'name': _('Advance: %s') % (time.strftime('%m %Y'),),
                    'price_unit': amount,
                    'product_uom_qty': 0.0,
                    'order_id': order.id,
                    'discount': 0.0,
                    'product_uom': self.product_id.uom_id.id,
                    'product_id': self.product_id.id,
                    'tax_id': [(6, 0, tax_ids)],
                })
                self._create_invoice(order, so_line, amount)
        if self._context.get('open_invoices', False):
            return sale_orders.action_view_invoice()
        return {'type': 'ir.actions.act_window_close'}


class SaleInherit(models.Model):
    _inherit = 'sale.order'

    delivery_id = fields.Many2one(comodel_name="delivery.order", string="Delivery Order", required=False, )


class PurchaseInherit(models.Model):
    _inherit = 'purchase.order'

    collection_id = fields.Many2one(comodel_name="amount.collection", string="Collection Reference", required=False, )

    @api.multi
    def create_invoice(self):
        invoice = self.env['account.invoice'].create({
            'type': 'in_invoice',
            'purchase_id': self.id,
            'partner_id': self.partner_id.id,
        })
        invoice.purchase_order_change()
        # journal = self.env['account.invoice']._default_journal().id
        # line = self.order_line
        # inv_line_vals = {
        #             'price_unit': line.price_unit,
        #             'quantity': 1,
        #             'product_id': line.product_id.id,
        #             'name': 'collection',
        #             'account_id': journal,
        #         }
        #
        # inv_data = {
        #             'type': 'in_invoice',
        #             'name': self.partner_id.name,
        #             'reference': self.name,
        #             'journal_id': 1,
        #             'fiscal_position_id': self.partner_id.property_account_position_id.id,
        #             'account_id': self.partner_id.property_account_payable_id.id,
        #             'partner_id': self.partner_id.id,
        #             'origin': self.name,
        #             'invoice_line_ids': [(0, 0, inv_line_vals)],
        #         }
        # record = self.env['account.invoice'].create(inv_data)
        # return record


class PickupLocation(models.Model):
    _name = 'pickup.location'
    _rec_name = 'name'
    _description = 'Pickup Locations'

    name = fields.Char(string="Name")
    full_address = fields.Text(string="Full Address", required=False, )
    client_id = fields.Many2one(comodel_name="res.partner", string="Client")


class Clients(models.Model):
    _inherit = 'res.partner'

    pickup_locations_ids = fields.One2many(comodel_name="pickup.location", inverse_name="client_id",
                                           string="Pickup Locations", required=False, )
    supplier = fields.Boolean(string="is a vendor", default=True)


class States(models.Model):
    _name = 'states.nigeria'
    _rec_name = 'name'
    _description = 'States in Nigeria'

    name = fields.Char()


class LocalGovernments(models.Model):
    _name = 'local.governments'
    _rec_name = 'name'
    _description = 'Local governments in Nigeria'

    name = fields.Char()
    state = fields.Many2one(comodel_name='states.nigeria', string='State')

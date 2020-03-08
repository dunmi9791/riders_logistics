from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class CollectAmount(models.TransientModel):
    _name = 'collect.amount'
    _description = 'Collect Amount Wizard'

    amount = fields.Float(string="Amount Collected")
    delivery_order_id = fields.Many2one(comodel_name="delivery.order", string="Delivery Order",
                                        required=False, readonly=True, )
    mode = fields.Selection(string="Mode of collection", selection=[('pos', 'POS'), ('cash', 'Cash'), ],
                            required=True, )
    client = fields.Char(string="Client", related="delivery_order_id.client_id.name", required=False, readonly=True, )
    amount_collect = fields.Float(string="Amount to collect", related="delivery_order_id.amount")

    @api.constrains('amount')
    def check_amount(self):
        for rec in self:
            if rec.amount != rec.amount_collect:
                raise ValidationError(
                    _('Amount collected is not correct'))

    def collect_amount(self):
        collection = self.env['amount.collection']
        vals = {
            'amount': self.amount,
            'delivery_order_id': self.delivery_order_id.id,
            'mode': self.mode,
            'state': 'collect'
        }
        collection.create(vals)
        self.delivery_order_id.collected = True


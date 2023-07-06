# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('midtrans', 'Midtrans')], ondelete={'midtrans': 'set default'})
    midtrans_merchant_id = fields.Char('Midtrans Merchant ID',
            required_if_provider='midtrans', groups='base.group_user')
    midtrans_client_key = fields.Char('Midtrans Client Key',
            required_if_provider='midtrans', groups='base.group_user')
    midtrans_server_key = fields.Char('Midtrans Server Key',
            required_if_provider='midtrans', groups='base.group_user')

    @api.model
    def _get_midtrans_urls(self, environment):
        if environment == 'prod':
            return 'https://app.midtrans.com/snap/v1/transactions'
        return 'https://app.sandbox.midtrans.com/snap/v1/transactions'

    def _get_midtrans_tx_values(self, values):
        values['client_key'] = self.midtrans_client_key
        values['order'] = request.website.sale_get_order()
        amount = values['amount']
        currency = values['currency']
        currency_IDR = self.env['res.currency'].search([('name', '=','IDR')], limit=1)
        assert currency_IDR.name == 'IDR'
        if currency.id != currency_IDR.id:
            values['amount'] = int(round(currency.compute(amount,
                    currency_IDR)))

            values['currency'] = currency_IDR
            values['currency_id'] = currency_IDR.id
        else:
            values['amount'] = int(round(amount))
        return values

    def midtrans_form_generate_values(self, values):
        values.update(self._get_midtrans_tx_values(values))
        return values

    def midtrans_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_midtrans_urls(environment)
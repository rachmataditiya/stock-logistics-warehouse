# -*- coding: utf-8 -*-

import logging
import requests
import pprint
import re
import base64

from odoo import _, api, fields, models
from odoo.addons.payment_midtrans.const import SUPPORTED_CURRENCIES
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('midtrans', "Midtrans")], ondelete={'midtrans': 'set default'})
    midtrans_merchant_id = fields.Char(string='Merchant Id', required_if_provider='midtrans')
    midtrans_client_key = fields.Char(string='Client Key', required_if_provider='midtrans')
    midtrans_server_key = fields.Char(string='Server Key', required_if_provider='midtrans')

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        """ Override of `payment` to filter out Upayments providers for unsupported currencies. """
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name not in SUPPORTED_CURRENCIES:
            providers = providers.filtered(lambda p: p.code != 'midtrans')
        return providers
    def _midtrans_make_request(self, payload=None, method='POST'):
        """ Make a request to Upayments API at the specified endpoint.

        Note: self.ensure_one()

        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        if self.state == "enabled":
            url = "https://app.midtrans.com/snap/v1/transactions"
        else:
            url = "https://app.sandbox.midtrans.com/snap/v1/transactions"
        auth_string = self.midtrans_server_key + ":"
        encoded_auth_string = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        headers = {
            'Content-type': 'application/json',
            'Authorization': 'Basic ' + encoded_auth_string,
            'Accept': 'application/json',
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s", url, pprint.pformat(payload),
                )
                raise ValidationError("Midtrans: " + _(
                    "The communication with the API failed. Midtrans gave us the following "
                    "information: '%s'", response.json()
                ))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Upayments: " + _("Could not establish the connection to the API.")
            )
        response = response.json()
        if 'status' in response and response.get('status') == 'errors':
            if response.get('error_msg') and response.get('error_code'):
                raise ValidationError("Midtrans: " + _(response.get('error_msg')))
            else:
                raise UserError(
                    _("We had troubles reaching Midtrans, please retry later "
                      "or contact the support if the problem persists"))
        token = response.get('token')
        redirect_url = response.get('redirect_url')
        values = {
            'token': token,
            'redirect_url': redirect_url,
        }
        return values

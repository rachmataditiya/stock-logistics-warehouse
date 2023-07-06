# -*- coding: utf-8 -*-

import logging

from werkzeug import urls
from odoo import _, models, fields
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment_midtrans.controllers.main import MidtransController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    midtrans_payment_ref = fields.Char(string='Midtrans Reference')
    midtrans_payment_id = fields.Char(string='Midtrans ID')
    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Upayments-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'midtrans':
            return res

        # Initiate the payment and retrieve the payment link data.
        base_url = self.provider_id.get_base_url()
        name_parts = self.partner_name.split()
        payload = {
            'transaction_details': {
                'order_id': self.reference,
                'gross_amount': self.amount,
            },
            'customer_details': {
                'first_name': ' '.join(name_parts[:-1]) if len(name_parts) >= 2 else self.partner_name,
                'last_name': name_parts[-1] if len(name_parts) >= 2 else self.partner_name,
                'email': self.partner_email,
                'phone': self.partner_phone,

                'billing_address': {
                    'first_name': ' '.join(name_parts[:-1]) if len(name_parts) >= 2 else self.partner_name,
                    'last_name': name_parts[-1] if len(name_parts) >= 2 else self.partner_name,
                    'email': self.partner_email,
                    'phone': self.partner_phone,
                    'address': self.partner_address,
                    'country_code': self.partner_country_id.code_alpha3,
                    'postal_code': self.partner_zip,
                    'city': self.partner_city,
                },
            },
        }

        payment_link_data = self.provider_id._midtrans_make_request(payload=payload)

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values = {
            'token': payment_link_data['token'],
            'redirect_url': payment_link_data['redirect_url']
        }

        return rendering_values
    
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Midtrans data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'midtrans' or len(tx) == 1:
            return tx

        reference = notification_data['order_id']
        if not reference:
            raise ValidationError("Midtrans: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'midtrans')])
        if not tx:
            raise ValidationError(
                "Midtrans: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'midtrans':
            return

        vals = {
            'provider_reference': notification_data['order_id'] if notification_data['order_id'] else '',
            'midtrans_payment_ref': notification_data['merchant_id'] if notification_data['merchant_id'] else '',
            'midtrans_payment_id': notification_data['transaction_id'] if notification_data['transaction_id'] else '',
        }

        status = notification_data['transaction_status']
        if not status:
            raise ValidationError("Midtrans: " + _("Received data with missing payment state."))

        self.write(vals)
        if status in ['capture', 'settlement']:
            self._set_done()
        elif status == 'cancel':
            self._set_canceled()
        elif status =='pending':
            self._set_pending()
        elif status in ['deny', 'expire']:
            self._set_error("Midtrans: " + _(
                "Received transaction status %(status)s.",
                status=status
            ))
        else:
            _logger.info(
                "Received data with invalid payment status (%(status)s) "
                "for transaction with reference %(ref)s",
                {'status': status, 'ref': self.reference},
            )
            self._set_error("Midtrans: " + _(
                "Received invalid transaction status %(status)s.",
                status=status
            ))

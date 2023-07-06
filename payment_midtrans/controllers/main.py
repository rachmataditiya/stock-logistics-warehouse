# -*- coding: utf-8 -*-

import logging
import pprint
import midtransclient
import json

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MidtransController(http.Controller):
    _notification_url = '/payment/midtrans/notification'

    @http.route(['/payment/midtrans/notification'],
                type='json', auth='public', methods=['POST'], csrf=False)
    def midtrans_return_from_checkout(self, **raw_data):
        """ Process the notification data sent by Midtrans after redirection.
        :param dict raw_data: The notification data.
        """
        _logger.info("Handling redirection from Midtrans with data:\n%s", pprint.pformat(request.httprequest.data))
        try:
            body = json.loads(request.httprequest.data)
            provider = request.env['payment.provider'].sudo().search([('code', '=', 'midtrans')], limit=1)
            api_client = midtransclient.CoreApi(
                is_production=False if provider.state == 'test' else True,
                server_key=provider.midtrans_server_key,
                client_key=provider.midtrans_client_key
            )
            status_response = api_client.transactions.notification(body)
            signature_key_received = body.get('signature_key')
            signature_key_midtrans = status_response['signature_key']
            if signature_key_received !=  signature_key_midtrans:
                raise ValidationError('sign error.')
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'midtrans', status_response
            )
            # Handle the notification data.
            tx_sudo._handle_notification_data('midtrans', body)

        except ValidationError:  # Acknowledge the notification to avoid getting spammed.
            _logger.exception("Unable to handle the notification data; skipping to acknowledge.")

        return request.redirect('/payment/status')

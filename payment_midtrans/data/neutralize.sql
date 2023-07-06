-- disable flutterwave payment provider
UPDATE payment_provider
   SET midtrans_merchant_id = NULL,
       midtrans_client_key = NULL,
       midtrans_server_key = NULL;

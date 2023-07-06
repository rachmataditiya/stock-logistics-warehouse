odoo.define('payment.provider.midtrans', function(require)
{
    "use strict";
    var session = require('web.session');
    var scriptTag = document.createElement('script');

    $(document).ready(function(){
        session.rpc('/midtrans/get_environtment').then(function(response){
            if(response.production == "1"){
                var js = "https://app.midtrans.com/snap/snap.js";
            }else{
                var js = "https://app.sandbox.midtrans.com/snap/snap.js";
            }
            scriptTag.src = js;
            scriptTag.setAttribute('data-client-key', response.client_key);
            document.body.appendChild(scriptTag);       
        });
    });

    function set_state_busy(is_busy)
    {
        if (is_busy)
        {
            $.blockUI();
        }
        else
        {
            if ($.blockUI) {
                $.unblockUI();
            }
        }
    }

    function get_form_data($el)
    {
        return $el.serializeArray().reduce(
                function(m,e){m[e.name] = e.value; return m;}, {});
    }

    function attach_event_listener(selector,e)
    {
        var $btn = $(selector),
            $form = $btn.parents('form'),
            $provider = $btn.closest('div.oe_sale_provider_button,div.oe_quote_provider_button,div.o_website_payment_new_payment'),
            provider_id = $("#provider_midtrans").val() || $provider.data('id') || $provider.data('provider_id');

        var access_token = $("input[name='access_token']").val() || $("input[name='token']").val();

        if (!provider_id)
        {
            alert('payment_midtrans got invalid provider_id');
            return;
        }

        set_state_busy(true);
            
        var promise, formData = get_form_data($form);
        formData['provider_id'] = provider_id;
        promise = session.rpc('/midtrans/get_token',formData)
            .then(function(response)
            {
                if (response.snap_errors)
                {
                    alert(response.snap_errors.join('\n'));
                    set_state_busy(false);
                    return;
                }
    
                scriptTag.setAttribute('data-client-key', response.client_key);
                set_state_busy(false);
                snap.pay(response.snap_token,
                    {
                        onSuccess: function(result)
                        {
                            session.rpc('/midtrans/validate', {
                                reference: result.order_id,
                                transaction_status: 'done',
                                message: result.status_message,
        
                            }).then(function()
                            {
                                window.location = response.return_url;
                            });
                        },
                        onPending: function(result)
                        {
                            session.rpc('/midtrans/validate', {
                                reference: result.order_id,
                                transaction_status: 'pending',
                                message: result.status_message,
        
                            }).then(function()
                            {
                                window.location = response.return_url;
                            });
                        },
                        onError: function(result)
                        {
                            session.rpc('/midtrans/validate', {
                                reference: result.order_id,
                                transaction_status: 'error',
                                message: result.status_message,
        
                            }).then(function()
                            {
                                window.location = response.return_url;
                            });
                        },
                        onClose: function()
                        {
                            set_state_busy(false);
                        },
                    });
            },
            function(error)
            {
                set_state_busy(false);
                console.log(error);
            });
    }

    odoo.payment_midtrans = {
        attach: attach_event_listener,
    };
});

# -*- coding: utf-8 -*-

{
    'name': 'Midtrans Payment Provider',
    'category': 'Accounting',
    'summary': 'Payment Provider: Midtrans',
    'version': '1.0',
    'license': 'OPL-1',
    'description': """
        Midtrans payment gateway.
    """,
    'depends': ['payment','base_iso3166'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_midtrans_templates.xml',
        'data/payment_provider_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'images': ['static/description/main.png'],
    'author': 'Arkana Solusi Digital',
    'website': 'https://www.arkana.co.id',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}

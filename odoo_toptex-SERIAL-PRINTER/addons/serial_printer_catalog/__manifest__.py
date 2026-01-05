# -*- coding: utf-8 -*-
{
    'name': "Serial Printer Catalog",
    'version': '19.0.1.0.0',
    'summary': "Sync products from TopTex API into Odoo",
    'description': "Automated product sync from TopTex API. Custom module for Serial Printer Canarias.",
    'author': "Serial Printer Canarias",
    'category': 'Sales',
    'depends': ['base'],
    'data': [
        'data/cron_product.xml',
    ],
    'installable': True,
    'application': False,
}

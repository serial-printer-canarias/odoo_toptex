# addons/serial_printer_web_custom/__manifest__.py
{
    'name': 'Serial Printer Web Custom',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Grid de cantidades por color/talla en la ficha de producto',
    'license': 'LGPL-3',
    'depends': ['website_sale', 'website_sale_stock'],
    'data': [],
    'assets': {
        'web.assets_frontend': [
            'serial_printer_web_custom/static/src/js/product_matrix.js',
            'serial_printer_web_custom/static/src/scss/product_matrix.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
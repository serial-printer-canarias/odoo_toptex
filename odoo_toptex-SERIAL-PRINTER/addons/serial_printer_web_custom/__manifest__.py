{
    'name': 'Serial Printer Web Custom',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'depends': ['website_sale'],
    'assets': {
        'web.assets_frontend': [
            'serial_printer_web_custom/static/src/js/product_matrix.js',
            # opcional si tienes estilos:
            # 'serial_printer_web_custom/static/src/scss/product_matrix.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
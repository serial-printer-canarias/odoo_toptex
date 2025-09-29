{
    'name': 'Serial Printer - Custom Wizard',
    'version': '18.0.1.0.0',
    'summary': 'Personalización de producto con vista previa en carrito',
    'license': 'LGPL-3',
    'category': 'Website/Website',
    'depends': ['website_sale'],
    'data': [
        'views/customizer_page.xml',
        'views/product_personalize_button.xml',
        'views/spw_cart_preview_inject.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Colores / estilos
            'serial_printer_custom_wizard/static/src/css/spw_colors.css',
            'serial_printer_custom_wizard/static/src/css/customizer.css',
            'serial_printer_custom_wizard/static/src/css/personalizar_preview.css',

            # Botón y opciones en PDP
            'serial_printer_custom_wizard/static/src/js/spw_button.js',
            'serial_printer_custom_wizard/static/src/js/spw_options.js',

            # Lógica customizer (si la usas además del inline)
            'serial_printer_custom_wizard/static/src/js/spw_customizer.js',
            'serial_printer_custom_wizard/static/src/js/spw_custom_submit.js',
            

            # Inyección preview carrito/checkout
            'serial_printer_custom_wizard/static/src/js/spw_cart_preview.inject.js',
        ],
    },
    'installable': True,
    'application': False,
}
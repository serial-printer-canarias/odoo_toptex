{
    'name': 'Serial Printer Custom Wizard',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Botón "Personalizar" en la ficha + formulario de personalización',
    'description': 'Añade un botón Personalizar en la ficha de producto y página /personalizacion/<id>.',
    'author': 'Serial Printer Fuerteventura',
    'website': 'https://serial-printer.com',
    'license': 'LGPL-3',
    'depends': ['website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/personalizacion_wizard_views.xml',
        'views/personalizacion_form.xml',
        'report/mockup_personalizacion_template.xml',
        'views/website_customize_template.xml',
        # ⚠️ NO CARGAR ninguna view llamada website_customize_button.xml
    ],
    'assets': {
        'web.assets_frontend': [
            'serial_printer_custom_wizard/static/src/js/add_customize_button.js',
            # si quieres estilos: 'serial_printer_custom_wizard/static/src/css/customize.css',
        ],
    },
    'installable': True,
    'application': False,
}
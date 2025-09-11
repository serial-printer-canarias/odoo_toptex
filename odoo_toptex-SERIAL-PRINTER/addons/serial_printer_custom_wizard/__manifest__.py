# addons/serial_printer_custom_wizard/__manifest__.py
{
    "name": "Serial Printer – Custom Wizard",
    "summary": "Personalización de productos en eCommerce",
    "version": "18.0.1.0.0",
    "category": "Website/Commerce",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website", "website_sale"],
    "data": [
        "views/customizer_page.xml",
        "views/personalizacion_form.xml",
        "views/personalizacion_wizard_views.xml",
        "views/personalizacion_wizard_website_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
            "serial_printer_custom_wizard/static/src/js/customizer_preview.js",
            "serial_printer_custom_wizard/static/src/css/spw.css",
            # --- NUEVO: controles extra y estilos de paleta ---
            "serial_printer_custom_wizard/static/src/js/customizer_enhancements.js",
            "serial_printer_custom_wizard/static/src/css/spw_colors.css",
        ],
    },
    "installable": True,
    "application": False,
}
{
    "name": "Serial Printer — Custom Wizard",
    "summary": "Personalización de productos en eCommerce",
    "version": "18.0.1.0.0",
    "category": "Website/Commerce",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website", "website_sale", "product"],
    "data": [
        "views/customizer_page.xml",
        "views/personalizacion_form.xml",
        "views/personalizacion_wizard_views.xml",
        "views/product_personalize_button.xml",  # botón en la ficha
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/css/spw.css",
            "serial_printer_custom_wizard/static/src/js/personalize_btn.js",
        ],
    },
    "installable": True,
    "application": False,
}
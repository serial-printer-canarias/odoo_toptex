# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard (minimal)",
    "summary": "Botón Personalizar en la ficha y página de destino",
    "version": "17.0.1.0.0",
    "category": "Website/Website",
    "license": "LGPL-3",
    "author": "SPW",
    "depends": ["website", "website_sale"],
    # Cargamos SOLO lo necesario para que no fallen tests
    "data": [
        "views/personalizacion_wizard_website_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # nuestro JS (ruta exacta con /)
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
    },
    "installable": True,
    "application": False,
}
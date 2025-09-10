# -*- coding: utf-8 -*-
{
    "name": "Serial Printer - Custom Wizard (minimal)",
    "summary": "Botón Personalizar en la ficha y página de destino",
    "version": "17.0.1.0.1",  # <— súbelo para forzar upgrade
    "category": "Website/Website",
    "license": "LGPL-3",
    "author": "SPW",
    "depends": ["website", "website_sale"],
    "data": [
        "views/personalizacion_wizard_website_views.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_custom_wizard/static/src/js/add_customize_button.js",
        ],
    },
    "installable": True,
    "application": False,
}
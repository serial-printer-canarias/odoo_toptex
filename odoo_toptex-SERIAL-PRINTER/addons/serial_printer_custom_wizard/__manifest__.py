# -*- coding: utf-8 -*-
{
    "name": "Serial Printer · Custom Wizard",
    "summary": "Botón «Personalizar» en la ficha de producto + página de personalización.",
    "version": "17.0.1.0.0",
    "category": "Website",
    "author": "Serial Printer",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/personalizacion_form.xml",
        "views/personalizacion_wizard_views.xml",
        "views/personalizacion_wizard_website_views.xml",
        "views/assets.xml",                     # deja los assets aquí si prefieres no usar la clave assets del manifest
        # NO añadas aquí ningún otro xml para el botón: lo ponemos con JS para evitar xpaths frágiles.
    ],
    "installable": True,
    "application": False,
}
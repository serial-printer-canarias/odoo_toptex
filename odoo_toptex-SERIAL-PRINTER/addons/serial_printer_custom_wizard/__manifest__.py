# -*- coding: utf-8 -*-
{
    "name": "Serial Printer – Custom Wizard (mínimo estable)",
    "version": "16.0.1.0.0",
    "summary": "Botón 'Personalizar' en la ficha + página dummy",
    "category": "Website/Website",
    "depends": ["website_sale"],
    "data": [
        # SOLO cargamos estos dos XML de tu carpeta views
        "views/assets.xml",
        "views/website_customize_template.xml",
    ],
    # No usamos assets aquí para evitar duplicados; van en views/assets.xml
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
{
    "name": "Serial Printer Catalog",
    "version": "1.0",
    "summary": "Integración completa con la API TopTex",
    "description": "Sincroniza productos, variantes, imágenes, tallas y stock desde la API de TopTex con Odoo.",
    "author": "Serial Printer",
    "category": "Sales",
    "website": "https://serialprinter.local",
    "depends": ["base", "product", "sale_management", "stock", "website_sale"],
    "data": [
        "views/brand_views.xml",
        "views/menu.xml",
        "data/cron.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3"
}
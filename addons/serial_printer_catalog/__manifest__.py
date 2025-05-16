{
    "name": "Serial Printer Catalog",
    "version": "1.0",
    "summary": "Integración completa con API TopTex: productos, variantes y stock",
    "description": "Sincroniza productos, variantes, imágenes y stock desde la API de TopTex con tu Odoo.",
    "author": "Serial Printer",
    "category": "Sales",
    "website": "https://serialprinter.local",
    "depends": [
        "base",
        "product",
        "stock",
        "sale_management",
        "website_sale"
    ],
    "data": [
        "views/brand_views.xml",
        "views/product_views.xml",
        "data/cron.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3"
}
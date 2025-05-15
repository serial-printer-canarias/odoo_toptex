
{
    "name": "Serial Printer Catalog",
    "version": "1.0",
    "summary": "Catálogo de productos y marcas importados por API",
    "description": "Importa productos, marcas, variantes y precios desde una API externa.",
    "author": "Serial Printer",
    "category": "Sales",
    "website": "https://www.serialprinter.com",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/brand_views.xml",
        "views/product_views.xml",
        "views/menu.xml"
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "LGPL-3"
}

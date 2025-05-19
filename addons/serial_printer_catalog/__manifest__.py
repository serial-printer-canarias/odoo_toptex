{
    "name": "Catálogo Serial Printer",
    "version": "1.0",
    "depends": ["base", "product"],
    "author": "Serial Printer",
    "category": "Sales",
    "description": "Sincronización automática con catálogo de productos TopTex",
    "data": [
        "views/menu_attribute.xml",
        "views/menu_variant.xml",

        "views/product_views.xml",
        "views/attribute_views.xml",
        "views/variant_views.xml",

        "data/cron.xml",
        "data/cron_attribute.xml",
        "data/cron_variant.xml",
    ],
    "installable": True,
    "application": True,
}
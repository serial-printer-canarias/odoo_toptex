{
    'name': 'Catálogo Serial Printer',
    'version': '1.0.0',
    'summary': 'Sincronización con la API de TopTex',
    'description': 'Importa productos, marcas, atributos, imágenes, precios y stock desde la API de TopTex',
    'category': 'Sales',
    'author': 'Serial Printer',
    'website': 'https://serialprinter.com',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'views/menu_root.xml',

        'views/menu_brands.xml',
        'views/brand_views.xml',

        'views/menu_attribute.xml',
        'views/attribute_views.xml',

        'views/menu_products.xml',
        'views/product_views.xml',

        'views/variant_views.xml',
        'views/image_views.xml',
        'views/prices_views.xml',
        'views/token_views.xml',

        'data/cron_token.xml',
        'data/cron_product.xml',
        'data/cron_brand.xml',
        'data/cron_attribute.xml',
        'data/cron_variant.xml',
        'data/cron_image.xml',
        'data/cron_prices.xml',
        'data/cron_stock.xml',
    ],
    'installable': True,
    'application': True,
}
{
    'name': 'Catálogo Serial Printer',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Catálogo automático desde API',
    'description': 'Importación automática de productos, marcas, variantes, precios e imágenes desde la API de TopTex',
    'author': 'Serial Printer',
    'depends': ['base', 'product'],
    'data': [
        'views/menu_root.xml',
        'views/menu_product.xml',
        'views/product_views.xml',

        'views/token_views.xml',

        'views/menu_brand.xml',
        'views/brand_views.xml',

        'views/menu_attribute.xml',
        'views/attribute_views.xml',

        'views/menu_variant.xml',
        'views/variant_views.xml',

        'views/menu_image.xml',
        'views/image_views.xml',

        'views/menu_prices.xml',
        'views/prices_views.xml',

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
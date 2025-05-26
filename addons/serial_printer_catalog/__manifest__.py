{
    'name': 'Catálogo Serial Printer',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Sincronización con API de TopTex',
    'description': 'Importación automática de productos, marcas, atributos, imágenes, variantes, precios y stock desde la API de TopTex.',
    'author': 'Serial Printer',
    'depends': ['base', 'sale', 'product'],
    'data': [
        # Menú raíz (siempre primero)
        'views/menu_root.xml',

        # TOKENS (orden correcto: menú → vistas → cron)
        'views/menu_token.xml',
        'views/token_views.xml',
        'data/cron_token.xml',

        # MARCAS
        'views/menu_brand.xml',
        'views/brand_views.xml',
        'data/cron_brand.xml',

        # PRODUCTOS
        'views/menu_product.xml',
        'views/product_views.xml',
        'data/cron_product.xml',

        # ATRIBUTOS
        'views/menu_attribute.xml',
        'views/attribute_views.xml',
        'data/cron_attribute.xml',

        # VARIANTES
        'views/menu_variant.xml',
        'views/variant_views.xml',
        'data/cron_variant.xml',

        # IMÁGENES
        'data/cron_image.xml',

        # PRECIOS
        'views/menu_prices.xml',
        'views/prices_views.xml',
        'data/cron_prices.xml',

        # STOCK
        'data/cron_stock.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
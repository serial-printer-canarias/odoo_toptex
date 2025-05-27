{
    'name': 'Catálogo Serial Printer',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Catálogo con productos sincronizados desde TopTex',
    'description': 'Módulo para importar productos de TopTex y mostrarlos en Odoo como catálogo',
    'author': 'Serial Printer',
    'depends': ['base', 'product'],
    'data': [
        'views/menu_root.xml',
        'views/menu_product.xml',
        'views/product_views.xml',
        'data/cron_product.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
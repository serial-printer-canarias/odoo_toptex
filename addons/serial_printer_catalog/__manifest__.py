{
    'name': 'Catálogo TopTex',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Importación de productos TopTex',
    'description': 'Crea productos desde la API de TopTex en el modelo estándar de Odoo',
    'author': 'Serial Printer',
    'license': 'LGPL-3',
    'depends': ['base', 'product'],
    'data': [
        'data/cron_product.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
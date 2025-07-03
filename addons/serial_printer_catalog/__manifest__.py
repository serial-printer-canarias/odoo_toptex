{
    'name': 'Catálogo TopTex',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Importación de productos TopTex',
    'description': 'Crea productos desde la API de TopTex',
    'author': 'Serial Printer',
    'license': 'LGPL-3',
    'depends': ['base', 'product'],
    'data': [
        'data/cron_product.xml',
        'ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
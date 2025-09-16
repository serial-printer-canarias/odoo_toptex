{
    "name": "Serial Printer Web Custom",
    "version": "18.0.1.0.0",
    "category": "Website/eCommerce",
    "summary": "Vista de producto + matriz color×talla",
    "author": "Serial Printer",
    "website": "https://serial-printer.com",
    "license": "LGPL-3",
    "depends": ["website_sale"],
    "data": [
        "views/product_template.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "serial_printer_web_custom/static/src/js/product_matrix.js"
        ]
    },
    "installable": True,
    "application": False,
    "auto_install": False
}
# -*- coding: utf-8 -*-
{
    "name": "Serial Printer Sale Personalization",
    "version": "18.0.1.4.0",
    "summary": "Fichas de personalización textil desde presupuestos y facturas",
    "author": "Serial Printer",
    "website": "https://www.serial-printer.com",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": ["base", "sale_management", "account", "website", "portal", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/personalization_views.xml",
        "views/sale_order_views.xml",
        "views/portal_templates.xml",
        "reports/personalization_report.xml",
        "reports/report_templates.xml",
    ],
    "installable": True,
    "application": True,
}

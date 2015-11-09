# -*- coding: utf-8 -*-

{
    'name': "MRP II",
    'version': '1.0',
    'category': "Manufacturing",
    'complexity': "normal",
    'description': """MRP II""",
    'author': 'BHECO SERVICES',
    'website': 'http://www.bhecoservices.com',
    'images': [],
    'depends': ["base","product","mrp","mrp_operations"],
    'init_xml': [],
    'update_xml': [
        'mrp2.xml',
        'mrp2_sequence.xml'
                ],
    'demo_xml': [],
    'test':[],
    'installable': True,
    'auto_install': False,
}
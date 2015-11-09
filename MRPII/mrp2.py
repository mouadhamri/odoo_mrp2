# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math

class product_product(osv.osv):
    
    _inherit = 'product.product'
    _name = "product.product"
    _columns= {
               'prevision': fields.boolean(u'Gestion des prévisions'),
               'period_type':fields.selection([('daily', 'Quotidiennement'),('weekly', 'Hebdomadairement') , ('monthly', 'Mensuellement')],u'Type de période'),
               'lot': fields.float('Lot de fabrication'),
               'ferme_zone': fields.integer(u'Ferme zone'),
               }
    _defaults={
        'prevision': False,
            }    
product_product()


class sale_forecast(osv.osv):
    _name = "sale.forecast"

    _columns = {
            'name': fields.char(u"Numéro",size=128),    
            'product_id': fields.many2one('product.product', string=u'Produit', required=True),
            'date_start': fields.date(string=u'Date début', required=True),
            'date_stop': fields.date(string=u'Date fin', required=True),
            'state': fields.selection([('draft','Brouillon'), ('done','Validé'),('cancel','Annulé')], string=u'Etat'),
            'forecast_line_ids': fields.one2many('sale.forecast.line', 'sale_forecast_id', string=u'Lignes des prévisions'),
                }
    
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'sale_forecast'),         
        'state': 'draft'
                }

    
    def create_period(self, cr, uid, ids, context=None):
        forecast_line_obj = self.pool.get('sale.forecast.line')
        for forcast in self.browse(cr, uid, ids, context=context):
            cr.execute('delete from sale_forecast_line where sale_forecast_id='+str(forcast.id))
            ds = datetime.strptime(forcast.date_start, '%Y-%m-%d')
            dt_stp = datetime.strptime(forcast.date_stop, '%Y-%m-%d')
            
            while ds.strftime('%Y-%m-%d') < forcast.date_stop:
                
                if  forcast.product_id.period_type=='daily':
                    de = ds + relativedelta(days=1, seconds =-1)
                    date_stop = ds + relativedelta(days=1)
                    new_id = forecast_line_obj.create(cr, uid, {
                        'period': de.strftime('%d-%m-%Y'),
                        'product_qty':0.0,
                        'sale_forecast_id':forcast.id,
                        'date_start':de.strftime('%d-%m-%Y'),
                        'date_stop':date_stop.strftime('%d-%m-%Y')
                        })
                    ds = ds + relativedelta(days=1)
                    
                if  forcast.product_id.period_type=='weekly':
                    de = ds + relativedelta(days=1, seconds =-1)
                    date_stop = ds + relativedelta(days=7, seconds =-1)
                    #if dt_stp < de:
                    #   de = dt_stp + relativedelta(days=1, seconds =-1)
                    #else:
                    #    de = ds + relativedelta(days=1, seconds =-1)
                    #if de.strftime('%Y') == date_stop.strftime('%Y'):
                    new_name = de.strftime('Week %W-%Y')
                    #else:
                    #    new_name = ds.strftime('Semaine %W-%Y') + ', ' + date_stop.strftime('Semaine %W-%Y')
                    new_id = forecast_line_obj.create(cr, uid, {
                    'period': new_name,
                    'product_qty':0.0,
                    'sale_forecast_id':forcast.id,
                    'date_start':de.strftime('%d-%m-%Y'),
                    'date_stop':date_stop.strftime('%d-%m-%Y')
                    })
                    ds = ds + relativedelta(days=7)
                    
                if forcast.product_id.period_type=='monthly':
                    de = ds + relativedelta(months=1, seconds=-1)
                    if dt_stp < de:
                        de = dt_stp + relativedelta(days=1, seconds =-1)
                    else:
                        de = ds + relativedelta(months=1, seconds=-1)
                    new_name = ds.strftime('%m/%Y')
                    if ds.strftime('%m') != de.strftime('%m'):
                        new_name = ds.strftime('%m/%Y') + '-' + de.strftime('%m/%Y')
                    new_id = forecast_line_obj.create(cr, uid, {
                    'period': new_name,
                    'product_qty':0.0,
                    'sale_forecast_id':forcast.id,
                    'date_start':ds.strftime('%d-%m-%Y'),
                    'date_stop':de.strftime('%d-%m-%Y')
                    })
                    ds = ds + relativedelta(months=1)
        return True
    
    def _check_duration(self, cr, uid, ids, context=None):
        sale_forecast_obj = self.browse(cr, uid, ids[0], context=context)
        if sale_forecast_obj.date_stop < sale_forecast_obj.date_start:
            return False
        return True
    
    def button_valid(self, cr, uid, ids, context=None):
        pdp_obj = self.pool.get('pdp')
        pdp_line_obj = self.pool.get('pdp.line')
        forecast_line_obj = self.pool.get('sale.forecast.line')
        for forcast in self.browse(cr, uid, ids, context=context):
            pdp_old_id=pdp_obj.search(cr,uid,[('sale_forecast_id','=',forcast.id)])
            if pdp_old_id:
                raise osv.except_osv(('Attention!'),(u'PDP déjà crée, vous devez le supprimer'))
            pdp_id = pdp_obj.create(cr, uid, {
                        'sale_forecast_id':forcast.id,                      
                        'product_id':forcast.product_id.id,
                        'date_start':forcast.date_start,
                        'date_stop':forcast.date_stop                   
                                            })
            
            ds = datetime.strptime(forcast.date_start, '%Y-%m-%d')
            dt_stp = datetime.strptime(forcast.date_stop, '%Y-%m-%d')
            
            stock_initial=forcast.product_id.qty_available
            
            if  forcast.product_id.period_type=='daily':
                
                de1 = ds + relativedelta(days=1, seconds =-1)
                date_stop1 = ds + relativedelta(days=1)
                                
                for forcast_line in forcast.forecast_line_ids:
                    forcast_line_id=forecast_line_obj.search(cr, uid, [('date_start','=', de1),('date_stop','=',date_stop1)], context = context)
                forecast_qty1=forecast_line_obj.browse(cr, uid, forcast_line_id[0], context=context).product_qty
                stock_qty=stock_initial-forecast_qty1
                planned_order_qty=0
                if stock_qty <= 0 :                    
                    planned_order_qty= abs(stock_qty)
                    stock_qty=0
                pdp_line = pdp_line_obj.create(cr, uid, {
                    'period': de1.strftime('%d-%m-%Y'),
                    'forecast_qty':forecast_qty1,
                    'stock_qty':stock_qty,
                    'planned_order_qty':planned_order_qty,
                    'date_start':de1.strftime('%d-%m-%Y'),
                    'date_stop':date_stop1.strftime('%d-%m-%Y'),
                    'pdp_id':pdp_id
                    })
                               
                ds = ds + relativedelta(days=1)
                while ds.strftime('%Y-%m-%d') < forcast.date_stop:
                        de = ds + relativedelta(days=1, seconds =-1)
                        date_stop = ds + relativedelta(days=1)
                        for forcast_line in forcast.forecast_line_ids:
                            forcast_line_id=forecast_line_obj.search(cr, uid, [('date_start','=', de),('date_stop','=',date_stop)], context = context)
                        forecast_qty=forecast_line_obj.browse(cr, uid, forcast_line_id[0], context=context).product_qty
                        
                        dts=ds+relativedelta(days=-1)
                        pdp_line_id=pdp_line_obj.search(cr, uid, [('date_start','=',dts ),('date_stop','=',de)], context = context)
                        stock_qty_init=pdp_line_obj.browse(cr, uid, pdp_line_id[0], context=context).stock_qty
                        
                        
                        lot=forcast.product_id.lot
                        if stock_qty_init<forecast_qty:
                            stock_qty_abs=forecast_qty-stock_qty_init
                            factor=math.ceil(stock_qty_abs/lot)
                            planned_order_qty=factor*lot
                        else:
                            planned_order_qty=0.0
                            
                        stock_qty=stock_qty_init-forecast_qty+planned_order_qty
                        
                        pdp_line = pdp_line_obj.create(cr, uid, {
                            'period': de.strftime('%d-%m-%Y'),
                            'forecast_qty':forecast_qty,
                            'stock_qty':stock_qty,
                            'planned_order_qty':planned_order_qty,
                            'date_start':de.strftime('%d-%m-%Y'),
                            'date_stop':date_stop.strftime('%d-%m-%Y'),
                            'pdp_id':pdp_id
                            })
                        ds = ds + relativedelta(days=1)                    
            
            
            if  forcast.product_id.period_type=='weekly':

                de1 = ds + relativedelta(days=1, seconds =-1)
                date_stop1 = ds + relativedelta(days=7, seconds =-1)
                                
                for forcast_line in forcast.forecast_line_ids:
                    forcast_line_id=forecast_line_obj.search(cr, uid, [('date_start','=', de1),('date_stop','=',date_stop1)], context = context)
                forecast_qty1=forecast_line_obj.browse(cr, uid, forcast_line_id[0], context=context).product_qty
                stock_qty=stock_initial-forecast_qty1

                planned_order_qty=0
                if stock_qty <= 0 :                    
                    planned_order_qty= abs(stock_qty)
                    stock_qty=0
                                    
                new_name = de1.strftime('Week %W-%Y')
                pdp_line = pdp_line_obj.create(cr, uid, {
                    'period': new_name,
                    'forecast_qty':forecast_qty1,
                    'stock_qty':stock_qty,
                    'planned_order_qty':planned_order_qty,
                    'date_start':de1.strftime('%d-%m-%Y'),
                    'date_stop':date_stop1.strftime('%d-%m-%Y'),
                    'pdp_id':pdp_id
                    })
                
                ds = ds + relativedelta(days=7)
                
                while ds.strftime('%Y-%m-%d') < forcast.date_stop:
                        de = ds + relativedelta(days=1, seconds =-1)
                        date_stop = ds + relativedelta(days=7, seconds =-1)
                        dtstop = ds + relativedelta(days=-1)
                        for forcast_line in forcast.forecast_line_ids:
                            forcast_line_id=forecast_line_obj.search(cr, uid, [('date_start','=', de),('date_stop','=',date_stop)], context = context)
                        forecast_qty=forecast_line_obj.browse(cr, uid, forcast_line_id[0], context=context).product_qty
                        dts=ds+relativedelta(days=-7)
                        pdp_line_id=pdp_line_obj.search(cr, uid, [('date_start','=',dts ),('date_stop','=',dtstop)], context = context)
                        stock_qty_init=pdp_line_obj.browse(cr, uid, pdp_line_id[0], context=context).stock_qty
                             
                        lot=forcast.product_id.lot
                        if stock_qty_init<forecast_qty:
                            stock_qty_abs=forecast_qty-stock_qty_init
                            factor=math.ceil(stock_qty_abs/lot)
                            planned_order_qty=factor*lot
                        else:
                            planned_order_qty=0.0
                            
                        stock_qty=stock_qty_init-forecast_qty+planned_order_qty
                        
                        new_name = de.strftime('Week %W-%Y')
                        pdp_line = pdp_line_obj.create(cr, uid, {
                            'period':new_name ,
                            'forecast_qty':forecast_qty,
                            'stock_qty':stock_qty,
                            'planned_order_qty':planned_order_qty,
                            'date_start':de.strftime('%d-%m-%Y'),
                            'date_stop':date_stop.strftime('%d-%m-%Y'),
                            'pdp_id':pdp_id
                            })
                        ds = ds + relativedelta(days=7)          

            if forcast.product_id.period_type=='monthly':
                    de = ds + relativedelta(months=1, seconds=-1)
                    if dt_stp < de:
                        de = dt_stp + relativedelta(days=1, seconds =-1)
                    else:
                        de = ds + relativedelta(months=1, seconds=-1)

                    for forcast_line in forcast.forecast_line_ids:
                        forcast_line_id=forecast_line_obj.search(cr, uid, [('date_start','=', ds),('date_stop','=',de)], context = context)
                    forecast_qty1=forecast_line_obj.browse(cr, uid, forcast_line_id[0], context=context).product_qty
                    stock_qty=stock_initial-forecast_qty1
                    new_name = ds.strftime('%m/%Y')
                    if ds.strftime('%m') != de.strftime('%m'):
                        new_name = ds.strftime('%m/%Y') + '-' + de.strftime('%m/%Y')

                    planned_order_qty=0
                    if stock_qty <= 0 :
                        stock_qty=abs(stock_qty)
                        lot=forcast.product_id.lot
                        factor=math.ceil(float(stock_qty)/float(lot))
                        planned_order_qty=factor*lot
                        stock_qty=stock_initial-forecast_qty1+planned_order_qty
                                                                                                                                        
                    pdp_line = pdp_line_obj.create(cr, uid, {
                        'period': new_name,
                        'forecast_qty':forecast_qty1,
                        'stock_qty':stock_qty,
                        'planned_order_qty':planned_order_qty,
                        'date_start':ds.strftime('%d-%m-%Y'),
                        'date_stop':de.strftime('%d-%m-%Y'),
                        'pdp_id':pdp_id
                        })

                    ds = ds + relativedelta(months=1)

                    while ds.strftime('%Y-%m-%d') < forcast.date_stop:
                        de = ds + relativedelta(months=1, seconds=-1)
                        if dt_stp < de:
                            de = dt_stp + relativedelta(days=1, seconds =-1)
                        else:
                            de = ds + relativedelta(months=1, seconds=-1)
                        new_name = ds.strftime('%m/%Y')
                        if ds.strftime('%m') != de.strftime('%m'):
                            new_name = ds.strftime('%m/%Y') + '-' + de.strftime('%m/%Y') 
                        for forcast_line in forcast.forecast_line_ids:
                            forcast_line_id=forecast_line_obj.search(cr, uid, [('date_start','=', ds),('date_stop','=',de)], context = context)
                        forecast_qty=forecast_line_obj.browse(cr, uid, forcast_line_id[0], context=context).product_qty
                        
                        dts=ds + relativedelta(months=-1) 
                        dtstop= dts + relativedelta(months=1, seconds=-1)
                        pdp_line_id=pdp_line_obj.search(cr, uid, [('date_start','=',dts ),('date_stop','=',dtstop)], context = context)

                        stock_qty_init=pdp_line_obj.browse(cr, uid, pdp_line_id[0], context=context).stock_qty
                        
                        lot=forcast.product_id.lot
                        if stock_qty_init<forecast_qty:
                            stock_qty_abs=forecast_qty-stock_qty_init
                            factor=math.ceil(float(stock_qty_abs)/float(lot))
                            planned_order_qty=factor*lot
                        else:
                            planned_order_qty=0.0
                            
                        stock_qty=stock_qty_init-forecast_qty+planned_order_qty
                        
                        pdp_line = pdp_line_obj.create(cr, uid, {
                            'period':new_name ,
                            'forecast_qty':forecast_qty,
                            'stock_qty':stock_qty,
                            'planned_order_qty':planned_order_qty,
                            'date_start':ds.strftime('%d-%m-%Y'),
                            'date_stop':de.strftime('%d-%m-%Y'),
                            'pdp_id':pdp_id
                            })
          
                        ds = ds + relativedelta(months=1)
                
        self.write(cr, uid, ids, {'state': 'done'})
        return True
    
    def button_draft(self, cr, uid, ids, context=None):
        pdp_obj = self.pool.get('pdp')
        for forcast in self.browse(cr, uid, ids, context=context):
            pdp_old_id=pdp_obj.search(cr,uid,[('sale_forecast_id','=',forcast.id)])
            if pdp_old_id:
                cr.execute("""select id from planned_order where pdp_id=%s""",(pdp_old_id))
                results = cr.fetchall()
                list_po=[]
                for res in results:
                    cr.execute("""delete from ordre_travail where planned_order_id = %s""",(res))                 
                cr.execute("""delete from planned_order where pdp_id=%s""",(pdp_old_id)) 
                cr.execute("""delete from pdp where id=%s""",(pdp_old_id))                                       
        self.write(cr, uid, ids, {'state': 'draft'})
        return True
    
    def button_cancel(self, cr, uid, ids, context=None):
        pdp_obj = self.pool.get('pdp')
        for forcast in self.browse(cr, uid, ids, context=context):
            pdp_old_id=pdp_obj.search(cr,uid,[('sale_forecast_id','=',forcast.id)])
            if pdp_old_id:
                cr.execute("""select id from planned_order where pdp_id=%s""",(pdp_old_id))
                results = cr.fetchall()
                list_po=[]
                for res in results:
                    cr.execute("""delete from ordre_travail where planned_order_id = %s""",(res))                 
                cr.execute("""delete from planned_order where pdp_id=%s""",(pdp_old_id)) 
                cr.execute("""delete from pdp where id=%s""",(pdp_old_id))
                        
        self.write(cr, uid, ids, {'state': 'cancel'})
        return True

    _constraints = [
        (_check_duration, u'Erreur!\n La date de début doit précéder la date de fin ', ['date_start','date_stop'])
    ]
    
sale_forecast()

class sale_forecast_line(osv.osv):
    _name = "sale.forecast.line"

    _columns = {
            'period': fields.char(string=u'Nom de la période', size=64, required=True),
            'date_start': fields.date(string=u'Date début de période', required=True),
            'date_stop': fields.date(string=u'Date fin de période', required=True),
            'product_qty': fields.float(string=u'Quantité', required=True),
            'sale_forecast_id':fields.many2one('sale.forecast', string=u'Prévision', required=True, ondelete='cascade'),    
                }
sale_forecast_line()

class pdp(osv.osv):
    _name = "pdp"

    _columns = {
            'name': fields.char(u"Numéro",size=128),    
            'sale_forecast_id': fields.many2one('sale.forecast', string=u'Prévision des ventes', required=True),
            'product_id': fields.many2one('product.product', string=u'Produit', required=True),
            'stock_initial': fields.related('product_id', 'qty_available', type='float', string='Stock initial', readonly=True),
            'date_start': fields.date(string=u'Date début', required=True),
            'date_stop': fields.date(string=u'Date fin', required=True),
            'pdp_line_ids': fields.one2many('pdp.line', 'pdp_id', string=u'Lignes PDP'),
            'entrer': fields.boolean(u'entrer'),  
                }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'pdp'),
        'entrer':True
                }


    def get_bom(self,cr,uid,bom,factor):
        r_value = []
        bom_obj = self.pool.get('mrp.bom')
        res= bom_obj._bom_explode(cr,uid,bom,bom.product_id,bom.product_qty)
        for r in res[0]:    
            r_value.append({'product_id':r['product_id'],'product_qty':r['product_qty']*factor})
            
        for r in res[0]:
            newbom = bom_obj._bom_find(cr, uid, r['product_id'], r['product_uom'],False)
            n_bom= bom_obj.browse(cr,uid,newbom)
            if newbom:
                r_value.extend(self.get_bom(cr,uid,n_bom,r['product_qty']*factor))
        return r_value
        
    def create_planned_order(self, cr, uid, ids, context=None):

        
        planned_order_obj = self.pool.get('planned.order')
        bom_obj = self.pool.get('mrp.bom')
        for pdp in self.browse(cr, uid, ids, context=context):            
            pdp_id=[pdp.id]
            cr.execute('delete from ordre_travail where pdp_id='+str(pdp.id))
            cr.execute("""delete  from purchase_requisition_cbn where pdp_id=%s""",(pdp_id))
            cr.execute("""select id from planned_order where pdp_id=%s""",(pdp_id))
            
            results = cr.fetchall()
            list_po=[]
            for res in results:
                res=[res]
                cr.execute("""delete from ordre_travail where planned_order_id = %s""",(res))            
            cr.execute('delete from planned_order where pdp_id='+str(pdp.id))
            product_id=pdp.product_id.id
            bom_id=bom_obj.search(cr,uid,[('product_id','=',product_id)])
            if not bom_id:
                raise osv.except_osv(('Erreur!'),
                                     (u'Pas de nomenclature pour ce produit: "%s"') % (pdp.product_id.name)) 
            else:
                bom_id=bom_id[0]
                routing_id=bom_obj.browse(cr, uid, bom_id, context=context).routing_id.id
                if routing_id:
                    routing_id=routing_id     
            for pdp_line in pdp.pdp_line_ids:
                if pdp_line.planned_order_qty != 0:
                    planned_order_id=planned_order_obj.create(cr, uid, {
                            'product_id':product_id ,
                            'qty':pdp_line.planned_order_qty,
                            'date':pdp_line.date_start,
                            'bom_id':bom_id,
                            'routing_id':routing_id,
                            'pdp_id':pdp.id
                            })
                    planned_order_id=[planned_order_id] 
                    planned_order_obj.create_ordre_travail(cr, uid, planned_order_id, context=None)
                    
                    purchase_requisition_cbn_obj = self.pool.get('purchase.requisition.cbn')
                    bom = bom_obj.browse(cr,uid,bom_id)
                    res= self.get_bom(cr, uid, bom,pdp_line.planned_order_qty)                 
                    if res:                        
                        for r in res:
                            pr_id=purchase_requisition_cbn_obj.create(cr, uid, {
                                'product_id':r['product_id'] ,
                                'besoin_brut':r['product_qty'],
                                'date_start':pdp_line.date_start,
                                'date_stop':pdp_line.date_stop,
                                'pdp_id':pdp.id                               
                                            })
                            routes= self.pool.get('product.product').browse(cr,uid,r['product_id']).route_ids
                            for r in routes:
                                if r.name=='Manufacture':
                                    ordre_travail_obj = self.pool.get('ordre.travail')
                                    bom_id_mp=bom_obj.search(cr,uid,[('product_id','=',r['product_id'])])

                                    if bom_id_mp:
                                        bom_browse= bom_obj.browse(cr,uid,bom_id_mp[0])
                                        if bom_browse.routing_id:
                                            for op in bom_browse.routing_id.workcenter_lines:
                                                ot_id = ordre_travail_obj.create(cr, uid, {
                                                           'pdp_id':pdp.id,
                                                           'workcenter_id':op.workcenter_id.id,
                                                           'capacity':op.hour_nbr * r['product_qty'],
                                                           'date_planned':pdp_line.date_start
                                                        })
                                                print   ot_id,'ot_id'
        return True
    
pdp()

class pdp_line(osv.osv):
    _name = "pdp.line"

    _columns = {
            'period': fields.char(string=u'Nom de la période', size=64, required=True),
            'date_start': fields.date(string=u'Date début de période', required=True),
            'date_stop': fields.date(string=u'Date fin de période', required=True),
            'forecast_qty': fields.float(string=u'Forcasting', required=True),
            'stock_qty': fields.float(string=u'Stock', required=True),
            'of_plannifie_qty': fields.float(string=u'OF Plannifié'),
            'planned_order_qty': fields.float(string=u'Planned order'),
            'pdp_id':fields.many2one('pdp', string=u'PDP', required=True, ondelete='cascade'),   
                }
pdp_line()

class planned_order(osv.osv):
    _name = "planned.order"

    def _get_of(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        mrp_production_obj = self.pool.get('mrp.production')
        
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id]=0
            of_id=mrp_production_obj.search(cr,uid,[('id','=',rec.of)])
            if of_id: 
                res[rec.id] = rec.of   
        return res

    _columns = {
            'name': fields.char(u"Numéro",size=128),    
            'product_id': fields.many2one('product.product', string=u'Produit', required=True),
            'qty': fields.float(string=u'Quantité', required=True),
            'date': fields.date(string=u'Date', required=True),
            'bom_id':fields.many2one('mrp.bom', string=u'Nomenclature', required=True), 
            'routing_id':fields.many2one('mrp.routing', string=u'Gamme'),
            'pdp_id':fields.many2one('pdp', string=u'PDP'),
            'of': fields.integer(u'OF'), 
            'of_id': fields.function(_get_of, type="many2one",relation="mrp.production",string=u'Ordre de fabrication'),            
                }
    
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'planned_order'),
                }
    
    def create_mrp_production(self, cr, uid, ids, context=None):
        mrp_production_obj = self.pool.get('mrp.production')
        ordre_travail_obj = self.pool.get('ordre.travail')
        for record in self.browse(cr, uid, ids, context=context):
            #otp_ids=ordre_travail_obj.search(cr,uid,[('planned_order_id','=',record.id)])
            #if otp_ids:
             #   raise osv.except_osv(('Attention!'),(u'OTP déjà crée'))
            cr.execute('delete from mrp_production where planned_order_id='+str(record.id))
            
            of_id = mrp_production_obj.create(cr, uid, {
                       'planned_order_id':record.id,
                       'product_id':record.product_id.id,
                       'product_uom':record.product_id.uom_id.id,
                       'bom_id':record.bom_id.id,
                       'routing_id':record.routing_id.id, 
                       'product_qty':record.qty,
                       'date_planned':datetime.strptime(record.date, "%Y-%m-%d")
                    })                                              
            self.write(cr, uid,ids, {'of':of_id})

    def create_ordre_travail(self, cr, uid, ids, context=None):
        ordre_travail_obj = self.pool.get('ordre.travail')
        mrp_production_obj = self.pool.get('mrp.production')
        for record in self.browse(cr, uid, ids, context=context):
            of_ids=mrp_production_obj.search(cr,uid,[('planned_order_id','=',record.id)])
            if of_ids:
                raise osv.except_osv(('Attention!'),(u'OF déjà crée'))
            cr.execute('delete from ordre_travail where planned_order_id='+str(record.id))
            for op in record.routing_id.workcenter_lines:
                ot_id = ordre_travail_obj.create(cr, uid, {                                
                           'planned_order_id':record.id,
                           'workcenter_id':op.workcenter_id.id,
                           'capacity':op.hour_nbr * record.qty,
                           'date_planned':datetime.strptime(record.date, "%Y-%m-%d")
                        })            
planned_order()    


class mrp_production(osv.osv):
    _name='mrp.production'
    _inherit = "mrp.production"
    
    _columns={
        'planned_order_id':fields.many2one('planned.order', string=u'Planned order'),
        }
    

mrp_production


class capacity(osv.osv):
    _name = "capacity"

    def create_capacity_line(self, cr, uid, ids, context=None):
        capacity_line_obj = self.pool.get('capacity.line')        
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        
        
        for rec in self.browse(cr, uid, ids, context=context):
            cr.execute('delete from capacity_line where capacity_id='+str(rec.id))
            ds = datetime.strptime(rec.date_start, '%Y-%m-%d')
            dt_stp = datetime.strptime(rec.date_stop, '%Y-%m-%d')
            
            if rec.period_type=='monthly':
                    while ds.strftime('%Y-%m-%d') < rec.date_stop:
                        de = ds + relativedelta(months=1, seconds=-1)
                        
                        if dt_stp < de:
                            de = dt_stp + relativedelta(days=1, seconds =-1)
                        else:
                            de = ds + relativedelta(months=1, seconds=-1)
                            
                        new_name = ds.strftime('%m/%Y')
                        if ds.strftime('%m') != de.strftime('%m'):
                            new_name = ds.strftime('%m/%Y') + '-' + de.strftime('%m/%Y') 
                        
                        dts=ds + relativedelta(months=-1) 
                        dtstop= dts + relativedelta(months=1, seconds=-1)
                        
                        date_from=ds.strftime('%d-%m-%Y')
                        date_to=de.strftime('%d-%m-%Y')
                        
                        charge_of=0.0
                        cr.execute("""
                        select sum(hour) 
                        from mrp_production_workcenter_line
                        where date_planned between '"""+str(date_from)+"""' and '"""+str(date_to)+""" '
                                """)
                        charge_of = cr.fetchone()

                        cr.execute("""
                        select sum(capacity) 
                        from ordre_travail
                        where date_planned between '"""+str(date_from)+"""' and '"""+str(date_to)+""" '
                                """)
                        charge_otp = cr.fetchone()
                        
                        demande=0.0
                        
                        if charge_of[0]!=None:
                            demande=charge_of[0]
                            
                        if charge_otp[0]!=None:
                            demande+=charge_otp[0]                            
                            
                        resource=rec.workcenter_id.calendar_id.id
            
                        dt_from=str(datetime.date(ds))
                        dt_from = datetime.strptime(dt_from, "%Y-%m-%d")

                        dt_to=str(datetime.date(de))
                        dt_to = datetime.strptime(dt_to, "%Y-%m-%d")                        
                        
                        total_hours = self.pool.get('resource.calendar')._interval_hours_get(cr, uid, resource, 
                                                                                            dt_from, 
                                                                                            dt_to,
                                                                                            timezone_from_uid=uid, 
                                                                                            exclude_leaves=False,
                                                                                            context=context)        
                                                     
                        capacity_line_id = capacity_line_obj.create(cr, uid, {
                            'period':new_name ,
                            'capacity':total_hours,
                            'demande':demande,
                            'capacity_id':rec.id,
                            'date_start':ds.strftime('%d-%m-%Y'),
                            'date_stop':de.strftime('%d-%m-%Y'),
                            })          
                        ds = ds + relativedelta(months=1)            
        return True

    _columns = {
            'name':fields.char(u'Opération', required=True, size=256),
            'workcenter_id': fields.many2one('mrp.workcenter', string=u'Poste de charge', required=True),
            'period_type':fields.selection([('monthly', 'Mensuellement')],u'Type de période'),   
            'date_start': fields.date(string=u'Date début', required=True),
            'date_stop': fields.date(string=u'Date fin', required=True),
            'capacity_line_ids': fields.one2many('capacity.line', 'capacity_id', string=u'Lignes capacité'),  
                }  
    _defaults={
        'period_type': 'monthly',
            }
          
capacity()

class capacity_line(osv.osv):
    _name = "capacity.line"

    def _get_ratio(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id]=0.0
            if rec.capacity and rec.demande:                
                res[rec.id] = rec.capacity / rec.demande   
        return res

    _columns = {
            'period': fields.char(string=u'Nom de la période', size=64, required=True),
            'date_start': fields.date(string=u'Date début de période', required=True),
            'date_stop': fields.date(string=u'Date fin de période', required=True),
            'capacity': fields.float(string=u'Capacité', required=True),
            'demande': fields.float(string=u'Demande', required=True),
            'capacity_id':fields.many2one('capacity', string=u'capacity', ondelete='cascade', required=True),  
            'ratio': fields.function(_get_ratio, type="float",string=u'Ratio(C/D)'),             
                }
capacity_line()   


class ordre_travail(osv.osv):
    _name = "ordre.travail"

    _columns = {
            'name':fields.char(u'Numéro', required=True, size=256),
            'workcenter_id': fields.many2one('mrp.workcenter', string=u'Poste de charge', required=True),
            'planned_order_id': fields.many2one('planned.order', string=u'Planned order'),            
            'date_planned': fields.date(string=u'Date', required=True),
            'capacity': fields.float(string=u"Nombre d'Heures", required=True),
            'pdp_id': fields.many2one('pdp', string=u'pdp_id'),             
                }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'ordre_travail'),
                }    
ordre_travail()   


class purchase_requisition_cbn(osv.osv):
    _name = "purchase.requisition.cbn"

    _columns = {
            'name': fields.char(u"Numéro",size=128),    
            'product_id': fields.many2one('product.product', string=u'Produit', required=True),
            'besoin_brut': fields.float(string=u'Besoin Brut', required=True),
            'date_start': fields.date(string=u'Date début', required=True),
            'date_stop': fields.date(string=u'Date fin', required=True),
            'pdp_id':fields.many2one('pdp', string=u'PDP', required=True, ondelete='cascade'),  
                }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'purchase_requisition_cbn'),
                }

class cbn(osv.osv):
    _name = "cbn"

    _columns = {
            'name': fields.char(u"Numéro",size=128),    
            'product_id': fields.many2one('product.product', string=u'Produit', required=True),
            'stock_initial': fields.related('product_id', 'qty_available', type='float', string='Stock initial', readonly=True),
            'date_start': fields.date(string=u'Date début', required=True),
            'date_stop': fields.date(string=u'Date fin', required=True),
            'period_type':fields.selection([('monthly', 'Mensuellement')],u'Type de période'),
            'cbn_line_ids': fields.one2many('cbn.line', 'cbn_id', string=u'Lignes CBN'),  
                }
    _defaults = {
        'name': lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'cbn'),
        'period_type': 'monthly',
                }

    def create_cbn_line(self, cr, uid, ids, context=None):
        cbn_line_obj = self.pool.get('cbn.line')                
        
        for rec in self.browse(cr, uid, ids, context=context):
            cr.execute('delete from cbn_line where cbn_id='+str(rec.id))
            ds = datetime.strptime(rec.date_start, '%Y-%m-%d')
            dt_stp = datetime.strptime(rec.date_stop, '%Y-%m-%d')
            
            if rec.period_type=='monthly':
                    de = ds + relativedelta(months=1, seconds=-1)
                    if dt_stp < de:
                        de = dt_stp + relativedelta(days=1, seconds =-1)
                    else:
                        de = ds + relativedelta(months=1, seconds=-1)
                        
                    stock_initial=rec.product_id.qty_available 

                    date_from=ds.strftime('%d-%m-%Y')
                    date_to=de.strftime('%d-%m-%Y')                       
                    besoin_brut=0.0
                    cr.execute("""
                    select sum(besoin_brut) 
                    from purchase_requisition_cbn
                    where date_start='"""+str(date_from)+"""' and date_stop='"""+str(date_to)+"""' and product_id='"""+str(rec.product_id.id)+"""'
                            """)
                    besoin_brut = cr.fetchone()[0]
                    if besoin_brut:
                        stock_qty=stock_initial-besoin_brut
                    else:
                        stock_qty=stock_initial
                    new_name = ds.strftime('%m/%Y')
                    if ds.strftime('%m') != de.strftime('%m'):
                        new_name = ds.strftime('%m/%Y') + '-' + de.strftime('%m/%Y')


                    planned_order_qty=0
                    print stock_qty,'stock_qty'

                    if not besoin_brut:
                        besoin_brut = 0

                    if stock_qty <= 0 :
                        stock_qty=abs(stock_qty)
                        lot=rec.product_id.lot
                        factor=math.ceil(float(stock_qty)/float(lot))
                        planned_order_qty=factor*lot
                        stock_qty=stock_initial-besoin_brut+planned_order_qty
                                                                                                                                        
                        cbn_line_id = cbn_line_obj.create(cr, uid, {
                            'period':new_name ,
                            'besoin_brut':besoin_brut,
                            'stock_qty':stock_qty,
                            'planned_order_qty':planned_order_qty,
                            'cbn_id':rec.id,
                            'date_start':ds.strftime('%d-%m-%Y'),
                            'date_stop':de.strftime('%d-%m-%Y'),
                            })

                    ds = ds + relativedelta(months=1)
                                    
                    while ds.strftime('%Y-%m-%d') < rec.date_stop:
                        de = ds + relativedelta(months=1, seconds=-1)
                        
                        if dt_stp < de:
                            de = dt_stp + relativedelta(days=1, seconds =-1)
                        else:
                            de = ds + relativedelta(months=1, seconds=-1)
                            
                        new_name = ds.strftime('%m/%Y')
                        if ds.strftime('%m') != de.strftime('%m'):
                            new_name = ds.strftime('%m/%Y') + '-' + de.strftime('%m/%Y') 
                        
                        dts=ds + relativedelta(months=-1) 
                        dtstop= dts + relativedelta(months=1, seconds=-1)
                        
                        date_from=ds.strftime('%d-%m-%Y')
                        date_to=de.strftime('%d-%m-%Y')
                        
                        besoin_brut=0.0
                        cr.execute("""
                        select sum(besoin_brut) 
                        from purchase_requisition_cbn
                        where date_start='"""+str(date_from)+"""' and date_stop='"""+str(date_to)+"""' and product_id='"""+str(rec.product_id.id)+"""'
                                """)
                        besoin_brut = cr.fetchone()[0]
                        
                        stock_qty=0

                                                
                        dts=ds + relativedelta(months=-1) 
                        dtstop= dts + relativedelta(months=1, seconds=-1)
                        cbn_line_id=cbn_line_obj.search(cr, uid, [('date_start','=',dts ),('date_stop','=',dtstop)], context = context)
                        stock_qty_init=cbn_line_obj.browse(cr, uid, cbn_line_id[0], context=context).stock_qty
                        
                        lot=rec.product_id.lot
                        if besoin_brut and stock_qty_init<besoin_brut:
                            stock_qty_abs=besoin_brut-stock_qty_init
                            factor=math.ceil(float(stock_qty_abs)/float(lot))
                            planned_order_qty=factor*lot
                        else:
                            planned_order_qty=0.0
                            besoin_brut=0.0
                        
                          
                        stock_qty=stock_qty_init-besoin_brut+planned_order_qty
                                                                               
                        cbn_line_id = cbn_line_obj.create(cr, uid, {
                            'period':new_name ,
                            'besoin_brut':besoin_brut,
                            'stock_qty':stock_qty,
                            'planned_order_qty':planned_order_qty,
                            'cbn_id':rec.id,
                            'date_start':ds.strftime('%d-%m-%Y'),
                            'date_stop':de.strftime('%d-%m-%Y'),
                            })          
                        ds = ds + relativedelta(months=1)            
        return True


class cbn_line(osv.osv):
    _name = "cbn.line"

    _columns = {
            'period': fields.char(string=u'Nom de la période', size=64, required=True),
            'date_start': fields.date(string=u'Date début de période', required=True),
            'date_stop': fields.date(string=u'Date fin de période', required=True),            
            'besoin_brut': fields.float(string=u'Besoin Brut', required=True),
            'stock_qty': fields.float(string=u'Stock prév', required=True),
            'planned_order_qty': fields.float(string=u'Ordre proposé'),
            'cbn_id':fields.many2one('cbn', string=u'CBN', required=True, ondelete='cascade'),   
                }
cbn_line()    
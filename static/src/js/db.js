odoo.define('pos_modifier_po_extension.db', function (require) {
	"use strict";

	var DB = require('point_of_sale.DB');

	DB.include({
		init: function(options){
        	this._super.apply(this, arguments);
        	this.sale_order_write_date = null;
        	this.sale_order_by_id = {};
        	this.sale_order_sorted = [];
        	this.sale_order_search_string = "";
        	this.all_product = []
        },
        add_sale_orders: function(orders){
            var updated_count = 0;
            var new_write_date = '';
            for(var i = 0, len = orders.length; i < len; i++){
                var order = orders[i];
                if (    this.sale_order_write_date &&
                        this.sale_order_by_id[order.id] &&
                        new Date(this.sale_order_write_date).getTime() + 1000 >=
                        new Date(order.write_date).getTime() ) {
                    continue;
                } else if ( new_write_date < order.write_date ) {
                    new_write_date  = order.write_date;
                }
                if (!this.sale_order_by_id[order.id]) {
                    this.sale_order_sorted.push(order.id);
                }
                this.sale_order_by_id[order.id] = order;
                updated_count += 1;
            }
            this.sale_order_write_date = new_write_date || this.sale_order_write_date;
            if (updated_count) {
                // If there were updates, we need to completely
                this.sale_order_search_string = "";
                for (var id in this.sale_order_by_id) {
                    var order = this.sale_order_by_id[id];
                    this.sale_order_search_string += this._sale_order_search_string(order);
                }
            }
            return updated_count;
        },
        _sale_order_search_string: function(order){
            var str =  order.name;
            if(order.partner_id){
                str += '|' + order.partner_id[1];
            }
            str = '' + order.id + ':' + str.replace(':','') + '\n';
            return str;
        },
        get_sale_order_write_date: function(){
            return this.sale_order_write_date;
        },
        get_sale_order_by_id: function(id){
            return this.sale_order_by_id[id];
        },
        search_order: function(query){
            try {
                query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
                query = query.replace(' ','.+');
                var re = RegExp("([0-9]+):.*?"+query,"gi");
            }catch(e){
                return [];
            }
            var results = [];
            var r;
            for(var i = 0; i < this.limit; i++){
                r = re.exec(this.sale_order_search_string);
                if(r){
                    var id = Number(r[1]);
                    results.push(this.get_sale_order_by_id(id));
                }else{
                    break;
                }
            }
            return results;
        },
        get_all_product: function(){
	        return this.all_product
	    },
	});

});
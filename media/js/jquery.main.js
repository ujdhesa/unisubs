$(function(){
	gallery();
	initListslide();
	initScrolSlide();
});
function initScrolSlide(){
	$('#main').each(function(){
		var hold = $(this);
		var link = hold.find('#nav .menu  li>a');
		var box =hold.find('.block')
		link.click(function(){
			$(window).scrollTo($($(this).attr('href')), 1000);
		});
	});
}
function gallery(){
	var speed = 700;
	$('div.gallery').each(function(){
		var hold = $(this);
		var t;
		var list = hold.find('div.gallery-holder > ul')
		var li = hold.find('div.gallery-holder > ul > li')
		var w = li.outerWidth(); 
		var prev = hold.find('a.link-prev');
		var next = hold.find('a.link-next');
		var box = hold.find('ul.list-item > li')
		var a = li.index(li.index(li.filter('.active:eq(0)')));
		var swit = hold.find('ul.switcher > li');
		if(a == -1) a = 0;
		li.eq(a);
		box.removeClass('active').css({opacity: 0}).eq(a).addClass('active').css({opacity: 1});
		swit.removeClass('active').eq(a).addClass('active');
		swit.click(function(){
			changeEl(swit.index(this));
			return false;
		});
		function changeEl(active){
			if (t) clearTimeout(t);
			if (active != a) {
				swit.eq(a).removeClass('active');
				swit.eq(active).addClass('active');
				box.eq(a).removeClass('active').animate({opacity: 0}, {queue: false,duration: speed});
				box.eq(active).addClass('active').animate({opacity: 1}, {queue: false,duration: speed});
				list.animate({left:- w*active}, {queue: false,duration: speed});
				a = active;
			}
			t = setTimeout(function(){
			if(a < li.length - 1) changeEl(a+1);
				else changeEl(0);
			}, 3000);
		}
		
		t = setTimeout(function(){
		if(a < li.length - 1) changeEl(a+1);
			else changeEl(0);
		}, 3000);

		next.click(function(){
			if(a != li.length - 1) changeEl(a + 1);
			else changeEl(0);
			return false;
		});

		prev.click(function(){
			if(a != 0) changeEl(a - 1);
			else changeEl(li.length - 1);
			return false;
		});
	})
}

function initListslide(){
	$('.publish').each(function(){		var hold = $(this);		var block = hold.find('.publish-block');
		var activeList = block.index(block.index(block.filter('.active:eq(0)')));
		var time;
		if(activeList == -1) activeList = 0;
		block.eq(activeList);
		block.removeClass('active').css({opacity: 0}).eq(activeList).addClass('active').css({opacity: 1});
		function changeEl(active){
			if (time) clearTimeout(time);
			if (active != activeList) {
				block.eq(activeList).removeClass('active').animate({opacity: 0}, {queue: false,duration: 300}).css({position: 'absolute'});
				block.eq(active).addClass('active').animate({opacity: 1}, {queue: false,duration: 300}).css({position: 'static'});;
				activeList = active;
			}
			time = setTimeout(function(){
			if(activeList < block.length - 1) changeEl(activeList+1);
				else changeEl(0);
			}, 3000);
		}
		time = setTimeout(function(){
		if(activeList < block.length - 1) changeEl(activeList+1);
			else changeEl(0);
		}, 3000);
	});
}
/**
 * Copyright (c) 2007-2012 Ariel Flesler - aflesler(at)gmail(dot)com | http://flesler.blogspot.com
 * Dual licensed under MIT and GPL.
 * @author Ariel Flesler
 * @version 1.4.3.1
 */
;(function($){var h=$.scrollTo=function(a,b,c){$(window).scrollTo(a,b,c)};h.defaults={axis:'xy',duration:parseFloat($.fn.jquery)>=1.3?0:1,limit:true};h.window=function(a){return $(window)._scrollable()};$.fn._scrollable=function(){return this.map(function(){var a=this,isWin=!a.nodeName||$.inArray(a.nodeName.toLowerCase(),['iframe','#document','html','body'])!=-1;if(!isWin)return a;var b=(a.contentWindow||a).document||a.ownerDocument||a;return/webkit/i.test(navigator.userAgent)||b.compatMode=='BackCompat'?b.body:b.documentElement})};$.fn.scrollTo=function(e,f,g){if(typeof f=='object'){g=f;f=0}if(typeof g=='function')g={onAfter:g};if(e=='max')e=9e9;g=$.extend({},h.defaults,g);f=f||g.duration;g.queue=g.queue&&g.axis.length>1;if(g.queue)f/=2;g.offset=both(g.offset);g.over=both(g.over);return this._scrollable().each(function(){if(e==null)return;var d=this,$elem=$(d),targ=e,toff,attr={},win=$elem.is('html,body');switch(typeof targ){case'number':case'string':if(/^([+-]=)?\d+(\.\d+)?(px|%)?$/.test(targ)){targ=both(targ);break}targ=$(targ,this);if(!targ.length)return;case'object':if(targ.is||targ.style)toff=(targ=$(targ)).offset()}$.each(g.axis.split(''),function(i,a){var b=a=='x'?'Left':'Top',pos=b.toLowerCase(),key='scroll'+b,old=d[key],max=h.max(d,a);if(toff){attr[key]=toff[pos]+(win?0:old-$elem.offset()[pos]);if(g.margin){attr[key]-=parseInt(targ.css('margin'+b))||0;attr[key]-=parseInt(targ.css('border'+b+'Width'))||0}attr[key]+=g.offset[pos]||0;if(g.over[pos])attr[key]+=targ[a=='x'?'width':'height']()*g.over[pos]}else{var c=targ[pos];attr[key]=c.slice&&c.slice(-1)=='%'?parseFloat(c)/100*max:c}if(g.limit&&/^\d+$/.test(attr[key]))attr[key]=attr[key]<=0?0:Math.min(attr[key],max);if(!i&&g.queue){if(old!=attr[key])animate(g.onAfterFirst);delete attr[key]}});animate(g.onAfter);function animate(a){$elem.animate(attr,f,g.easing,a&&function(){a.call(this,e,g)})}}).end()};h.max=function(a,b){var c=b=='x'?'Width':'Height',scroll='scroll'+c;if(!$(a).is('html,body'))return a[scroll]-$(a)[c.toLowerCase()]();var d='client'+c,html=a.ownerDocument.documentElement,body=a.ownerDocument.body;return Math.max(html[scroll],body[scroll])-Math.min(html[d],body[d])};function both(a){return typeof a=='object'?a:{top:a,left:a}}})(jQuery);

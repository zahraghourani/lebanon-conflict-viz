const ADV_EVENT_LABELS = {
    "Explosions/Remote violence": "Explosions",
    "Violence against civilians": "V. vs Civilians",
    "Strategic developments":     "Strategic Dev.",
};
function eventColor(name) { return (typeof EVENT_COLORS !== "undefined" && EVENT_COLORS[name]) || "#999"; }
function eventLabel(name) { return ADV_EVENT_LABELS[name] || name; }

// ── RESPONSIVE WIDTH HELPER ──────────────────────────────────────────────────
function containerWidth(el, fallback) {
    fallback = fallback || 640;
    var rect = el.getBoundingClientRect();
    return Math.max(rect.width || el.clientWidth || fallback, 200);
}

// ── TOOLTIP HELPER ───────────────────────────────────────────────────────────
function makeTooltip(parentEl) {
    var tip = document.createElement("div");
    tip.className = "adv-tooltip-el";
    parentEl.style.position = "relative";
    parentEl.appendChild(tip);
    return {
        show: function(html, event) {
            tip.innerHTML = html;
            tip.style.display = "block";
            this.move(event);
        },
        move: function(event) {
            var r = parentEl.getBoundingClientRect();
            var x = event.clientX - r.left + 14;
            var y = event.clientY - r.top  - 10;
            if (x + 240 > r.width) x = event.clientX - r.left - 240;
            if (y < 0) y = 4;
            tip.style.left = x + "px";
            tip.style.top  = y + "px";
        },
        hide: function() { tip.style.display = "none"; }
    };
}

// ═══════════════════════════════════════════════════════════════════════════
//  1. ZOOMABLE SUNBURST
// ═══════════════════════════════════════════════════════════════════════════

async function refreshSunburst() {
    var container = document.getElementById("chart-sunburst");
    if (!container) return;
    container.innerHTML = '<div class="adv-loading">Loading hierarchy…</div>';
    try {
        var data = await fetchJSON(API + "/api/sunburst?" + buildParams());
        drawSunburst(data, container);
    } catch(e) {
        console.error("Sunburst:", e);
        container.innerHTML = '<p class="no-data">Could not load data.</p>';
    }
}

function drawSunburst(data, container) {
    container.innerHTML = "";
    if (!data.children || !data.children.length) {
        container.innerHTML = '<p class="no-data">No data for current filters.</p>';
        return;
    }

    var W      = Math.min(containerWidth(container), 620);
    var radius = W / 6;

    var countryColor = d3.scaleOrdinal(
        data.children.map(function(d){ return d.name; }),
        d3.schemeTableau10
    );
    function nodeColor(d) {
        if (d.depth === 0) return "transparent";
        if (d.depth === 1) return countryColor(d.data.name);
        return eventColor(d.data.name);
    }

    var hierarchy = d3.hierarchy(data)
        .sum(function(d){ return d.value || 0; })
        .sort(function(a,b){ return (b.value||0)-(a.value||0); });
    var root = d3.partition().size([2*Math.PI, hierarchy.height+1])(hierarchy);
    root.each(function(d){ d.current = d; });

    var arc = d3.arc()
        .startAngle(function(d){ return d.x0; })
        .endAngle(function(d){ return d.x1; })
        .padAngle(function(d){ return Math.min((d.x1-d.x0)/2, 0.006); })
        .padRadius(radius*1.5)
        .innerRadius(function(d){ return d.y0*radius; })
        .outerRadius(function(d){ return Math.max(d.y0*radius, d.y1*radius-1); });

    var svg = d3.select(container).append("svg")
        .attr("viewBox", [0,0,W,W])
        .style("width","100%").style("height","auto").style("display","block");
    var g = svg.append("g").attr("transform","translate("+W/2+","+W/2+")");

    var path = g.append("g").selectAll("path")
        .data(root.descendants().slice(1)).join("path")
        .attr("fill", function(d){ return nodeColor(d); })
        .attr("fill-opacity", function(d){ return arcVisible(d.current)?(d.children?0.88:0.72):0; })
        .attr("pointer-events", function(d){ return arcVisible(d.current)?"auto":"none"; })
        .attr("d", function(d){ return arc(d.current); })
        .style("cursor", function(d){ return d.children?"pointer":"default"; })
        .style("transition","filter 0.12s");

    path.filter(function(d){ return d.children; }).on("click", clicked);

    var tip = makeTooltip(container);
    path.on("mousemove", function(event,d){
        var fat = d.data.fatalities!=null
            ? "<br>Fatalities: <strong>"+d.data.fatalities.toLocaleString()+"</strong>" : "";
        tip.show("<strong>"+d.data.name+"</strong><br>Events: <strong>"+(d.value||0).toLocaleString()+"</strong>"+fat, event);
        d3.select(event.currentTarget).style("filter","brightness(1.22)");
    }).on("mouseout", function(event){
        tip.hide();
        d3.select(event.currentTarget).style("filter",null);
    });

    var label = g.append("g")
        .attr("pointer-events","none").attr("text-anchor","middle")
        .style("user-select","none")
        .selectAll("text").data(root.descendants().slice(1)).join("text")
        .attr("dy","0.35em")
        .attr("fill-opacity", function(d){ return +labelVisible(d.current); })
        .attr("transform", function(d){ return labelTransform(d.current); })
        .text(function(d){ var n=d.data.name; return n.length>15?n.slice(0,13)+"…":n; })
        .style("font-size", function(d){ return d.depth===1?"11px":"9.5px"; })
        .style("font-weight", function(d){ return d.depth===1?"600":"400"; })
        .style("fill","#fff"); // white on coloured arc — always legible

    var centerG = g.append("g");
    centerG.append("circle").datum(root)
        .attr("r", radius)
        .attr("fill","rgba(240,242,245,0.9)")
        .attr("stroke","#ddd").attr("stroke-width",1)
        .attr("pointer-events","all").style("cursor","pointer")
        .on("click", clicked);
    var centerText = centerG.append("text")
        .attr("text-anchor","middle")
        .style("fill","#555").style("font-size","12px").style("font-weight","600")
        .style("pointer-events","none");
    centerText.append("tspan").attr("x",0).attr("y","-0.3em").text("Click ring");
    centerText.append("tspan").attr("x",0).attr("dy","1.4em").text("to drill in");

    function clicked(event,p) {
        centerG.select("circle").datum(p.parent||root);
        root.each(function(d){
            d.target = {
                x0: Math.max(0,Math.min(1,(d.x0-p.x0)/(p.x1-p.x0)))*2*Math.PI,
                x1: Math.max(0,Math.min(1,(d.x1-p.x0)/(p.x1-p.x0)))*2*Math.PI,
                y0: Math.max(0,d.y0-p.depth),
                y1: Math.max(0,d.y1-p.depth)
            };
        });
        var t = g.transition().duration(750).ease(d3.easeCubicInOut);
        path.transition(t)
            .tween("data",function(d){
                var i=d3.interpolate(d.current,d.target);
                return function(tt){ d.current=i(tt); };
            })
            .filter(function(d){ return +this.getAttribute("fill-opacity")||arcVisible(d.target); })
            .attr("fill-opacity",function(d){ return arcVisible(d.target)?(d.children?0.88:0.72):0; })
            .attr("pointer-events",function(d){ return arcVisible(d.target)?"auto":"none"; })
            .attrTween("d",function(d){ return function(){ return arc(d.current); }; });
        label.filter(function(d){ return +this.getAttribute("fill-opacity")||labelVisible(d.target); })
            .transition(t)
            .attr("fill-opacity",function(d){ return +labelVisible(d.target); })
            .attrTween("transform",function(d){ return function(){ return labelTransform(d.current); }; });
        var name = p.data.name==="Conflict"?"All Countries":p.data.name;
        centerText.selectAll("tspan").remove();
        centerText.append("tspan").attr("x",0).attr("y",p.depth>0?"-0.2em":"-0.3em")
            .style("fill","#1a1a2e").text(name);
        if (p.depth>0) {
            centerText.append("tspan").attr("x",0).attr("dy","1.4em")
                .style("font-size","10px").style("font-weight","400").style("fill","#888")
                .text("click centre ← back");
        } else {
            centerText.append("tspan").attr("x",0).attr("dy","1.4em")
                .style("fill","#777").text("to drill in");
        }
    }

    function arcVisible(d){ return d.y1<=3&&d.y0>=1&&d.x1>d.x0; }
    function labelVisible(d){ return d.y1<=3&&d.y0>=1&&(d.y1-d.y0)*(d.x1-d.x0)>0.032; }
    function labelTransform(d){
        var x=((d.x0+d.x1)/2)*(180/Math.PI);
        var y=((d.y0+d.y1)/2)*radius;
        return "rotate("+(x-90)+") translate("+y+",0) rotate("+(x<180?0:180)+")";
    }

    // Country legend
    var COLS=3, legRows=Math.ceil(data.children.length/COLS), legH=legRows*20+12;
    var colW=(W-16)/COLS;
    var legSvg=d3.select(container).append("svg")
        .attr("viewBox",[0,0,W,legH]).style("width","100%").style("height",legH+"px")
        .style("display","block").style("margin-top","6px");
    var lg=legSvg.append("g").attr("transform","translate(8,8)");
    data.children.forEach(function(d,i){
        var col=i%COLS, row=Math.floor(i/COLS);
        var grp=lg.append("g").attr("transform","translate("+(col*colW)+","+(row*20)+")");
        grp.append("rect").attr("width",11).attr("height",11).attr("rx",2)
            .attr("fill",countryColor(d.name));
        grp.append("text").attr("x",16).attr("y",9)
            .style("font-size","11px").style("fill","#555")
            .text(d.name.replace("Occupied Palestine","Palestine"));
    });
}


// ═══════════════════════════════════════════════════════════════════════════
//  2. CHORD DIAGRAM
// ═══════════════════════════════════════════════════════════════════════════

async function refreshChordDiagram() {
    var container = document.getElementById("chart-chord");
    if (!container) return;
    container.innerHTML = '<div class="adv-loading">Computing co-occurrence matrix…</div>';
    try {
        var data = await fetchJSON(API + "/api/chord?" + buildParams());
        drawChordDiagram(data.matrix, data.labels, container);
    } catch(e) {
        console.error("Chord:", e);
        container.innerHTML = '<p class="no-data">Could not load data.</p>';
    }
}

function drawChordDiagram(matrix, labels, container) {
    container.innerHTML = "";
    if (!matrix || !matrix.length) {
        container.innerHTML = '<p class="no-data">No data for current filters.</p>';
        return;
    }
    var W           = Math.min(containerWidth(container), 620);
    var outerRadius = W/2 - 80;
    var innerRadius = outerRadius - 20;

    var colorScale = d3.scaleOrdinal()
        .domain(labels.map(function(_,i){ return i; }))
        .range(labels.map(function(l){ return eventColor(l); }));

    var chord   = d3.chord().padAngle(0.06).sortSubgroups(d3.descending).sortChords(d3.descending);
    var chords  = chord(matrix);
    var arcGen  = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius);
    var ribbGen = d3.ribbon().radius(innerRadius-1);

    var svg = d3.select(container).append("svg")
        .attr("viewBox",[-W/2,-W/2,W,W])
        .style("width","100%").style("height","auto")
        .style("display","block").style("overflow","visible");

    var tip = makeTooltip(container);
    var group = svg.append("g").selectAll("g").data(chords.groups).join("g");

    group.append("path")
        .style("fill",   function(d){ return colorScale(d.index); })
        .style("stroke", function(d){ return d3.rgb(colorScale(d.index)).darker(0.5); })
        .attr("d", arcGen).style("cursor","pointer")
        .on("mouseover", function(_,d){
            svg.selectAll(".chord-ribbon").attr("fill-opacity",function(c){
                return c.source.index===d.index||c.target.index===d.index?0.85:0.06;
            });
        })
        .on("mousemove", function(event,d){
            var total=matrix[d.index].reduce(function(a,b){return a+b;},0);
            tip.show("<strong>"+eventLabel(labels[d.index])+"</strong><br>Total weight: <strong>"+total.toLocaleString()+"</strong>", event);
        })
        .on("mouseout", function(){
            svg.selectAll(".chord-ribbon").attr("fill-opacity",0.65);
            tip.hide();
        });

    // Tick marks
    group.each(function(d){
        var span=d.endAngle-d.startAngle;
        var step=span>0.3?0.08:span>0.1?0.12:0.25;
        d3.select(this).selectAll("g.tick")
            .data(d3.range(d.startAngle,d.endAngle-1e-6,step)).join("g").attr("class","tick")
            .attr("transform",function(a){ return "rotate("+(a*180/Math.PI-90)+") translate("+outerRadius+",0)"; })
            .call(function(g){ g.append("line").attr("x2",5)
                .attr("stroke","rgba(0,0,0,0.15)").attr("stroke-width",0.8); });
    });

    // Labels
    group.append("text")
        .each(function(d){ d.angle=(d.startAngle+d.endAngle)/2; })
        .attr("dy","0.35em")
        .attr("transform",function(d){
            return "rotate("+(d.angle*180/Math.PI-90)+") translate("+(outerRadius+14)+") "+(d.angle>Math.PI?"rotate(180)":"");
        })
        .attr("text-anchor",function(d){ return d.angle>Math.PI?"end":"start"; })
        .text(function(d){ return eventLabel(labels[d.index]); })
        .style("font-size","11.5px").style("font-weight","600")
        .style("fill",function(d){ return colorScale(d.index); });

    // Ribbons
    svg.append("g").attr("fill-opacity",0.65).selectAll("path")
        .data(chords).join("path").attr("class","chord-ribbon")
        .attr("d",ribbGen)
        .style("fill",   function(d){ return colorScale(d.target.index); })
        .style("stroke", function(d){ return d3.rgb(colorScale(d.target.index)).darker(0.4); })
        .style("stroke-width",0.5).style("cursor","pointer")
        .on("mousemove",function(event,d){
            tip.show(
                "<strong>"+eventLabel(labels[d.source.index])+"</strong> ↔ <strong>"+eventLabel(labels[d.target.index])+"</strong><br>Co-occurrences: <strong>"+d.source.value.toLocaleString()+"</strong>",
                event
            );
        })
        .on("mouseout",function(){ tip.hide(); });
}


// ═══════════════════════════════════════════════════════════════════════════
//  3. NIGHTINGALE COXCOMB
// ═══════════════════════════════════════════════════════════════════════════

async function refreshCoxcomb() {
    var container = document.getElementById("chart-coxcomb");
    if (!container) return;
    container.innerHTML = '<div class="adv-loading">Drawing polar diagram…</div>';
    try {
        var data = await fetchJSON(API + "/api/fatalities/by-type?" + buildParams());
        drawCoxcomb(data.data||[], container);
    } catch(e) {
        console.error("Coxcomb:", e);
        container.innerHTML = '<p class="no-data">Could not load data.</p>';
    }
}

function drawCoxcomb(rows, container) {
    container.innerHTML = "";
    if (!rows.length) { container.innerHTML = '<p class="no-data">No data for current filters.</p>'; return; }

    var months  = [...new Set(rows.map(function(d){return d.year_month;}))].sort();
    var evTypes = Object.keys(EVENT_COLORS);
    var byMonth = {};
    months.forEach(function(m){ byMonth[m]={}; });
    rows.forEach(function(r){
        if (byMonth[r.year_month]!==undefined)
            byMonth[r.year_month][r.event_type]=(byMonth[r.year_month][r.event_type]||0)+r.fatalities;
    });
    var monthData = months.map(function(m){
        return {
            month:  m,
            label:  m.slice(5)+"/"+m.slice(2,4),
            total:  evTypes.reduce(function(s,et){return s+(byMonth[m][et]||0);},0),
            byType: evTypes.map(function(et){return {et:et,val:byMonth[m][et]||0};})
        };
    });

    var maxTotal = Math.max.apply(null, monthData.map(function(d){return d.total;}));
    maxTotal = maxTotal || 1;
    var W       = Math.min(containerWidth(container), 680);
    var COLS    = 2;
    var legRows = Math.ceil(evTypes.length/COLS);
    var LEGEND_H= legRows*22+16;
    var outerR  = W/2-54, innerR=22;
    var n       = months.length, slice=(2*Math.PI)/n, gap=slice*0.07;

    var rScale = d3.scalePow().exponent(0.5).domain([0,maxTotal]).range([innerR,outerR]);
    var totalH = W + LEGEND_H;

    var svg = d3.select(container).append("svg")
        .attr("viewBox",[0,0,W,totalH])
        .style("width","100%").style("height","auto").style("display","block");
    var g = svg.append("g").attr("transform","translate("+(W/2)+","+(W/2)+")");

    // Grid
    for (var i=1;i<=4;i++){
        var gr=rScale(maxTotal*i/4);
        g.append("circle").attr("r",gr).attr("fill","none")
            .attr("stroke","#e8e8e8").attr("stroke-dasharray","4,3");
        g.append("text").attr("x",0).attr("y",-gr-4).attr("text-anchor","middle")
            .style("font-size","9px").style("fill","#bbb")
            .text(Math.round(maxTotal*i/4).toLocaleString());
    }

    var tip = makeTooltip(container);

    monthData.forEach(function(md,i){
        var startAngle=i*slice-Math.PI/2+gap/2;
        var endAngle=startAngle+slice-gap;
        var wg=g.append("g");
        // Largest first (behind), smallest last (on top) — Nightingale overlap
        var sorted=[...md.byType].sort(function(a,b){return b.val-a.val;});
        sorted.forEach(function(item){
            if(!item.val) return;
            wg.append("path")
                .attr("d",d3.arc().innerRadius(innerR).outerRadius(rScale(item.val))
                    .startAngle(startAngle).endAngle(endAngle)())
                .attr("fill",eventColor(item.et)).attr("fill-opacity",0.8)
                .attr("stroke","#fff").attr("stroke-width",0.6);
        });
        // Hit area
        wg.append("path")
            .attr("d",d3.arc().innerRadius(innerR).outerRadius(outerR)
                .startAngle(startAngle).endAngle(endAngle)())
            .attr("fill","transparent").style("cursor","pointer")
            .on("mousemove",function(event){
                var breakdown=md.byType.filter(function(x){return x.val>0;})
                    .sort(function(a,b){return b.val-a.val;})
                    .map(function(x){return '<span style="color:'+eventColor(x.et)+'">■</span> '+eventLabel(x.et)+': <strong>'+x.val.toLocaleString()+'</strong>';})
                    .join("<br>");
                tip.show("<strong>"+md.month+"</strong><br>Total: <strong>"+md.total.toLocaleString()+"</strong><br>"+breakdown, event);
            })
            .on("mouseout",function(){ tip.hide(); });
        // Month label
        // WITH this:
        var mid=(startAngle+endAngle)/2, lr=outerR+18;
        g.append("text")
            .attr("x", lr * Math.sin(mid))      // ← correct D3-to-SVG conversion
            .attr("y", -lr * Math.cos(mid))     // ← correct D3-to-SVG conversion
            .attr("text-anchor","middle").attr("dy","0.35em")
            .style("font-size","9px").style("fill","#888").text(md.label);
            });

    // Centre
    var grand=monthData.reduce(function(s,d){return s+d.total;},0);
    g.append("text").attr("text-anchor","middle").attr("dy","-0.2em")
        .style("font-size","14px").style("font-weight","700").style("fill","#1a1a2e")
        .text(grand.toLocaleString());
    g.append("text").attr("text-anchor","middle").attr("dy","1.2em")
        .style("font-size","9px").style("fill","#999").text("total fatalities");

    // Legend
    var legColW=(W-32)/COLS;
    var legG=svg.append("g").attr("transform","translate(16,"+(W+8)+")");
    evTypes.forEach(function(et,i){
        var col=i%COLS, row=Math.floor(i/COLS);
        var lg=legG.append("g").attr("transform","translate("+(col*legColW)+","+(row*22)+")");
        lg.append("rect").attr("width",12).attr("height",12).attr("rx",2)
            .attr("fill",eventColor(et)).attr("fill-opacity",0.85);
        lg.append("text").attr("x",18).attr("y",10)
            .style("font-size","11px").style("fill","#555").text(eventLabel(et));
    });
}


// ═══════════════════════════════════════════════════════════════════════════
//  4. BUMP / RANK CHART
// ═══════════════════════════════════════════════════════════════════════════

async function refreshBumpChart() {
    var container = document.getElementById("chart-bump");
    if (!container) return;
    container.innerHTML = '<div class="adv-loading">Ranking countries…</div>';
    try {
        var data = await fetchJSON(API + "/api/bump?" + buildParams());
        drawBumpChart(data.data||[], container);
    } catch(e) {
        console.error("Bump:", e);
        container.innerHTML = '<p class="no-data">Could not load data.</p>';
    }
}

function drawBumpChart(rows, container) {
    container.innerHTML = "";
    if (!rows.length) { container.innerHTML = '<p class="no-data">No data for current filters.</p>'; return; }

    var months    = [...new Set(rows.map(function(d){return d.year_month;}))].sort();
    var countries = [...new Set(rows.map(function(d){return d.country;}))];
    var maxRank   = Math.max.apply(null, rows.map(function(d){return d.rank;}));

    var lookup={};
    rows.forEach(function(r){
        if(!lookup[r.country]) lookup[r.country]={};
        lookup[r.country][r.year_month]={rank:r.rank,events:r.events};
    });

    var margin={top:24,right:110,bottom:36,left:40};
    // Use container width at render time
    var CW     = containerWidth(container);
    var innerW = Math.max(CW - margin.left - margin.right, 220);
    var innerH = Math.max(maxRank*44, 260);
    var totalW = innerW + margin.left + margin.right;
    var totalH = innerH + margin.top  + margin.bottom;

    var xScale = d3.scalePoint().domain(months).range([0,innerW]).padding(0.4);
    var yScale = d3.scaleLinear().domain([0.5,maxRank+0.5]).range([0,innerH]);
    var cColor = d3.scaleOrdinal(countries, d3.schemeTableau10);

    // viewBox keeps proportions; explicit height prevents collapse
    var svg = d3.select(container).append("svg")
        .attr("viewBox",[0,0,totalW,totalH])
        .style("width","100%")
        .style("height",totalH+"px")
        .style("display","block");
    var g = svg.append("g").attr("transform","translate("+margin.left+","+margin.top+")");

    // Horizontal rank grid
    for (var r=1;r<=maxRank;r++){
        g.append("line")
            .attr("x1",0).attr("x2",innerW).attr("y1",yScale(r)).attr("y2",yScale(r))
            .attr("stroke","#f0f0f0").attr("stroke-width",1);
        g.append("text").attr("x",-8).attr("y",yScale(r)).attr("dy","0.35em")
            .attr("text-anchor","end").style("font-size","10px").style("fill","#ccc")
            .text("#"+r);
    }

    // Month axis
    g.append("g").attr("transform","translate(0,"+(innerH+8)+")")
        .call(d3.axisBottom(xScale).tickSize(0))
        .call(function(ax){ ax.select(".domain").remove(); })
        .selectAll("text")
        .style("fill","#999").style("font-size","10px").attr("dy","1em");

    var tip  = makeTooltip(container);
    var line = d3.line()
        .x(function(d){ return xScale(d.month); })
        .y(function(d){ return yScale(d.rank);  })
        .curve(d3.curveCatmullRom.alpha(0.5))
        .defined(function(d){ return d.rank!=null; });

    countries.forEach(function(country){
        var pts=months.filter(function(m){return lookup[country]&&lookup[country][m];})
            .map(function(m){return {month:m,rank:lookup[country][m].rank,events:lookup[country][m].events};});
        if (pts.length<2) return;
        var col=cColor(country);
        // Shadow
        g.append("path").datum(pts).attr("fill","none")
            .attr("stroke","rgba(0,0,0,0.08)").attr("stroke-width",6)
            .attr("stroke-linecap","round").attr("d",line);
        // Line
        g.append("path").datum(pts).attr("fill","none")
            .attr("stroke",col).attr("stroke-width",2.8)
            .attr("stroke-linecap","round").attr("d",line);
        // Dots
        pts.forEach(function(pt){
            g.append("circle")
                .attr("cx",xScale(pt.month)).attr("cy",yScale(pt.rank)).attr("r",5)
                .attr("fill",col).attr("stroke","#fff").attr("stroke-width",1.8)
                .style("cursor","pointer")
                .on("mousemove",function(event){
                    tip.show("<strong>"+country+"</strong><br>Month: "+pt.month+"<br>Rank: <strong>#"+pt.rank+"</strong><br>Events: <strong>"+pt.events.toLocaleString()+"</strong>",event);
                })
                .on("mouseout",function(){ tip.hide(); });
        });
        // End label
        var last=pts[pts.length-1];
        g.append("text")
            .attr("x",xScale(last.month)+10).attr("y",yScale(last.rank)).attr("dy","0.35em")
            .style("fill",col).style("font-size","11px").style("font-weight","600")
            .text(country.replace("Occupied Palestine","Palestine").replace("Saudi Arabia","S. Arabia"));
    });
}


// ═══════════════════════════════════════════════════════════════════════════
//  ORCHESTRATOR — call this from refreshAll() in app.js
// ═══════════════════════════════════════════════════════════════════════════
async function refreshAdvancedCharts() {
    await Promise.all([
        refreshChordDiagram(),
        refreshCoxcomb(),
        refreshBumpChart(),
    ]);
}
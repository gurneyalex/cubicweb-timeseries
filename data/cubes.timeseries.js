
// Grid

function init_ts_grid(gridid, url) {
  var grid = jQuery('#' + gridid);
  if (grid.attr('cubicweb:type') != 'prepared-grid') {
    grid.jqGrid({
      url: url,
      datatype: 'json',
      height: 450,
      colNames:['date', 'value'],
      colModel :[
        {name:'date', index:'date', width:120, align:'center'},
        {name:'value', index:'value', width:120, align:'right'}
      ],
      sortname: 'date',
      sortorder: 'asc',
      pager: '#pager'
    });
  grid.attr('cubicweb:type', 'prepared-grid');
  }
}

// /Grid
// Plot

function init_ts_plot(figid, plotdata) {
  var mainfig = jQuery('#main' + figid);
  var overviewfig = jQuery('#overview' + figid);

  if ((mainfig.attr('cubicweb:type') != 'prepared-plot') ||
    (overviewfig.attr('cubicweb:type') != 'prepared-plot')) {

    var mainoptions = {points: {show: true, radius: 2},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: true, clickable: true},
         xaxis: {mode: "time"},
         selection: {mode: "x", color: 'blue'}
         };
    var overviewoptions = {points: {show: false},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: false},
         xaxis: {mode: "time"},
         selection: {mode: "x", color: 'blue'}
         };
    var main = jQuery.plot(mainfig, plotdata, mainoptions);
    var overview = jQuery.plot(overviewfig, plotdata, overviewoptions);
    mainfig.bind("plothover", onTSPlotHover);
    // now connect the two
    mainfig.bind("plotselected", function (event, ranges) {
        // do the zooming
        main = jQuery.plot(mainfig, plotdata,
                      jQuery.extend(true, {}, mainoptions, {
                          xaxis: { min: ranges.xaxis.from, max: ranges.xaxis.to }
                      }));
        // don't fire event on the overview to prevent eternal loop
        overview.setSelection(ranges, true);
    });
    overviewfig.bind('plotselected', function (event, ranges) {
        main.setSelection(ranges);
    });
    jQuery("#reset").click(function () {
        jQuery.plot(mainfig, plotdata, mainoptions);
        overview.clearSelection();
    });
    mainfig.attr('cubicweb:type','prepared-plot');
    overviewfig.attr('cubicweb:type','prepared-plot');
  }
}

function showTooltip(x, y, contents) {
  $('<div id="tooltip">' + contents + '</div>').css({
    position: 'absolute',
    display: 'none',
    top: y + 5,
    left: x + 5,
    border: '1px solid #fdd',
    padding: '2px',
    'background-color': '#fee',
    opacity: 0.80
  }).appendTo("body").fadeIn(200);
}

var previousPoint = null;
function onTSPlotHover(event, pos, item) {
    if (item) {
        if (previousPoint != item.datapoint) {
            previousPoint = item.datapoint;
            $("#tooltip").remove();
            var x = item.datapoint[0].toFixed(2);
            var y = item.datapoint[1].toFixed(2);
            x = new Date(item.datapoint[0]);
            x = x.strftime("%Y/%m/%d %H:%M");
            showTooltip(item.pageX, item.pageY,
                        item.series.label + ': (' + x + ' ; ' + y + ')');
        }
    } else {
        $("#tooltip").remove();
        previousPoint = null;
    }
}

// /Plot

// data: constant/non-constant switch

// returns the value of the selected element

function granularity_value(granularity_id) {
  var $granularity = cw.jqNode(granularity_id).children();
  for (var i=0; i < $granularity.length; i++) {
    var $elt = $($granularity[i]);
    if ($elt.attr('selected')) {
       return $elt.val();
    }
  }
}

function install_granularity_trigger(granid, nonconstid, constid) {
  var event = $.browser.msie ? 'click' : 'change';
  cw.jqNode(granid).bind(event, function () {
    switch_widget(granid , nonconstid, constid);
  });
}

function switch_widget(granid, nonconstid, constid) {
  if (granularity_value(granid) == 'constant') {
    cw.jqNode(constid).show();
    cw.jqNode(nonconstid).hide();
  } else {
    cw.jqNode(nonconstid).show();
    cw.jqNode(constid).hide();
 }
}

function init_data_widget(granid, nonconstid, constid) {
  // this may amount to not much since the granid is not garanteed
  // to yield an existing dom node
  var $node = cw.jqNode(granid);
  if (!$node) { return; }
  install_granularity_trigger(granid, nonconstid, constid);
  switch_widget(granid, nonconstid, constid);
}

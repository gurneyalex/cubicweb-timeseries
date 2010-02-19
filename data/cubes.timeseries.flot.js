function showTooltip(x, y, contents) {
    $('<div id="tooltip">' + contents + '</div>').css( {
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
            var x = item.datapoint[0].toFixed(2),
                y = item.datapoint[1].toFixed(2);

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
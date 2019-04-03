var $graph_type_dropdown = $('#graph-type-dropdown')
var $rank_column_select = $('#rank-column-select')

$graph_type_dropdown.on('change', function() {
  if (this.value == 'bar-graph') {
    $rank_column_select.show()
  } else {
    $rank_column_select.hide()
  }
}).trigger('change');

$('#builder').queryBuilder({
  plugins: ['bt-tooltip-errors'],

  filters: filters,
});

var frm = $('#selection-form');
frm.submit(function(event) { // catch the form's submit event

  var result = $('#builder').queryBuilder('getRules');
  var column_sel_obj = $('#selection-form').serializeArray()
  var filters_obj = result


  $.ajax({
      type: frm.attr('method'),
      dataType: 'json',
      url: '/benchmark/visualize',
      data: $.param({
        'selection_form': JSON.stringify(column_sel_obj) ,
        'filters': JSON.stringify(filters_obj),
      }),
      success: function (data) {
        $("#graph-view").html(data.graph)
        $("#table-view").html(data.table);
      },
  });
  return false;
});

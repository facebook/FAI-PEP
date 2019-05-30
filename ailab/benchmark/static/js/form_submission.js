$('#builder').queryBuilder({
  plugins: ['bt-tooltip-errors'],
  filters: filters,
  rules: filter_rules,
});

function getUrlVars(href) {
    var vars = {};
    var parts = href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
        vars[key] = value;
    });
    return vars;
}

$('#form-submit').click(function(event) { // catch the form's submit event
  var result = $('#builder').queryBuilder('getRules');
  var column_sel_obj = $('#selection-form').serializeArray()
  var filters_obj = result
  old_url_parts = getUrlVars(window.location.href)
  var new_url_parts = {
    'selection_form': JSON.stringify(column_sel_obj) ,
    'filters': JSON.stringify(filters_obj),
  }
  if (old_url_parts["sort"] != undefined) {
    new_url_parts["sort"] = old_url_parts["sort"]
  }
  var param = $.param(new_url_parts)
  var url = '/benchmark/visualize'
  $.ajax({
      type: 'get',
      dataType: 'json',
      url: url,
      data: param,
      success: function (data) {
        $("#graph-view").html(data.graph)
        $("#table-view").html(data.table)
        window.history.pushState(param, "title", url + "?" + param)
      },
  });
  return false;
});

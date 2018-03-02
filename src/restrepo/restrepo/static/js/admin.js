/* Set the defaults for DataTables initialisation */
$.extend( true, $.fn.dataTable.defaults, {
  "sDom": "<'row-fluid'<'span6'l><'span6'f>r>t<'row-fluid'<'span6'i><'span6'p>>",
  "sPaginationType": "bootstrap",
  "oLanguage": {
    "sLengthMenu": "_MENU_ records per page"
  }
} );

$.extend( true, $.fn.dataTableExt.oApi, {'fnReloadAjax':
    function ( oSettings, sNewSource, fnCallback, bStandingRedraw ) {
        if ( typeof sNewSource != 'undefined' && sNewSource != null ) {
            oSettings.sAjaxSource = sNewSource;
        }

        // Server-side processing should just call fnDraw
        if ( oSettings.oFeatures.bServerSide ) {
            this.fnDraw();
            return;
        }

        this.oApi._fnProcessingDisplay( oSettings, true );
        var that = this;
        var iStart = oSettings._iDisplayStart;
        var aData = [];

        this.oApi._fnServerParams( oSettings, aData );

        oSettings.fnServerData.call( oSettings.oInstance, oSettings.sAjaxSource, aData, function(json) {
            /* Clear the old information from the table */
            that.oApi._fnClearTable( oSettings );

            /* Got the data - add it to the table */
            var aData =  (oSettings.sAjaxDataProp !== "") ?
                that.oApi._fnGetObjectDataFn( oSettings.sAjaxDataProp )( json ) : json;

            for ( var i=0 ; i<aData.length ; i++ )
            {
                that.oApi._fnAddData( oSettings, aData[i] );
            }

            oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();

            if ( typeof bStandingRedraw != 'undefined' && bStandingRedraw === true )
            {
                oSettings._iDisplayStart = iStart;
                that.fnDraw( false );
            }
            else
            {
                that.fnDraw();
            }

            that.oApi._fnProcessingDisplay( oSettings, false );

            /* Callback user function - for event handlers etc */
            if ( typeof fnCallback == 'function' && fnCallback != null )
            {
                fnCallback( oSettings );
            }
        }, oSettings );
    }
});

/* Default class modification */
$.extend( $.fn.dataTableExt.oStdClasses, {
  "sWrapper": "dataTables_wrapper form-inline"
} );

function cleanMainDiv() {
  $('#main').html('');
}

function enableTable(url, columns, after_load) {
  var table = $('#main').html('<table width="100%" class="table table-striped"><thead><tr></tr></thead><tbody></tbody></table>');
  var row = $('tr', table);
  $.each(columns, function(i, col) {
    var el = $('<th></th>').html(col.label);
    row.append(el);
  });
  var table_obj = $('#main table').dataTable( {
      "bProcessing": true,
      "bServerSide": true,
      "sAjaxSource": url,
      "sPaginationType": "bootstrap",
      "oLanguage": {
          "sLengthMenu": "_MENU_/page"
      },
      "fnServerData": function(url, aoData, callback, oSettings) {
          var options = {};
          $.each(aoData, function(i, el){options[el.name] = el.value;});
          var query_options = {};
          if (!/ead/.test(url)) {
            var query_options = {
                'start': options.iDisplayStart,
                'limit': options.iDisplayLength
            };
          }
          // };
          sEcho = options.sEcho;
          if (!/ead/.test(url) && options.iSortCol_0) {
            // EAD don't support paging right now
            query_options['order_by'] = columns[options.iSortCol_0].name;
            if (/scan/.test(url) && options.sSortDir_0=='desc') {
                // only scans support reverse ordering
                query_options['order_by'] = '-' + query_options['order_by'];
            }
          }
          oSettings.jqXHR = jQuery.getJSON(url, query_options, function(json){
              var res = {
                  'iTotalRecords': json.total_results,
                  'iTotalDisplayRecords':json.total_results,
                  'sEcho': sEcho,
                  "aaData": []
              };
              $.each(json.results, function(i, el) {
                  var element = [];
                  $.each(columns, function(i, col) {
                    element.push(el[col.name]);
                  });
                  res.aaData.push(element);
              });
              callback(res);
              if (after_load) {after_load();}
          });
      }
  });
  return table_obj;
}
initialize_main = function() {
  $(document).ready(function() {
    var Appstate = Backbone.Model.extend({
      set: function(attributes, options) {
        Backbone.Model.prototype.set.call(this, attributes, options);
      }
    });
    var appstate = new Appstate();
    var ead_table;
    appstate.on('change', function() {
      var action = arguments[0].get('currentaction');
      var configs = {
      'Logs': function(){
        $('#ead-add-panel').hide();
        enableTable('/log', [
          {label: 'Date', name: 'date'},
          {label: 'Message', name: 'message'},
          {label: 'Type', name: 'object_type'},
          {label: 'ID', name: 'object_id'},
          {label: 'User', name: 'user'}
        ]);
      }, 'Scans': function(){
        $('#ead-add-panel').hide();
        enableTable('/scans', [
          {label: 'ID', name: 'number'},
          {label: 'Position', name: 'sequenceNumber'},
          {label: 'Archive Id', name: 'archive_id'},
          {label: 'Archive File', name: 'archiveFile'}
        ]);
      }, 'EAD': function(){
        $('#ead-add-panel').show();
        function enable_delete_buttons() {
            $('.dataTable tr td:last-child').each(function() {
                var id=$(this).html(), value = id;
                $(this).html(value + ' <a class="btn btn-mini" href="#"><i class="icon-trash"></i></a>');
                $(this).find('a').click(function(){
                    var resp = confirm("Really delete EAD " + value + "?");
                    if (resp) {
                      $.ajax({
                        type: 'delete',
                        url: '/ead/' + value,
                        success: function() {
                          ead_table.fnReloadAjax();
                        }, error: function(jqXHR, textStatus, errorThrown) {
                            var result = JSON.parse(jqXHR.responseText);
                            var messages = [];
                            $(result.errors).each(function() {
                                messages.push(this.description);
                            });
                            alert(messages.join("\n"));
                            if (console) {console.error(textStatus);}
                        }
                      });
                    };
                    return false;
                });
            });
        }
        ead_table = enableTable('/ead', [
          {label: 'status', name: 'status'},
          {label: 'EAD id', name: 'ead_id'}
          // {label: 'DEL', name: 'delete_btn'}
        ], enable_delete_buttons);
      }};
      if (configs[action]) {
        (configs[action])();
        $('#navigation li').removeClass('active');
        $('#navigation li a').filter(function(){
          return this.innerHTML==action;
        }).parent().addClass('active');
      }
    }, appstate);
    $('#navigation a').click(
      function() {
        var action = $(this).text();
        appstate.set('currentaction', action);
        return false;
      }
    );
    // Initial state
    $('#addead').click(
      function() {
        var formData = new FormData($(this).parents('form')[0]);
        $.ajax({
            type: 'POST',
            url: '/ead',
            data: formData,
            cache: false,
            contentType: false,
            processData: false,
            error: function(jqXHR) {
                var result = JSON.parse(jqXHR.responseText);
                var messages = [];
                $(result.errors).each(function() {
                    messages.push(this.description);
                });
                $('#ead-errors').html(messages.join('<br>'));
            },
            success: function(data, textStatus, jqXHR) {
                var result = JSON.parse(jqXHR.responseText);
                $('#ead-errors').html("Added EAD " + result.ead_id);
                ead_table.fnReloadAjax();
            },
            xhr: function() {
                var myXhr = $.ajaxSettings.xhr();
                var progressHandlingFunction = function(progressEvent, upload) {
                    if( progressEvent.lengthComputable) {
                        var percent = Math.round( progressEvent.loaded * 100 / progressEvent.total) + '%';
                        $('#ead-add-panel .bar').width(percent);
                    }
                };
                if(myXhr.upload){
                    myXhr.upload.addEventListener('progress', progressHandlingFunction, false);
                }
                return myXhr;
            }
        });
        return false;
      }
    );
    $('#eadfileinput').change(function(e) {
        if (e.currentTarget.value == '') {
            $('#addead').attr('disabled', 'disabled');
        } else {
            $('#addead').removeAttr('disabled');
        }
    })
    appstate.set('currentaction', 'Scans');
  });
}


initialize_admin_archives = function() {
  $(document).ready(function() {
    archive_list_template = _.template($("#archive_list_template").html());
    update_archive_list();
    $('#action_buttons button.edit').click(function() {
        $('#modal-error-message').html('');
        var record = JSON.parse(unescape($("#archive_list .selected").attr('data-record')));
        var form = $('#edit_overlay form');
        populate_form(record, form);
        $('#edit_overlay').modal();
    });
    $('#edit_overlay .modal-footer .cancel').click(function(){
      $('#edit_overlay').modal('hide');
    });
    $('#edit_overlay .modal-footer .save').click(function(){
      var data = {};
      $($('#edit_overlay form').serializeArray()).each(function() {
        data[this.name] = this.value
      });
      var original_id = data.original_id;
      delete data.original_id;
      delete data.id;
      var id = $('#edit_overlay form input[name=original_id]').val();
      // id is defined only on edit: in the creation form the field is empty and disabled
      var method = id ? 'PUT':'POST';
      var url = id ? '/lists/archives/' + id: '/lists/archives';
      $.ajax({
        type: method,
        url: url,
        data: data,
        success: function() {
          update_archive_list(function() {$('#edit_overlay').modal('hide');})
        }, error: function(jqXHR, textStatus, errorThrown) {
          var messages = [];
          var errors = JSON.parse(jqXHR.responseText).errors;
          $(errors).each(function() {
            messages.push(this.description);
          });
          $('#modal-error-message').html(messages.join('<br>'));
        },
        dataType: 'json'
      });
    });
    $('#delete_confirmation .modal-footer .cancel').click(function(){
      $('#delete_confirmation').modal('hide');
    });
    $('#delete_confirmation .modal-footer .delete').click(function(){
      // XXX using the DOM as state holder is a known anti-pattern
      var id = $('tr[class=selected] td')[0].innerHTML;
      $.ajax({
        type: 'delete',
        url: '/lists/archives/' + id,
        success: function() {
          update_archive_list(function() {$('#delete_confirmation').modal('hide');})
        }, error: function(jqXHR, textStatus, errorThrown) {
          try {
            var data = JSON.parse(jqXHR.responseText);
            var messages = [];
            $(data.errors).each(function() {
              messages.push(this.description);
            });
            $('#modal-delete-error-message').html(messages.join('<br>'));
          } catch(e) {
            $('#modal-delete-error-message').html(jqXHR.responseText);
          }
        },
        dataType: 'json'
      });
    });
    $('#action_buttons button.delete').click(function(){
      $('#modal-delete-error-message').html('');
      $('#delete_confirmation').modal();
    });
    $('#action_buttons button.new').click(function(){
      $('#modal-error-message').html('');
      $('#edit_overlay form')[0].reset();
      $('#edit_overlay').modal();
    });
  });
};

function populate_form(record, form) {
    for (var key in record) {
      if (record.hasOwnProperty(key)) {
        $(form).find('[id=' + key + ']').val(record[key]);
      }
    }
    $(form).find('[name=original_id]').val(record.id);
}

update_archive_list = function(callback) {
    $.ajax('/lists/archives', {success: function(data, textStatus, jqXHR) {
        var rendered_table = archive_list_template({items:data.results});
        $("#archive_list").html(rendered_table);
        $("#archive_list table").click(function(e) {
            var row = $(e.target).parent();
            var record = JSON.parse(unescape(row.attr('data-record')));
            row.siblings().css('outline', '')
            row.css('outline', 'dotted red');
            row.addClass('selected');
            row.siblings().removeClass('selected');
            $('#action_buttons button').removeAttr('disabled');
        });
        $('#action_buttons button.edit').attr('disabled', 'disabled');
        $('#action_buttons button.delete').attr('disabled', 'disabled');
        if (callback) {callback();}
    }});
};

archive_list_template =  _.template("<b><%- value %></b>");

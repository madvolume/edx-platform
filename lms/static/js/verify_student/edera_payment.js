function showSubmissionError() {
    if (xhr.status == 400) {
        $('#order-error .copy p').html(xhr.responseText);
    }
    $('#order-error').show();
    $("html, body").animate({ scrollTop: 0 });
}

function submitForm(data) {
    for (prop in data) {
    $('<input>').attr({
        type: 'hidden',
        name: prop,
        value: data[prop]
    }).appendTo('#pay_form');
    }
    $("#pay_form").submit();
}

function refereshPageMessage() {
    $('#photo-error').show();
    $("html, body").animate({ scrollTop: 0 });
}

var submitToPaymentProcessing = function() {
  $("#pay_button").addClass('is-disabled').attr('aria-disabled', true);
  var contribution_input = $("input[name='contribution']:checked")
  var contribution = 0;
  contribution = $(".chosen-price").data("price");

  var course_id = $("input[name='course_id']").val();
  $.ajax({
    url: "/verify_student/create_order",
    type: 'POST',
    data: {
      "course_id" : course_id,
      "contribution": contribution
    },
    success:function(data) {
      if (data.success) {
        submitForm(data);
      } else {
        refereshPageMessage();
      }
    },
    error:function(xhr,status,error) {
      $("#pay_button").removeClass('is-disabled').attr('aria-disabled', false);
      showSubmissionError()
    }
  });
}

function doResetButton(resetButton, captureButton, approveButton, nextButtonNav, nextLink) {
  approveButton.removeClass('approved');
  nextButtonNav.addClass('is-not-ready');
  nextLink.attr('href', "#");

  captureButton.show();
  resetButton.hide();
  approveButton.hide();
}

function doApproveButton(approveButton, nextButtonNav, nextLink) {
  nextButtonNav.removeClass('is-not-ready');
  approveButton.addClass('approved');
  nextLink.attr('href', "#next");
}

function doSnapshotButton(captureButton, resetButton, approveButton) {
  captureButton.hide();
  resetButton.show();
  approveButton.show();
}

function handleEvents() {
    //OTHER
    $("[name=contribution-other-amt]").change(function () {
        $("[name=contribution]#contribution-other").prop("checked", true).val($(this).val()).change();
    });
    $("[name=contribution]").change(function () {
        var val;

        val = $(this).val();
        $(".chosen-price").text(val).data("price", val);
    });
}

$(document).ready(function() {
  $(".carousel-nav").addClass('sr');
  handleEvents();
  $("#pay_button").click(function(){
      analytics.pageview("Payment Form");
      submitToPaymentProcessing();
  });

  $('a[rel="external"]').attr({
    title: gettext('This link will open in a new browser window/tab'),
    target: '_blank'
  });
});

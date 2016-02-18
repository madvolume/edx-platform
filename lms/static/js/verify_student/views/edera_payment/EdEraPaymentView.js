;
(function (define, undefined) {
  'use strict';
  define([
    "backbone",
    "jquery",
    "underscore",
    "js/verify_student/views/edera_payment/EdEraContributionView",
    "js/verify_student/templates/EdEraPaymentTemplate"
  ], function (Backbone, $, _, EdEraContributionView, EdEraPaymentTemplate) {
    return Backbone.View.extend({
      /**
       * @overrides
       */
      template: EdEraPaymentTemplate,
      /**
       * @overrides
       */
      events: {
        "click #pay_button": "_onClickPayButton"
      },
      /**
       * @private
       */
      _onClickPayButton: function () {
        this.submitToPaymentProcessing();
      },
      /**
       * Submits data to payment processing
       */
      submitToPaymentProcessing: function() {
        var contribution, course_id;

        this.$("#pay_button").addClass('is-disabled').attr('aria-disabled', true);

        contribution = this.model.get("chosen_price");
        course_id = this.model.get("course_id");
        $.ajax({
          url: "/verify_student/create_order",
          type: 'POST',
          data: {
            "course_id" : course_id,
            "contribution": contribution
          },
          success: _.bind(function(data) {
            if (data.success) {
              this.submitForm(data);
            }
          }, this),
          error: _.bind(function(xhr,status,error) {
            this.$("#pay_button").removeClass('is-disabled').attr('aria-disabled', false);
          }, this)
        });
      },
      submitForm: function (data) {
        var prop;

        for (prop in data) {
          $('<input>').attr({
            type: 'hidden',
            name: prop,
            value: data[prop]
          }).appendTo('#pay_form');
        }
        $("#pay_form").submit();
      },
      /**
       * @overrides
       */
      initialize: function (options) {
        this.model = options.model;
      },
      /**
       * @overrides
       */
      render: function () {
        var contributionView;

        this.$el.html(this.template(this.model.toJSON()));
        contributionView = new EdEraContributionView({
          model: this.model,
          el: this.$(".contribution")
        });
        contributionView.render();
      }
    });
  });
}).call(this, define || RequireJS.define);
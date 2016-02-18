;
(function (define, undefined) {
  'use strict';
  define([
    "backbone",
    "jquery",
    "underscore",
    "js/verify_student/templates/EdEraContributionButtonTemplate"
  ], function (Backbone, $, _, EdEraContributionButtonTemplate) {
    return Backbone.View.extend({
      /**
       * @overrides
       */
      template: EdEraContributionButtonTemplate,
      className: "contribution-button-wrapper",
      events: {
        "change input": "_onChangeInput",
        "click .contribution-button": "_onClickMe"
      },
      _onChangeInput: function (ev) {
        this.model.set("price", $(ev.currentTarget).val());
        this.trigger("change", this);
      },
      _onClickMe: function () {
        this.trigger("change", this);
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
        this.$el.html(this.template(this.model.toJSON()));
      }
    });
  });
}).call(this, define || RequireJS.define);
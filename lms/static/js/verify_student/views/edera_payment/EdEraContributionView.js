;
(function (define, undefined) {
  'use strict';
  define([
    "backbone",
    "jquery",
    "underscore",
    "js/verify_student/enums/contributions",
    "js/verify_student/views/edera_payment/EdEraContributionButtonView",
    "js/verify_student/templates/EdEraContributionTemplate"
  ], function (Backbone, $, _, contributions, EdEraContributionButtonView, EdEraContributionTemplate) {
    return Backbone.View.extend({
      /**
       * @overrides
       */
      template: EdEraContributionTemplate,
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
        var suggested_prices, contributionsCollection;

        this.$el.html(this.template(this.model.toJSON()));
        suggested_prices = this.model.get("suggested_prices");
        contributionsCollection = new Backbone.Collection([
          {
            price: suggested_prices[0],
            text: contributions.firstContributionText,
            active: true,
            selectable: false
          },
          {
            price: suggested_prices[1],
            text: contributions.secondContributionText,
            active: false,
            selectable: false
          },
          {
            price: this.model.get("min_price"),
            text: contributions.thirdContributionText,
            active: false,
            selectable: true
          }
        ]);
        contributionsCollection.each(function (model) {
          var contributionButtonView;

          contributionButtonView = new EdEraContributionButtonView({
            model: model
          });
          this.listenTo(contributionButtonView, "change", this._onChangeContributionButton);
          this.$(".contributions-row").append(contributionButtonView.$el);
          contributionButtonView.render();
        }, this);
      },
      /**
       * @private
       */
      _onChangeContributionButton: function (view) {
        this.model.set("chosen_price", view.model.get("price"));
        this.updateDecisionPrice();
        this.$(".contribution-button").removeClass("active");
        view.$(".contribution-button").addClass("active");
      },
      /**
       *
       */
      updateDecisionPrice: function () {
        var price;

        price = this.model.get("chosen_price");
        this.$(".chosen_price").data("chosen_price", price).text(price);
      }
    });
  });
}).call(this, define || RequireJS.define);
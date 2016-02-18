;
(function (define, undefined) {
    define(["underscore"], function (_) {
        var html, input, span;

        input = '<input type="number" min="<%=price%>" value="<%=price%>"/>';
        span = '<span><%=price%></span>';

        html = '<div class="contribution-button <%if (active) {%>active<%}%>" data-price=<%=price%>>' +
                    '<div class="contribution-price">'                          +
                        '<% if (selectable) { %>' + input + '<% } else { %>' + span + '<% } %>' + '</div>' +
                    '<div class="contribution-description"><%=text%></div>' +

                '</div>';

        return _.template(html);
    });
}).call(this, define || RequireJS.define);
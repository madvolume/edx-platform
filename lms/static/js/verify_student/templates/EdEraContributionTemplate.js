;
(function (define, undefined) {
    define(["underscore"], function (_) {
        var html, decision, free, mailLink;

        decision = '<div class="decision">Ви вирішили оплатити <span class="chosen_price" data-chosen="<%=chosen_price%>"><%=chosen_price%></span> грн.</div>';

        mailLink = '<a target="_blank" href="mailto:info@ed-era.com?subject=Мотиваційний лист для запису на <%=course_name%>&body=Мотиваційний лист від <%=user_full_name%>">' +
                     'Надішліть нам мотиваційний лист' +
                    '</a>'

        free = '<div class="free">' +
        'З огляду на різні ситуації, які можуть траплятися у житті, та на події в країні, ми надаємо можливість <strong>безкоштовного навчання</strong>. ' +
        'Таке право мають передусім громадяни пільгових категорії та переселенці з зони АТО. ' +
         mailLink +', у якому опишіть свою ситуацію, та додайте до нього відповідні документи, якщо це можливо.' +
        '</div>';

        html = '<div class="contributions-row"></div>' +
                free +
                decision;

        return _.template(html);
    });
}).call(this, define || RequireJS.define);
$(document).ready(function() {

  // for each trigger
  $('.trigger').each(function() {

    // check if cookie has value on true
    if ($.cookie($(this).parent().prop('id')) == "true") {
      // add displayed class and show the content
      $(this).parent().addClass("displayed");
      $(this).next('.content').show();

    } else {
      // remove displayed class and hide the content
      $(this).parent().removeClass("displayed");
      $(this).next('.content').hide();
    }
  });

  // if user clicked trigger element
  $('.trigger').click(function() {

    // toggle parent's class and animate the content
    $(this).parent().toggleClass('displayed');
    $(this).next('.content').slideToggle("fast");

    // save the state to cookies
    var parent_id =
    $.cookie($(this).parent().prop('id'),
             $(this).parent().hasClass('displayed'),
             { path: '/' });
  });
});

/*
  This function will search for all classes matching all IDs which are under
  #admonition_selector element and display/hide their content.

  State is saved in cookies so user doesn't lose his settings after page
  reload or changing pages.

  To make this feature work, you need to:
  - add checkbox to _templates/layout.html file with proper ID
  - in admonitions use proper class which matches above mentioned ID
*/



// after document is loaded
$(document).ready(function() {

    // for each checkbox in #admonition_selector do
    $('#admonition_selector :checkbox').each(function() {

      // check value of cookies and set state to the related element
      if ($.cookie($(this).attr("id")) == "true") {
        $(this).prop("checked", true);
      } else if (($.cookie($(this).attr("id")) == "false")) {
        $(this).prop("checked", false);
      }

      // show/hide elements after page loaded
      toggle_admonition($(this).attr("id"));
    });

    // when user clicks on the checkbox, react
    $('#admonition_selector :checkbox').change(function() {

        // show/hide related elements
        toggle_admonition($(this).attr("id"));

        // save the state in the cookies
        $.cookie($(this).attr("id"), $(this).is(':checked'), { path: '/' });
    });
});


// function to show/hide elements based on checkbox state
// checkbox has ID and it toggles elements having class named same way as the ID
function toggle_admonition(admonition) {

  // for each element having class as the checkbox's ID
  $(".admonition." + admonition).each(function() {

    // set show/hide
    if($("#" + admonition).is(':checked')) {
      $(this).show();
    } else {
      $(this).hide();
    }
  });
}

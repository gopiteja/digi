// reset builder

$('.reset').on('click', function() {
    var target = $(this).data('target');

    $('#builder-'+target).queryBuilder('reset');
});

// set rules
$('.set-json').on('click', function() {
    var target = $(this).data('target');
    var rules = window['rules_'+target];

    $('#builder-'+target).queryBuilder('setRules', rules);
});

// get rules
$('.parse-json').on('click', function() {
    var target = 'basic';
    var result = $('#builder-'+target).queryBuilder('getRules');

    if (!$.isEmptyObject(result)) {
        selectedCell = localStorage.getItem('selected')
        obj = localStorage.getItem('ruleBox') == undefined ? {} : JSON.parse(localStorage.getItem('ruleBox'));
        result['valid'] = result['valid'].toString()
        obj[selectedCell] = result;
        localStorage.setItem('ruleBox', JSON.stringify(obj))
    }
    else {

    }
});


function format4popup(object) {
    return JSON.stringify(object, null, 2).replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

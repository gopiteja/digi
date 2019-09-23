var case_id = getUrlParameter('case_id');
var testData;
var table_rows=[];
var table_s=[];
var table_cols=[];
var cell_id_selected_t={};
var no_table_ruleid=false;
// var decision_display = {}
function getUrlParameter(sParam) {
    var sPageURL = window.location.search.substring(1),
    sURLVariables = sPageURL.split('&'),
    sParameterName,
    i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
        }
    }
}

originUrl = window.location.origin.split(':');

dynamicUrl = originUrl[0] + ":" + originUrl[1] + ":5002";
// dynamicUrl = "http://3.89.199.59:5002"

o = {};
o.case_id = case_id;
// o.case_id='TX05D5ABAD03791';
input = []
trace = []
testData = {}

var settings11 = {
    "async": true,
    "crossDomain": true,
    "url": dynamicUrl+"/show_decision_tree",
    "method": "POST",
    "processData": false,
    "contentType": "application/json",
    "data": JSON.stringify(o)
};
$(".loading_full").show();
$.ajax(settings11).done(function (msg) {
    $(".loading_full").hide();
    if ($.type(msg) == 'string') {
        $.alert('Something went wrong', 'Alert')
    }
    else {
        inputConverter(msg)
    }
});

// inputConverter(input_data)


function inputConverter(dt){
    input = dt['data'];
    trace = dt['trace'];
    testData = dt['testData'];
    // testData = {
    //     "14": {
    //         "output": true,
    //         "description": "some random text to be displayed here",
    //         "input": [
    //             {
    //                 "table": "Table Name",
    //                 "column": "Coulmn Name",
    //                 "value": "Value"
    //             },
    //             {
    //                 "table": "Table Name",
    //                 "column": "Coulmn Name",
    //                 "value": "Value"
    //             }
    //         ]
    //     }
    // }
    // decision_display = dt['testData'];

    links = [];
    nodes = [];
    var end_id = '';
    //console.log(input,trace,"odfsfgsd")
    for (var i = 0; i < input.length; i++) {
        // node generation
        obj = {}
        obj.id = input[i].rule_id
        obj.attrs = {};
        obj.size= {
            width: 150,
            height: 70
        }
        obj.attrs.body = {
            fill: "transparent",
            rx: 2,
            ry: 2,
            width: 50,
            height: 30,
            strokeDasharray: "0",
            strokeWidth:1,
            ruleCheck: input[i].rule_string
        }
        if (trace.indexOf(input[i].rule_id) > -1) {
            obj.attrs.body.stroke = "#0089FF";
            obj.attrs.body.strokeWidth=2
            //console.log(obj);
        }
        else {
            obj.attrs.body.stroke = "#d6d6d6"
            obj.attrs.body.strokeWidth=1
        }
        if (input[i].next_if_sucess == input[i].next_if_failure) {
            obj.type = "standard.Rectangle";
            if (input[i].next_if_sucess != 'END') {
                obj_l = {}
                x1 = trace.indexOf(input[i].next_if_sucess);
                x2 = trace.indexOf(input[i].rule_id);
                if (x1 > -1 && x2 > -1 && x1-x2 >= -1 && x1-x2 <= 1) {
                    obj_l.attrs = {"line": {"stroke": "#0089FF","stroke-width": 2}}
                }
                else {
                    obj_l.attrs = {"line": {"stroke": "#d6d6d6","stroke-width": 1}}
                }
                obj_l.connector = {name: "rounded"}
                obj_l.id = "l-"+input[i].rule_id
                obj_l.labels = [{"attrs": {"text":{"text": 'True', "fill": "#999999"}, "rect": {"stroke": "#d6d6d6"}}}]
                obj_l.router = {name: "normal"}
                obj_l.source = {id: input[i].rule_id}
                obj_l.target = {id: input[i].next_if_sucess}
                obj_l.type = "app.Link"
                links.push(obj_l)
            }
        }
        else {
            obj.type = "standard.Polygon"
            obj.attrs.body.refPoints = "50,0 100,50 50,100 0,50";

            if (input[i].next_if_sucess != 'END') {
                obj_l = {}
                x1 = trace.indexOf(input[i].next_if_sucess);
                x2 = trace.indexOf(input[i].rule_id);
                if (x1 > -1 && x2 > -1 && x1-x2 >= -1 && x1-x2 <= 1) {
                    obj_l.attrs = {"line": {"stroke": "#0089FF","stroke-width": 2}}
                }
                else {
                    obj_l.attrs = {"line": {"stroke": "#d6d6d6","stroke-width": 1}}
                }
                obj_l.connector = {name: "rounded"}
                obj_l.id = "l-"+input[i].rule_id
                obj_l.labels = [{"attrs": {"text":{"text": 'True', "fill": "#999999"}, "rect": {"stroke": "#d6d6d6"}}}]
                obj_l.router = {name: "normal"}
                obj_l.source = {id: input[i].rule_id}
                obj_l.target = {id: input[i].next_if_sucess}
                obj_l.type = "app.Link"
                links.push(obj_l)
            }

            if (input[i].next_if_failure != 'END') {
                obj_l = {}
                x1 = trace.indexOf(input[i].next_if_failure);
                x2 = trace.indexOf(input[i].rule_id);
                if (x1 > -1 && x2 > -1 && x1-x2 >= -1 && x1-x2 <= 1) {
                    obj_l.attrs = {"line": {"stroke": "#0089FF","stroke-width": 2}}
                }
                else {
                    obj_l.attrs = {"line": {"stroke": "#d6d6d6","stroke-width": 1}}
                }
                obj_l.connector = {name: "rounded"}
                obj_l.id = "l-"+input[i].id+"-"+input[i].rule_id
                obj_l.labels = [{"attrs": {"text":{"text": 'False', "fill": "#999999"}, "rect": {"stroke": "#d6d6d6"}}}]
                obj_l.router = {name: "normal"}
                obj_l.source = {id: input[i].rule_id}
                obj_l.target = {id: input[i].next_if_failure}
                obj_l.type = "app.Link"
                links.push(obj_l)
            }
        }
        obj.attrs.label = {
            fontSize: 11,
            fill: "#333333",
            text: input[i].rule_name,
            fontFamily: "Roboto Condensed",
            fontWeight: "Normal",
            strokeWidth: 0

        };
        obj.attrs.root = {
            dataTooltipPosition: "left",
            dataTooltipPositionSelector: ".joint-stencil"
        };

        if (input[i].next_if_sucess == 'END') {
            obj = {}
            obj.attrs = {
                body: {
                    fill: "transparent",
                    height: 30,
                    strokeDasharray: "0",
                    strokeWidth:0,
                    width: 50
                },
                label: {
                    fill: "#333333",
                    fontFamily: "Roboto Condensed",
                    fontSize: 11,
                    fontWeight: "Normal",
                    strokeWidth: 0,
                    text: input[i].rule_name
                }
            };

            if (trace.indexOf(input[i].rule_id) > -1) {
                obj.attrs.body.stroke = "#0089FF";
                obj.attrs.body.strokeWidth = "2";
                //console.log(obj);
            }
            else {
                obj.attrs.body.stroke = "#d6d6d6";
                obj.attrs.body.strokeWidth = "1";
            }
            obj.root = {dataTooltipPosition: "left", dataTooltipPositionSelector: ".joint-stencil"};
            obj.id =  input[i].rule_id;
            obj.size =  {width: 90, height: 54};
            obj.type =  "standard.Ellipse";
        }

        nodes.push(obj)
    }

    if (end_id != '') {

        nodes.push(obj)
    }

    for (var i = 0; i < links.length; i++) {
        nodes.push(links[i])
    }
    //console.log('nodes',nodes)
    runApp(nodes)


}

function runApp(cells) {

    joint.setTheme('modern');
    app = new App.MainView({ el: '#app' });

    //console.log(App.config)
    themePicker = new App.ThemePicker({ mainView: app });
    themePicker.render().$el.appendTo(document.body);

    // window.addEventListener('load', function() {
    //console.log(cells,'ceslsdlfsl')
    app.graph.fromJSON({"cells": cells});
    // });

    setTimeout(function(){
        joint.layout.DirectedGraph.layout(app.graph, {
            setLinkVertices: true,
            rankDir: 'TB',
            marginX: 100,
            marginY: 100
        });
        app.paperScroller.scroll(900,300)
        // app.paperScroller.center();
        // app.paperScroller.centerContent();
    },500)
}

function TableDataConverter(table_obj,rule_id){
}

function displayCellData(cell_id) {
    console.log(cell_id);
    ic = ''
    if(testData[cell_id]){
        node_data = testData[cell_id];

        ic += '<p><span>Output:</span> '+node_data['output']+'</p>';
        ic += '<p><span>Description:</span> '+node_data['description']+'</p>';

        ic += '<div class=forTable><span>Input:</span><div class="widthFull">' + generateTable(node_data['input']) + '</div></div>'

    }
    $(".inspector-container").html(ic);
}


function generateTable(table) {
    cols = Object.keys(table[0])
    th = '<tr>'
    for (var i = 0; i < cols.length; i++) {
        console.log(cols[i]);
        th += '<th>' + cols[i] + '</th>'
    }
    th += '</tr>'

    td = ''
    for (var i = 0; i < table.length; i++) {
        td += '<tr>'
        for (var j = 0; j < cols.length; j++) {
            td += '<td>' + table[i][cols[j]] + '</td>'
        }
        td += '</tr>'
    }

    return '<table class="table_name">' + th + td + '</table>'
}

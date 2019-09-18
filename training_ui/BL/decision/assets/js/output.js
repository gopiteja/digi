function outputConverter(output) {
    console.log(output);
    lines = [];
    nodes = [];
    for (var i = 0; i < output.length; i++) {
        if (output[i].type == 'app.Link') {
            lines.push(output[i])
        }
        else {
            obj = {};
            obj.id = i;
            obj.rule_string = output[i].attrs.body.ruleCheck == undefined ? "" : output[i].attrs.body.ruleCheck;
            obj.type = output[i].type == 'standard.Polygon' ? 'condition' : 'sequence'
            obj.rule_id = output[i].id;
            obj.group = 'chain';
            obj.stage = output[i].attrs.label.text;
            if (output[i].type == 'standard.Ellipse') {
                obj.next_if_failure = 'END';
                obj.next_if_sucess = 'END';
            }
            nodes.push(obj)
        }
    }

    for (var i = 0; i < lines.length; i++) {
        id = lines[i].source.id;
        target = lines[i].target.id;
        type = lines[i].labels[0].attrs.text.text;
        idx = nodes.findIndex(x => x.rule_id===id.toString());

        if (nodes[idx].type == 'condition') {
            if (type == 'False') {
                nodes[idx]['next_if_failure'] = target
            }
            else {
                nodes[idx]['next_if_sucess'] = target
            }
        }
        else {
            nodes[idx]['next_if_failure'] = target
            nodes[idx]['next_if_sucess'] = target
        }
    }

    console.log(nodes);
}

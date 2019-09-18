$(document).ready(function () {
    originUrl = window.location.origin.split(':');
    $('.selectClass').show();
    dynamicUrl = originUrl[0]+":"+originUrl[1]+":5002";

    fieldSplits = 0;

    // dynamicUrl = 'http://8c6bae87.ngrok.io'

    console.log(originUrl)
    logThis(2, dynamicUrl)

    var extraTrainingFields = {}

    var trained_table = {}
    var nextClicked = false;
    var footerData;

    var tableCount = 0;

    var default_Output_fields = ["PO Number","Table.Base Amount","Table.Invoice Total", "Invoice Number", "Invoice Date", "Invoice Total","SGST/CGST Amount","Invoice Base Amount","Table.GST Percentage","IGST Amount","DRL GSTIN","Vendor GSTIN","Billed To (DRL Name)","DC Number","Document Heading","Table.HSN/SAC","Table.Product description","GST Percentage","HSN/SAC","Table.Quantity","Table.Rate","Table.Gross Amount","Table.CGST Percentage","Table.SGST Percentage", "Table.SGST/CGST Amount","Table.CGST Amount","Table.SGST Amount","Table.IGST Percentage","Table.IGST Amount","Vendor Name","Table.PO Number", "GRN Number", "Service Entry Number"]

    var headerCropAreas = {}, vendor_crop_data={}, tableCrops = {};
    var tableFinalCrops = {};
    var all_cropped_data_history = {};
    var mainAreasCount=[];
    var already_selected = {};
    var initial_training_arr = ["header_ocr", "address_ocr", "footer_ocr"];

    var last_selected = 'header';
    var alt_title = 'header';

    var mainDataToSend = {};
    var final_table_save = {}
    var img_ocr_data;
    var final_arr = {}
    var selectedOption;

    var list_json = [
        "SBP","SEZ",
        "Sample PO",
        "Imports",
        "Fastrack",
        "Coal",
        "Job Work",
        "CHA",
        "Freight",
        "Transport",
        "Receipts",
        "cab invoices",
        "Thomas Cook Credit notes",
        "Clay/Matrix bills",
        "Conference Invoices-NONPO",
        "FIT invoices",
        "Guest house related invoices"
    ]

    var retrainedData = {}

    var retrainedTable = {}


    // var vendor_name_field = '<div class="col-sm-12"><div class="outputBody"><div class="row" style="margin:0px !important"><div class="col-sm-6"><input class="mods_inputs" value="Vendor Name" readonly=""></div><div class="col-sm-6" style="padding: 0px;"><input class="mods_inputs vendor_name_Val" list="vendor_name" placeholder="Give the Vendor name"></div></div></div></div>';

    var file_id = getUrlParameter('file_name');
    // file_id.option = selectedOption;
    var case_id = getUrlParameter('case_id');
    var retrain = getUrlParameter('retrain');

    var template_name_retrain;

    retrain = nullCheck(retrain) ? retrain : "no"

    case_id = case_id.split('.')[0];

    file_name = 'images/invoices/'+file_id;
    var stepper = document.querySelector('.stepper');
    var stepperInstace = new MStepper(stepper, {
        // options
        firstActive: 0, // this is the default
        // Allow navigation by clicking on the next and previous steps on linear steppers.
        linearStepsNavigation: false,
        // Enable or disable navigation by clicking on step-titles
        stepTitleNavigation: false,
        // Preloader used when step is waiting for feedback function. If not defined, Materializecss spinner-blue-only will be used.
        feedbackPreloader: '<div class="spinner-layer spinner-blue-only">...</div>'
    })
    if (nullCheck(file_name)) {
        sendObj = {};
        sendObj.file_name = file_id;
        sendObj.case_id = case_id;
        sendObj.retrain = retrain;

        console.log(sendObj);

        var form = new FormData();
        form.append("file", JSON.stringify(sendObj));
        var settings11 = {
            "async": true,
            "crossDomain": true,
            "url": dynamicUrl+"/get_ocr_data",
            "method": "POST",
            "processData": false,
            "contentType": "application/json",
            "data": JSON.stringify(sendObj)
        };
        $.ajax(settings11).done(function (msg) {
            console.log(msg);
            if (msg.flag) {

                if(nullCheck(msg.info)){
                    retrainedData = msg.info.fields;
                    retrainedTable = msg.info.table;
                    template_name_retrain = msg.template_name;
                }
                // if (nullCheck(msg.fields)) {
                //     default_Output_fields = msg.fields;
                // }
                console.log(default_Output_fields);
                img_ocr_data = msg.data;
                // localStorage.setItem('ocr', JSON.stringify(img_ocr_data))
                check_file = file_name.substr(file_name.length - 5)
                logThis(6, [file_name,check_file]);
                if (check_file.toLowerCase().indexOf('.pdf') > -1) {
                    logThis(8, "Its a PDF file")
                    previewPdfFile(file_name)
                }
                else if (check_file.toLowerCase().indexOf('.tiff') > -1 || check_file.toLowerCase().indexOf('.tif') > -1) {
                    logThis(8, "Its a TIFF file")
                    previewTiffFile(file_name)
                }
                else if (check_file.toLowerCase().indexOf('.jpg') > -1 || check_file.toLowerCase().indexOf('.jpeg') > -1 || check_file.toLowerCase().indexOf('.png') > -1) {
                    logThis(8, "Its a Image file")
                    displayImage([file_name])
                }
                else {
                    logThis(8, "It is not a image file")
                }
            }
            else {

            }
        })
    }

    function displayImage(imagefiles) {
        inital_ct = 0;
        img__ = ''
        //here need to get all data like OCR from database
        for (var i = 0; i < imagefiles.length; i++) {
            img__ += '<img src="'+imagefiles[i]+'" id="imageCountNum'+i+'" class="imageCount imageCountNum'+i+'" alt="'+i+'"  width="100%">';
        }
        $(".showImgs").html(img__)

        for (var i = 0; i < imagefiles.length; i++) {
            width_ = $(".imagesCountNum"+i).width();
            $("#imageCountNum"+i).selectAreas({
                onChanged: debugHeaderAreas,
                width: width_,
                maxAreas:3
            });
        }
    }

    var tableCrops

    debugHeaderAreas = function debugHeaderAreas (event, id, areas) {
        console.log(areas)
        target = event.target.alt;
        nofiles = $(".imageCount").length;
        a = 0;
        if (!nullCheck(nextClicked)) {
            if (alt_title == 'header') {
                headerCropAreas[target] = areas;
                for (var i = 0; i < nofiles; i++) {
                    if (nullCheck(headerCropAreas[i])) {
                        a = a + headerCropAreas[i].length;
                    }
                }
                b = $(".getcropvendor").length;
                if ((a > b || a==b) && nullCheck(areas)) {
                    area_indx = areas.findIndex(x => x.id==id);
                    areas[area_indx].page = target;
                    rteData = rte(areas[area_indx], $("#imageCountNum0").width());

                    console.log(rteData);
                    // rteData = rte();
                    text = '';
                    for (var i = 0; i < rteData.length; i++) {
                        text = text +' '+ rteData[i].word;
                    }
                    text_= $.trim(text);
                    vendor_crop_data[initial_training_arr[inital_ct]] = {};
                    vendor_crop_data[initial_training_arr[inital_ct]].page = target;
                    vendor_crop_data[initial_training_arr[inital_ct]].value = text_;
                    vendor_crop_data[initial_training_arr[inital_ct]].keyword = "";
                    vendor_crop_data[initial_training_arr[inital_ct]].validation = {"pattern":"NONE","globalCheck":false};
                    vendor_crop_data[initial_training_arr[inital_ct]].coordinates = areas[area_indx];
                    vendor_crop_data[initial_training_arr[inital_ct]].width = $("#imageCountNum0").width();
                    console.log(vendor_crop_data);

                    if ($('.vndr-'+id+'-'+target).length == 0) {
                        ht = '<div class="row pos_rl vndr-'+id+'-'+target+'">'
                        ht += '<div>'
                        ht += '<div class="input-field col s11 mr-b-0">'
                        ht += '<select class="mods_inputs getcropvendor getcropvendor-'+id+'-'+target+'" key="'+id+'" target="'+target+'" style="margin-bottom: 20px;">'
                        ht += '<option value="" disabled selected>Select Crop</option>'
                        ht += '<option value="header_ocr">Header</option>'
                        ht += '<option value="address_ocr">Address</option>'
                        ht += '<option value="footer_ocr">Footer</option>'
                        ht += '</select>'
                        ht += '<div class="clear___"></div>'
                        ht += '</div>'
                        ht += '<label class="displayHeaderText headerText-'+id+'-'+target+'"></label>'
                        ht += '</div>'
                        // ht += '<div class="input-field col s1">'
                        // ht += '<img typ="vndr" class="delete_crop_field" src="images/trash.svg" width="17px" id="'+id+'" target="'+target+'">'
                        // ht += '</div>'
                        ht += '</div>'
                        $(".vendorValidation").append(ht);
                        $('.getcropvendor-'+id+'-'+target).val(initial_training_arr[inital_ct]);

                        inital_ct += 1;
                    }
                    $('.headerText-'+id+'-'+target).html(text_);
                }
                else if ((a < b)  && nullCheck(areas)) {
                    $(".vndr-"+id+"-"+target).remove();
                    vendor_crop_data[initial_training_arr[inital_ct]] = {};
                    inital_ct = inital_ct - 1;
                }
            }
            else if (alt_title == 'field' || alt_title == 'fieldmap') {
                if (alt_title == 'field') {
                    class_name_field = 'displayresults';
                    valid_options = '<option value="NONE">Select Validation</option><option value="Remove Junk">Remove Junk</option>';
                    // for (var i = 0; i < validationsArr.length; i++) {
                    //     if (validationsArr[i] != 'NONE') {
                    //         valid_options = valid_options + '<option value="'+validationsArr[i]+'">'+validationsArr[i]+'</option>'
                    //     }
                    // }

                    validation_select = '<select key="'+id+'" target="'+target+'" class="mods_inputs validationLabel validationLabel-'+id+'-'+target+'">'+valid_options+'</select>'

                }
                else {
                    class_name_field = 'field_map_rows';
                    field_opts = '<option value="">Select Type</option>'
                    field_opts = '<option value="kh_vh">Key, Values in Header</option>'
                    field_opts += '<option value="kh_vc">Key in Header, Value in Column</option>'
                    validation_select = '<select class="label_inputs mr-b-0 validationtype-'+id+'-'+target+'">'+field_opts+'</select>'
                }

                box_id = id+"-"+target;
                arrCount = $(".fieldTrain").length;
                mainAreasCount[target] = areas;
                for (var i = 0; i < mainAreasCount.length; i++) {
                    if (!nullCheck(mainAreasCount[i])) {
                        mainAreasCount[i] = [];
                    }
                    a += mainAreasCount[i].length
                }
                if (arrCount < a) {
                    console.log(default_Output_fields);
                    default_op_optns = '<option value="">Select Field</option>'

                    for (var i = 0; i < default_Output_fields.length; i++) {
                        // if (default_Output_fields[i][1] == selectedFile[14] || default_Output_fields[i][1] == 'All') {
                        //     default_op_optns = default_op_optns + '<option value="'+default_Output_fields[i][0]+'">'+default_Output_fields[i][0]+'</option>';
                        // else {
                        if (default_Output_fields[i].indexOf('Table.') == -1) {
                            if (Object.values(already_selected).indexOf(default_Output_fields[i][0]) == -1) {
                                default_op_optns = default_op_optns + '<option value="'+default_Output_fields[i]+'">'+default_Output_fields[i]+'</option>';
                            }
                        }
                        // }
                        // }
                    }
                    // <select class="mods_inputs keyword-'+id+'-'+target+'"></select>

                    tr = '<div class="col-sm-12 fieldTrain recd-'+id+'-'+target+'" id="'+id+'" split="no" target="'+target+'" ty="new">'
                    tr += '<div class="outputBody">'
                    tr += '<div class="row fieldValid-'+id+'-'+target+'" style="border-bottom: 1px solid #c9c9c9;height: 30px !important;">'
                    tr += '<div class="col-sm-6 padding0">'
                    tr += '<select class="mods_inputs keywordSelect keyword-'+id+'-'+target+'">'+default_op_optns+'</select>'
                    tr += '</div>'
                    tr += '<div class="col-sm-6 padding0"> '+validation_select+' </div>'
                    tr += '</div>'
                    tr += '<div class="parent_main parent_main-'+id+'-'+target+'" style="height: 31px;">'
                    tr += '<input type="text" class="inputLabel inputLabel-'+id+'-'+target+' hideInput" value="">'
                    tr += '<div class="parent_input_here parent_input_here-'+id+'-'+target+'"></div>'
                    tr += '<div class="drag drag-'+id+'-'+target+'" key="'+id+'" target="'+target+'">'
                    tr += '<div class="triangle-down"></div>'
                    tr += '<div class="triangle-up"></div>'
                    tr += '</div>'
                    tr += '</div>'
                    tr += '<div class="row s99p keyValRow-'+id+'-'+target+'">'
                    tr += '<div class="col-sm-6">'
                    tr += '<input class="mods_inputs keyword-final-'+id+'-'+target+'" placeholder="Keyword">'
                    tr += '</div>'
                    tr += '<div class="col-sm-6">'
                    tr += '<input class="mods_inputs value-final-'+id+'-'+target+'" placeholder="Value">'
                    tr += '</div>'
                    tr += '</div>'
                    tr += '<img src="images/md-swap.svg" class="swaping swap-'+id+'-'+target+'" key="'+id+'" target="'+target+'" width="15px">'
                    tr += '<img src="images/2D.png" class="extraCrps croping2d" key="'+id+'" target="'+target+'" title="2D Training">'
                    tr += '<img src="images/CT.png" class="extraCrps cropingContext" key="'+id+'" target="'+target+'" title="Context Training">'
                    tr += '</div>'
                    tr += '</div>'

                    $("."+class_name_field).append(tr);

                    $("select").formSelect();

                    sessionStorage.setItem('validation-'+id+'-'+target, JSON.stringify({"pattern":"NONE","globalCheck":false}));
                    ar_ind = areas.findIndex(x => x.id==id);
                    areas[ar_ind].page = target;
                    areas[ar_ind].record = 'new';

                    croped = areas[ar_ind];
                    reslt = rte(croped, $("#imageCountNum0").width());
                    //console.log(reslt);

                    get_Ocr(reslt, box_id)
                }
                else if (arrCount > a) {
                    // Deleted crop
                    $(".recd-"+id+"-"+target).remove();
                    delete already_selected[id+'-'+target];
                    arrCount = arrCount-1;
                }
                else {
                    // modified the crop
                    ar_ind = areas.findIndex(x => x.id==id);

                    croped = areas[ar_ind];
                    reslt = rte(croped, $("#imageCountNum0").width());
                    //console.log(reslt);

                    get_Ocr(reslt, box_id)
                }
            }
            else if (alt_title == 'table') {
                if (nullCheck(areas[id])) {
                    areas[id].page = target;
                    tableCrops[target] = areas
                    tableFinalCrops[target] = Object.assign({}, areas);
                }
                console.log(tableCrops);
                for (var i = 0; i < nofiles; i++) {
                    if (nullCheck(tableCrops[i])) {
                        a = a + tableCrops[i].length;
                    }
                }
                console.log(a);
                if (a == 2) {
                    table_train = false
                    var dt = new Date();
                    // var time = dt.getHours() + ":" + dt.getMinutes() + ":" + dt.getSeconds();
                    // tbl = '<p>'
                    // tbl += '<label>'
                    // tbl += '<input type="checkbox" class="filled-in headerCheck"/>'
                    // tbl += '<span>Is Header is repeatable?</span>'
                    // tbl += '</label>'
                    // tbl += '</p>'
                    // tbl += '<p>'
                    // tbl += '<label>'
                    // tbl += '<input type="checkbox" class="filled-in footerCheck"/>'
                    // tbl += '<span>Are you want to show Footer?</span>'
                    // tbl += '</label>'
                    // tbl += '</p>'
                    tbl = '<button class="waves-effect waves-light btn-small mr-t-10 tryAbbyTable"  onclick="return false;">Proceed</button>'

                    $(".intialTableConfirm").html(tbl)
                }
            }
            else if(alt_title == 'displayFields'){

            }
            $("select").formSelect();
        }
    }
    // $("body").on("change", "#selectClass", function(){
    //     $(this).value;
    //     console;
    // })

    $("body").on("change", ".keywordSelect", function () {
        val = $(this).val();
        id = $(this).parent().parent().parent().parent().parent()[0].attributes['id'].value

        target = $(this).parent().parent().parent().parent().parent()[0].attributes['target'].value

        already_selected[id+'-'+target] = val;
        console.log(already_selected)
    })

    $("body").on("change", ".validationLabel", function () {
        key = $(this).attr('key');
        target = $(this).attr('target');
        value = $(this).val();
        keyword = $(".keyword-"+key+"-"+target).val();
        if(value == 'New') {
            $(".NewRuleName").val(keyword)
            $(".submitValidationModal").attr("key", key);
            $(".submitValidationModal").attr("target", target);
            $('#myModal1').modal('show');
        }
        else {
            vld_ = JSON.parse(sessionStorage.getItem('validation-'+key+'-'+target));
            vld_.pattern = value;
            sessionStorage.setItem('validation-'+key+'-'+target, JSON.stringify(vld_));
        }
    })


    $("body").on("click", ".nextToFields", function () {
        mainDataToSend.template = Object.assign({}, vendor_crop_data);
        if(retrain == "yes" || (nullCheck(mainDataToSend.template.header_ocr) && nullCheck(mainDataToSend.template.footer_ocr) && nullCheck(mainDataToSend.template.address_ocr))){
            if(retrain == "yes"){
                nofiles = $(".imageCount").length;

                for (var i = 0; i < nofiles; i++) {
                    $('#imageCountNum'+i).selectAreas('destroy');
                }
                showRetrinedData(retrainedData)
                stepperInstace.nextStep()
            }
            else {
                var list_json_ = '<option value="">Select Category</option>';
                for(i = 0;i < list_json.length;i++){
                    console.log(list_json[i]);
                    list_json_ += '<option value="'+list_json[i]+'">'+list_json[i]+'</option>';
                }
                $(".allFieldResults").prepend('<div class="col-sm-12"><div class="outputBody_"><div class="row" style="margin:0px !important"><div class="col-sm-6"><input class="mods_inputs invoiceCat" value="Invoice Category" readonly=""></div><div class="col-sm-6" style="padding: 0px;"><select class="mods_inputs optionss" name="selectClass">'+list_json_+'</select></div></div></div></div>')

                nextClicked = true
                nofiles = $(".imageCount").length;


                // console.log(all_cropped_data_history);

                for (var i = 0; i < nofiles; i++) {
                    $('#imageCountNum'+i).selectAreas('destroy');
                }


                console.log(mainDataToSend);

                alt_title = 'field'

                nextClicked = false

                for (var i = 0; i < nofiles; i++) {
                    width_ = $(".imagesCountNum"+i).width();

                    $("#imageCountNum"+i).selectAreas({
                        onChanged: debugHeaderAreas,
                        width: width_
                    });
                }
                $("select").formSelect();
                stepperInstace.nextStep()
            }
        }
        else{
            alert("Select all Header, Address and Footer from the template");
        }


    })

    tableTrainedArr = []
    $("body").on("click", ".nextToTable", function () {
        nextClicked = true
        mainArr = [];
        totalboxess = $(".fieldTrain").length;
        empt___ = 0;
        for (var ii = 0; ii < totalboxess; ii++) {
            id = $(".fieldTrain")[ii].attributes['id'].value;
            target = $(".fieldTrain")[ii].attributes['target'].value;
            checkSplit = $(".fieldTrain")[ii].attributes['split'].value;
            box_id = id+"-"+target;
            width_ = $('#imageCountNum'+target).width();
            var areas = $('#imageCountNum'+target).selectAreas('areas');
            if (areas.length > 0) {
                inx = areas.findIndex(x => x.id==id)
                codd = areas[inx];
                if (checkSplit == 'no') {
                    mainObj = {};
                    mainObj.field = $(".keyword-"+box_id).val();
                    if (!nullCheck($(".keyword-final-"+box_id).val()) && !nullCheck($(".value-final-"+box_id).val())) {
                        mainObj.keyword = '';
                        if ($(".parent_input_here-"+box_id).attr('title') == undefined) {
                            title = ''
                        }
                        else {
                            title = $(".parent_input_here-"+box_id).attr('title');
                        }
                        mainObj.value = title;
                    }
                    else {
                        $(".value-final-"+box_id).val()

                        if (!nullCheck($(".keyword-final-"+box_id).val())) {
                            keyword = ''
                        }
                        else {
                            keyword =$(".keyword-final-"+box_id).val();
                        }
                        mainObj.keyword = keyword;

                        if (!nullCheck($(".value-final-"+box_id).val())) {
                            value = ''
                        }
                        else {
                            value = $(".value-final-"+box_id).val();
                        }
                        mainObj.value = value;
                    }
                    mainObj.validation = JSON.parse(sessionStorage.getItem('validation-'+box_id));
                    mainObj.split = 'no'
                    mainObj.coordinates = codd;
                    mainObj.width = width_;
                    mainObj.page = areas[inx].page;
                    if (nullCheck(extraTrainingFields[box_id])) {
                        mainObj.additional_splits = extraTrainingFields[box_id]
                        console.log("hereeeeeeeeeeee", mainObj);
                    }
                    // mainObj.vendorName = selectedOption;
                    if (nullCheck(mainObj.keyword) || nullCheck(mainObj.value)) {
                        mainArr.push(mainObj);
                    }
                    if (!nullCheck(mainObj.field) || (!nullCheck(mainObj.value) && !nullCheck(mainObj.keyword))) {
                        empt___ = 1;
                    }
                }
                else {
                    splitedDivs = $(".splitDiv-"+box_id)
                    for (var iij = 0; iij < splitedDivs.length; iij++) {
                        splitId = $(".splitDiv-"+box_id)[iij].attributes['splitId'].value
                        box_id_ = box_id+'-'+splitId;
                        mainObj = {};
                        mainObj.field = $(".keyword-"+box_id_).val();
                        if (!nullCheck($(".keyword-final-"+box_id_).val()) && !nullCheck($(".value-final-"+box_id_).val())) {
                            mainObj.keyword = '';
                            if ($(".parent_input_here-"+box_id_).attr('title') == undefined) {
                                title = ''
                            }
                            else {
                                title = $(".parent_input_here-"+box_id_).attr('title');
                            }
                            mainObj.value = title;
                        }
                        else {
                            $(".value-final-"+box_id_).val()

                            if (!nullCheck($(".keyword-final-"+box_id_).val())) {
                                keyword = ''
                            }
                            else {
                                keyword =$(".keyword-final-"+box_id_).val();
                            }
                            mainObj.keyword = keyword;

                            if (!nullCheck($(".value-final-"+box_id_).val())) {
                                value = ''
                            }
                            else {
                                value = $(".value-final-"+box_id_).val();
                            }
                            mainObj.value = value;
                        }

                        mainObj.validation = JSON.parse(sessionStorage.getItem('validation-'+box_id));
                        mainObj.split = 'yes'
                        mainObj.coordinates = codd;
                        mainObj.width = width_;
                        mainObj.page = codd.page;
                        if (nullCheck(mainObj.keyword) || nullCheck(mainObj.value)) {
                            mainArr.push(mainObj);
                        }
                        if (!nullCheck(mainObj.field) || (!nullCheck(mainObj.value) && !nullCheck(mainObj.keyword))) {
                            empt___ = 1;
                        }
                    }
                }
            }
        }
        var vendor_field_data = {
            'field':'Invoice Category',
            'keyword': $(".optionss").val(),
            'value':$(".optionss").val(),
            'coordinates':
            {
                'x':0,
                'y':0,
                'width':0,
                'height':0,
                'page':0,
            },

        }
        console.log(mainArr)

        if(empt___ == 0){
            if(nullCheck($(".optionss").val()) || retrain == 'yes') {
                if(retrain == 'no'){
                    mainArr.push(vendor_field_data)
                }
                mainDataToSend.fields = Object.assign({}, mainArr);

                for (var i = 0; i < nofiles; i++) {
                    $('#imageCountNum'+i).selectAreas('destroy');
                }
                stepperInstace.nextStep()

                if(retrain == 'yes' && !$.isEmptyObject(retrainedTable)){
                    displayTableTrainedData(retrainedTable)
                }

                console.log(mainDataToSend);
            }
            else{
                alert("Invoice Catergory should not be empty")
            }

        }
        else{
            alert("Field data should not be empty");
        }
    })

    $("body").on("click", ".addNewTable", function () {
        tableCount = $(this).attr("count");
        $(this).attr("count", Number(tableCount)+1);
        $(".allTableResults").html('<p>Crop the Header and Footer of the table</p><div class="intialTableConfirm mr-t-10"></div><div class="allTablesShow mr-t-20" style="overflow-x: auto;"></div><div class="anyBtns mr-t-20"></div>')
        if (!$.isEmptyObject(final_table_save)) {
            $(".header_crop").remove();
            tableTrainedArr.push(final_table_save)
        }
        nextClicked = false
        alt_title = 'table';
        table_train = true
        for (var i = 0; i < nofiles; i++) {
            width_ = $(".imagesCountNum"+i).width();
            $("#imageCountNum"+i).selectAreas({

                onChanged: debugHeaderAreas,
                width: width_,
                maxAreas:2
            });
        }
    })

    // tableResponse = [[[[[['<b>SR. NO.</b>', 1, 1], ['<b>PRODUCT DESCRIPTION</b>', 1, 1], ['<b>ITEM CODE</b>', 1, 1], ['<b>HSN CODE</b>', 1, 1], ['<b>BATCH NUMBER</b>', 1, 1], ['<b>EXPIRY DATE</b>', 1, 1], ['<b>TOTAL QUANTITY</b>', 1, 1], ['<b>PKG/ DRUM</b>', 1, 1], ['<b>UOM</b>', 1, 1], ['<b>MRP</b>', 1, 1], ['<b>UNIT PRICE</b>', 1, 1], ['<b>TAXABLE VALUE</b>', 1, 1], ['<b>FREIGHT</b>', 1, 1], ['<b>TOTAL TAXABLE VALUE</b>', 1, 1], ['<b>IGST RATE AMOUNT</b>', 1, 1], ['<b>CGST RATE AMOUNT</b>', 1, 1], ['<b>SGST RATE AMOUNT</b>', 1, 1]], [['', 1, 1], [' 1 ATARAX 6MG/ML 15ML DRO IN', 1, 1], [' FDA00001', 1, 1], [' 30049099', 1, 1], [' LI0418015', 1, 1], [' suspicious11/2020', 1, 1], [' 96240.00', 1, 1], [' 401', 1, 1], [' EA', 1, 1], [' 48.00', 1, 1], [' 8.02', 1, 1], [' 771845.00', 1, 1], ['', 1, 1], [' 771845.00', 1, 1], [' 12.00 92621.00', 1, 1], ['', 1, 1], ['', 1, 1]]], [[[' Total', 1, 1], [' 96240.00 771845.00 771845.00 92621.00', 1, 1]]]],["SR. NO.","PRODUCT DESCRIPTION","ITEM CODE","HSN CODE","BATCH NUMBER","EXPIRY DATE","TOTAL QUANTITY","PKG/ DRUM","UOM","MRP","UNIT PRICE","TAXABLE VALUE","FREIGHT","TOTAL TAXABLE VALUE","IGST RATE AMOUNT","CGST RATE AMOUNT","SGST RATE AMOUNT"], {'hors': [[[13, 195], [655, 195]], [[13, 212], [655, 212]], [[13, 232], [655, 232]]], 'vers': [[[13, 195], [13, 232]], [[16, 195], [16, 232]], [[135, 195], [135, 232]], [[166, 195], [166, 232]], [[193, 195], [193, 232]], [[230, 195], [230, 232]], [[256, 195], [256, 232]], [[289, 195], [289, 232]], [[311, 195], [311, 232]], [[331, 195], [331, 232]], [[352, 195], [352, 232]], [[380, 195], [380, 232]], [[420, 195], [420, 232]], [[448, 195], [448, 232]], [[480, 195], [480, 232]], [[541, 195], [541, 232]], [[598, 195], [598, 232]], [[655, 195], [655, 232]]]}]]

    abbyyTrainObj = {}
    $("body").on("click", ".tryAbbyTable", function () {
        table_cords = []
        $.each(tableFinalCrops, function (k, v) {
            $.each(v, function (kk, vv) {
                table_cords.push(vv)
            })
        })
        sendObj = {};
        sendObj.table_data = {};
        sendObj.table_data.coordinates = table_cords;
        // sendObj.table_data.headerCheck = $(".headerCheck").is(":checked");
        // sendObj.table_data.footerCheck = $(".footerCheck").is(":checked");
        // sendObj.ocr_data = ocr_data;
        sendObj.file_name = file_id;
        sendObj.case_id = case_id;
        sendObj.method = 'abbyy'
        sendObj.img_width = $(".showImgs ").width();
        abbyyTrainObj = sendObj
        console.log(sendObj);
        var settings11 = {
            "async": true,
            "crossDomain": true,
            "url": dynamicUrl+"/predict_with_ui_data",
            "method": "POST",
            "processData": false,
            "contentType": "application/json",
            "data": JSON.stringify(sendObj)
        };
        $.ajax(settings11).done(function (msg) {
            console.log(msg);
            tableResponse = msg.data.table;

            $(".intialTableConfirm *").attr("disabled", "disabled").off('click');

            for (var i = 0; i < nofiles; i++) {
                $('#imageCountNum'+i).selectAreas('destroy');
            }

            tableShow = tableResponse[0][0];
            console.log(tableShow);
            table_generate_display(tableShow)



            btns = '<button class="waves-effect waves-light btn-small light-blue tryHorsVers removeThis" onclick="return false;">Try another method</button>'
            btns += ' <span>or</span> <button class="waves-effect waves-light btn-small light-blue mr-r-20 proceedAbby removeThis" onclick="return false;">Proceed</button>'

            $(".anyBtns").html(btns)
        });

        // console.log(JSON.stringify(sendObj));

    })

    function table_generate_display(tableShow, class_) {
        // alert();
        tr = ''
        trained_table[tableCount] = tableShow;

        for (var i = 0; i < tableShow.length; i++) {
            table = tableShow[i];
            tr += '<table class="table table-bordered">'
            for (var j = 0; j < table.length; j++) {
                row = table[j]
                tr += '<tr>'
                for (var k = 0; k < row.length; k++) {
                    cell = row[k]
                    console.log(cell[0]);
                    tr += '<td rowspan="'+cell[1]+'" colspan="'+cell[2]+'">'+cell[0].replace(/suspicious/g, '')+'</td>'
                }
                tr += '</tr>'
            }
            tr += '</table>'
        }

        if (nullCheck(class_)) {
            $("."+class_).html(tr)
        }
        else {
            $(".allTablesShow").html(tr)
        }
    }

    $("body").on("click", ".tryHorsVers", function () {
        lines = tableResponse[0][2];
        table_line_draw(lines)

        btns = '<button class="waves-effect waves-light btn-small light-blue mr-r-20 confirm_table removeThis" onclick="return false;">Adjust & Proceed</button>'

        $(".anyBtns").html(btns)
    })

    $("body").on("click", ".proceedAbby", function () {
        $(".allTableResults").append('<div class="stage2"></div>')
        displayHeaders(tableResponse[0][1], "abbyy");
    })

    header_lines_temp = [];
    header_lines = [];
    header_lines_temp = [];
    split_lines_temp = [];
    ver_splt_lines_temp = [];
    initial_hor = [];
    splitsData = {};
    ver_splits=[];
    $("body").on("click", ".confirm_table", function(){
        $(".stage2").remove()
        $(".stage2Btns").remove()
        $(".allTableResults").append('<div class="stage2"></div><div class="stage2Btns"><button method="tnox" class="waves-effect waves-light btn-small mr-t-10 light-blue mr-r-20 mr-b-20 proceedVers removeThis" onclick="return false;">Train</button></div>')
        optns = '<option value="">Select Alias</option>'
        console.log(default_Output_fields);
        for (var i = 0; i < default_Output_fields.length; i++) {
            if (default_Output_fields[i].indexOf('Table.') > -1) {
                tableField = default_Output_fields[i].replace('Table.', '')
                optns += '<option value="'+tableField+'">'+tableField+'</option>'
            }
        }
        $(".displayTrainedTable").remove();
        splt_lines = $(".horizontal_linesptl");
        ver_lines = $(".vertical_line");


        header_lines = [];
        header_lines_temp = [];
        split_lines_temp = [];
        ver_splt_lines_temp = [];
        initial_hor = [];
        splitsData = {};

        ver_splits=[];

        hor_init = $(".hor_gen_ver");
        ;
        for (var i = 0; i < hor_init.length; i++) {
            obj = {};
            obj.t = hor_init[i].offsetTop;
            obj.l = hor_init[i].offsetLeft;
            obj.w = hor_init[i].offsetWidth;
            obj.h = hor_init[i].offsetHeight;
            obj.page = hor_init[i].attributes['page'].value;
            initial_hor.push(obj);
        }

        console.log(initial_hor);

        for (var vl = 0; vl < ver_lines.length; vl++) {
            if (ver_lines[vl].className.indexOf("vertical_linesptl") == -1) {
                header_lines_temp.push(ver_lines[vl])
            }
            else {
                split_lines_temp.push(ver_lines[vl])
            }
        }

        console.log(header_lines_temp, split_lines_temp);

        for (var i = 0; i < initial_hor.length-1; i++) {
            for (var j = 0; j < split_lines_temp.length; j++) {
                sp_t = split_lines_temp[j].offsetTop
                sp_h = split_lines_temp[j].offsetHeight
                if (sp_t >= initial_hor[i].t && sp_t <= initial_hor[i+1].t) {
                    //console.log("inside "+i);
                    obj = {};
                    obj.t = sp_t;
                    obj.h = sp_h;
                    obj.w = split_lines_temp[j].offsetWidth;
                    obj.l = split_lines_temp[j].offsetLeft;
                    ver_splits.push(obj)
                }
            }
        }

        console.log("vertical splits", ver_splits);

        for (var i = 0; i < initial_hor.length-1; i++) {
            split = "false";
            inbetween = [];
            for (var jj = 0; jj < splt_lines.length; jj++) {
                if (splt_lines[jj].offsetTop >= initial_hor[i].t && splt_lines[jj].offsetTop <= initial_hor[i+1].t) {
                    inbetween = [];
                    mobj = {};

                    left = splt_lines[jj].offsetLeft;
                    right = splt_lines[jj].offsetWidth + left;

                    top_data = splt_lines[jj].offsetTop;
                    ll_ = 0;
                    for (var j = 0; j < ver_lines.length; j++) {
                        if (ver_lines[j].className.indexOf("vertical_linesptl") == -1) {
                            if (ver_lines[j].offsetLeft + 15 >= left && ver_lines[j].offsetLeft + 15 <= right) {
                                arr = [];
                                obj = {};
                                wd = ver_lines[j+1].offsetLeft - ver_lines[j].offsetLeft;
                                obj = {};
                                obj.w = wd;
                                obj.h = splt_lines[jj].offsetTop - initial_hor[i].t;
                                obj.l = splt_lines[jj].offsetLeft + ll_;
                                obj.t = initial_hor[i].t + 7;
                                arr.push(obj)
                                obj = {};
                                obj.w = wd;
                                obj.h = initial_hor[i+1].t - splt_lines[jj].offsetTop;
                                obj.l = splt_lines[jj].offsetLeft + ll_;
                                obj.t = splt_lines[jj].offsetTop + 7;
                                arr.push(obj)

                                mobj['v'+(j)] = arr;
                                ll_ = ll_ + wd;
                            }
                        }
                    }
                    split = "true";
                    //console.log("in between ",inbetween);
                    $.each(mobj, function (kk,vv) {
                        splitsData["h"+i+""+kk] = vv;
                    })

                }
            }

        }

        console.log(splitsData, header_lines_temp);
        sortedHeaders = []
        for (var i = 0; i < header_lines_temp.length; i++) {
            obj = {}
            obj.t = header_lines_temp[i].offsetTop
            obj.w = header_lines_temp[i].offsetWidth
            obj.l = header_lines_temp[i].offsetLeft
            obj.h = header_lines_temp[i].offsetHeight
            sortedHeaders.push(obj)
        }

        sortedHeaders = sortedHeaders.sort(function(a, b){ return a.l - b.l; })

        header_lines = []
        for (var i = 0; i < initial_hor.length-1; i++) {
            for (var j = 1; j < sortedHeaders.length; j++) {
                if (j != sortedHeaders.length) {
                    if (initial_hor[i].t <= sortedHeaders[j].t + 5) {

                        obj = {};
                        obj.t = sortedHeaders[j].t

                        obj.l = sortedHeaders[j-1].l + 7;
                        obj.w = sortedHeaders[j].l - sortedHeaders[j-1].l;
                        obj.h = initial_hor[i+1].t - initial_hor[i].t
                        obj.page = 0;
                        header_lines.push(obj);
                        // drawbox(obj)
                    }
                }

            }
        }
        console.log("initail hors", initial_hor);
        footerVerSplits = []
        for (var i = 0; i < header_lines.length; i++) {
            prev_value = '';
            if (splitsData['h0v'+i] != undefined) {
                for (var jj = 0; jj < splitsData['h0v'+i].length; jj++) {
                    splitsData['h0v'+i][jj].page = header_lines[i].page
                    btw = splitsData['h0v'+i][jj].l + header_lines[i].w;
                    lines_in_box = [];
                    for (var jk = 0; jk < ver_splits.length; jk++) {
                        if (ver_splits[jk].t <= splitsData['h0v'+i][jj].t && (splitsData['h0v'+i][jj].l <= ver_splits[jk].l && btw >= ver_splits[jk].l)) {
                            lines_in_box.push(ver_splits[jk]);
                        }
                    }
                    prev_v_line = {};

                    if (lines_in_box.length>0) {
                        for (var jk = 0; jk <= lines_in_box.length; jk++) {
                            obj = {};
                            tpp = nullCheck(lines_in_box[jk]) ? lines_in_box[jk].t : lines_in_box[jk-1].t
                            obj.t = tpp - adjtop(splitsData['h0v'+i][jj].page);
                            obj.h = splitsData['h0v'+i][jj].h;
                            obj.page = splitsData['h0v'+i][jj].page;

                            if (!$.isEmptyObject(prev_v_line)) {
                                obj.l = prev_v_line.l;
                            }
                            else {
                                obj.l = header_lines[i].l;
                            }

                            if (jk == lines_in_box.length) {
                                obj.w = (header_lines[i].l + header_lines[i].w) - prev_v_line.l;
                            }
                            else if (jk == 0) {
                                obj.w = lines_in_box[jk].l - header_lines[i].l + 7;
                                lines_in_box[jk].page = header_lines[i].page;
                                prev_v_line = lines_in_box[jk];
                            }
                            else {
                                obj.w = lines_in_box[jk].l - prev_v_line.l + 7;
                                lines_in_box[jk].page = header_lines[i].page;
                                prev_v_line = lines_in_box[jk];
                            }
                            // drawbox(obj)
                            text = '';
                            reslt = table_rte(obj, $(".imageCountNum0").width());
                            //console.log(obj, reslt);
                            for (var jkk = 0; jkk < reslt.length; jkk++) {
                                text = text +' '+ reslt[jkk].word+ ' ';
                            }
                            $('.box-v'+(i+1)+'.'+(jk+1)).remove();

                            vv  = '<div class="removeAllHeaders box box-v box-v'+(i+1)+'.'+(jk+1)+'" del="no" id="'+(i+1)+'" splits="yes"  sub="'+(jk+1)+'">'
                            vv += '<div class="">'
                            vv += '<p style="float: left;">V'+(i+1)+'.'+(jk+1)+'</p>'
                            vv += '<input type="text" placeholder="Label" name="" value="'+$.trim(text)+'" class="label_inputs label_name">'
                            vv += '<div class="clear__"></div>'
                            vv += '</div>'
                            vv += '<div class="">'
                            vv += '<select class="label_inputs alias_change thisOpt mr-b-0">'+optns+'</select>'
                            vv += '</div>'
                            vv += '<image src="images/trash.svg" class="delete_col trash">'
                            vv += '<div>'
                            vv += '<label>'
                            vv += '<input class="with-gap" name="group1" type="radio" checked/>'
                            vv += '<span>Ref key</span>'
                            vv += '</label>'
                            vv += '<label class="mr-l-20">'
                            vv += '<input type="checkbox" class="filled-in markField"/>'
                            vv += '<span>Mark as field</span>'
                            vv += '</label>'
                            vv += '<div class="fieldSelectDiv">'

                            vv += '</div>'
                            vv += '</div>'
                            vv += '</div>'

                            $(".stage2").append(vv);
                        }
                    }
                    else {
                        text = '';
                        top__ =  splitsData['h0v'+i][jj].t - adjtop(splitsData['h0v'+i][jj].page);
                        splitsData['h0v'+i][jj].t = top__
                        reslt = table_rte(splitsData['h0v'+i][jj], $(".imageCountNum0").width());
                        //console.log(splitsData['h0v'+i][jj], reslt);
                        // drawbox(splitsData['h0v'+i][jj])
                        for (var jk = 0; jk < reslt.length; jk++) {
                            text = text +' '+ reslt[jk].word+ ' ';
                        }
                        prev_value = text;
                        $('.box-v'+(i+1)).remove();

                        vv  = '<div class="removeAllHeaders box box-v box-v'+(i+1)+'" del="no" id="'+(i+1)+'" splits="yes">'
                        vv += '<div class="">'
                        vv += '<p style="float: left;">V'+(i+1)+'</p>'
                        vv += '<input type="text" placeholder="Label" name="" value="'+$.trim(text)+'" class="label_inputs label_name">'
                        vv += '<div class="clear__"></div>'
                        vv += '</div>'
                        vv += '<div class="">'
                        vv += '<select class="label_inputs alias_change thisOpt mr-b-0">'+optns+'</select>'
                        vv += '</div>'
                        vv += '<image src="images/trash.svg" class="delete_col trash">'
                        vv += '<div>'
                        vv += '<label>'
                        vv += '<input class="with-gap" name="group1" type="radio" checked/>'
                        vv += '<span>Ref key</span>'
                        vv += '</label>'
                        vv += '<label class="mr-l-20">'
                        vv += '<input type="checkbox" class="filled-in markField"/>'
                        vv += '<span>Mark as field</span>'
                        vv += '</label>'
                        vv += '<div class="fieldSelectDiv">'

                        vv += '</div>'
                        vv += '</div>'
                        vv += '</div>'

                        $(".stage2").append(vv);

                    }
                }
            }
            else {
                // header_lines[i].page = 0;
                top__ =  header_lines[i].t - adjtop(header_lines[i].page);
                //console.log(header_lines[i].page, adjtop(header_lines[i].page), top__);
                header_lines[i].t = top__
                // drawbox(header_lines[i])
                reslt = table_rte(header_lines[i], $(".imageCountNum0").width());
                //console.log(header_lines[i], reslt);
                text = '';
                for (var j = 0; j < reslt.length; j++) {
                    text = text +' '+ reslt[j].word+ ' ';
                }
                //console.log(text);
                prev_value = $.trim(text);
                $('.box-v'+(i+1)).remove();
                vv  = '<div class="removeAllHeaders box box-v box-v'+(i+1)+'" del="no" id="'+(i+1)+'">'
                vv += '<div class="">'
                vv += '<p style="float: left;">V'+(i+1)+'</p>'
                vv += '<input type="text" placeholder="Label" name="" value="'+$.trim(text)+'" class="label_inputs label_name">'
                vv += '<div class="clear__"></div>'
                vv += '</div>'
                vv += '<div class="">'
                vv += '<select class="label_inputs alias_change thisOpt mr-b-0">'+optns+'</select>'
                vv += '</div>'
                vv += '<image src="images/trash.svg" class="delete_col trash">'
                vv += '<div>'
                vv += '<label>'
                vv += '<input class="with-gap" name="group1" type="radio" checked/>'
                vv += '<span>Ref key</span>'
                vv += '</label>'
                vv += '<label class="mr-l-20">'
                vv += '<input type="checkbox" class="filled-in markField"/>'
                vv += '<span>Mark as field</span>'
                vv += '</label>'
                vv += '<div class="fieldSelectDiv">'

                vv += '</div>'
                vv += '</div>'
                vv += '</div>'
                $(".stage2").append(vv);
            }
        }
        // console.log(headers);
        hors = $(".inital_res");

        footers = [];
        footerVerSplits = []
        for (var i = 2; i < 3; i++) {
            for (var jk = 0; jk < ver_splits.length; jk++) {
                if (ver_splits[jk].t >= hors[i].offsetTop - 6 && hors[i].offsetLeft <= ver_splits[jk].l) {
                    footerVerSplits.push(ver_splits[jk]);
                }
            }
        }
        finalCrops = []
        console.log(footerVerSplits);
        for (var i = 0; i < footerVerSplits.length; i++) {
            obj = {};
            obj.t = footerVerSplits[i].t;
            obj.h = footerVerSplits[i].h;
            obj.w = footerVerSplits[i].l - hors[2].offsetLeft + 15;
            obj.l = hors[2].offsetLeft - 10;
            obj.page = hors[2].attributes.page.value;
            // drawbox(obj)
            finalCrops.push(obj)
            reslt = table_rte(obj, $("#imageCountNum0").width());
            // reslt = ["Sample text"];
            console.log(obj, reslt);
            text = ''
            for (var jk = 0; jk < reslt.length; jk++) {
                text = text +' '+ reslt[jk].word+ ' ';
            }
            prev_value = $.trim(text);
            vv  = '<div class="removeAllHeaders box" del="no">'
            vv += '<div class="">'
            vv += '<p style="float: left;">Footer'+(i+1)+'</p>'
            vv += '<input type="text" placeholder="Label" name="" value="'+$.trim(prev_value)+'" class="label_inputs label_name footerData">'
            vv += '<div class="clear__"></div>'
            vv += '</div>'
            vv += '</div>'
            $(".stage2").append(vv);
            footers.push(prev_value)
        }
        console.log(footers);
        footerData = footers

        // getHeaderLines(header_hors, ver_lines)

        $("select").formSelect();

    })

    function drawbox(data) {
        //$(".showImgs").append('<div style="position: absolute; z-index: 999999; border: 2px solid blue; height:'+data.h+'px;width:'+data.w+'px;top:'+data.t+'px;left:'+data.l+'px;"></div>')
        return '';
    }

    $("body").on("dblclick", ".horizontal_line", function (e) {

        wrapper = $(this).parent();
        parentOffset = wrapper.offset();
        lft = e.pageX - parentOffset.left + wrapper.scrollLeft();
        initial_hor = []
        hor_init = $(".hor_gen_ver");
        for (var i = 0; i < hor_init.length; i++) {
            obj = {};
            obj.t = hor_init[i].offsetTop;
            obj.l = hor_init[i].offsetLeft;
            obj.w = hor_init[i].offsetWidth;
            obj.h = hor_init[i].offsetHeight;
            obj.page = hor_init[i].attributes['page'].value;
            initial_hor.push(obj);
        }

        id = $(this).attr('id');
        obj = {};
        y1 = $(this)[0].offsetTop+5;
        if (id == 0) {
            y2 = $(".hor_gen_ver")[1].offsetTop+5;
            obj.height = y2-y1;
            obj.width = 10;
            obj.left = lft-4;
            obj.top = y1;
            //console.log("---2----", $(".vertical_line").length);
            drawVerLines(0, obj);
        }
        else {
            if (id != 'sptl') {
                for (var i = 0; i < initial_hor.length-1; i++) {
                    if (y1 >= initial_hor[i].t && y1 <= initial_hor[i+1].t) {
                        if (i == 0) {
                            y2 = initial_hor[i+2].t;
                        }
                        else {
                            y2 = initial_hor[i+1].t;
                        }

                    }
                }
            }
            else {
                y2 = $(".hor_gen_ver")[1].offsetTop+5;
            }


            obj.height = y2-y1 + 6;
            obj.width = 10;
            obj.left = lft - 7.5;
            obj.top = y1;
            //console.log("---split----", $(".vertical_line").length);
            drawVerLines('sptl', obj);
        }

    })

    $("body").on("dblclick", ".vertical_line", function (e) {
        obj = {};
        wrapper = $(this).parent();
        parentOffset = wrapper.offset();
        lft = e.pageX - parentOffset.left + wrapper.scrollLeft();
        relY = e.pageY - parentOffset.top + wrapper.scrollTop();
        // lft = e.screenX - $(".HorZOn").offset().left + 1;
        obj.top = relY - 5;
        obj.left = lft;
        obj.width = initial_hor[0].w - lft + 15;
        obj.height = 12;
        //console.log(obj);
        drawHorLines('sptl', obj, 'null', 0);

    })

    function displayHeaders(headers, method_) {
        optns = '<option value="">Select Alias</option>'
        console.log(default_Output_fields);
        for (var i = 0; i < default_Output_fields.length; i++) {
            if (default_Output_fields[i].indexOf('Table.') > -1) {
                optns += '<option value="'+default_Output_fields[i].replace(/Table./g, "")+'">'+default_Output_fields[i].replace(/Table./g, "")+'</option>'
            }
        }

        $(".removeAllHeaders").remove();
        for (var i = 0; i < headers.length; i++) {
            text = headers[i];
            vv  = '<div class="removeAllHeaders box box-v box-v'+(i+1)+'" del="no" id="'+(i+1)+'" splits="yes">'
            vv += '<div class="">'
            vv += '<p style="float: left;">V'+(i+1)+'</p>'
            vv += '<input type="text" placeholder="Label" name="" value="'+$.trim(text)+'" class="label_inputs label_name">'
            vv += '<div class="clear__"></div>'
            vv += '</div>'
            vv += '<div class="">'
            vv += '<select class="label_inputs alias_change thisOpt mr-b-0">'+optns+'</select>'
            vv += '</div>'
            vv += '<image src="images/trash.svg" class="delete_col trash">'
            vv += '<div>'
            vv += '<label>'
            vv += '<input class="with-gap" name="group1" type="radio" checked/>'
            vv += '<span>Ref key</span>'
            vv += '</label>'
            vv += '<label class="mr-l-20">'
            vv += '<input type="checkbox" class="filled-in markField"/>'
            vv += '<span>Mark as field</span>'
            vv += '</label>'
            vv += '<div class="fieldSelectDiv">'

            vv += '</div>'
            vv += '</div>'
            vv += '</div>'

            $(".stage2").append(vv);
        }

        $(".allTableResults").append('<div><button method="'+method_+'" class="waves-effect waves-light btn-small mr-t-10 light-blue mr-r-20 mr-b-20 proceedVers removeThis" onclick="return false;">Train</button></div>')

        $("select").formSelect();
    }

    $("body").on("click", ".markField", function () {
        if ($(this).is(":checked")) {
            field_opts = '<option value="">Select Type</option>'
            field_opts = '<option value="kh_vh">Key, Values in Header</option>'
            field_opts += '<option value="kh_vc">Key in Header, Value in Column</option>'
            $(this).parent().parent().find(".fieldSelectDiv").html('<select class="label_inputs  mr-b-0">'+field_opts+'</select>')
            $("select").formSelect();
        }
        else {
            $(this).parent().parent().find(".fieldSelectDiv").html('')
        }
    })

    var final_table_save

    $("body").on("click", ".proceedVers", function () {
        console.log($(".box-v"));
        vrs = $(".box-v")
        method__ = $(this).attr('method');
        final_arr = {}
        emp_alias = 0;
        for (var i = 0; i < vrs.length; i++) {
            text = vrs[i].children[0].children[0].innerText;
            obj = {};
            obj.label = vrs[i].children[0].children[1].value;
            obj.del = vrs[i].attributes.del.value;

            obj.alias = vrs[i].children[1].children[0].children[3].value;
            if(obj.del == 'no' && !nullCheck(obj.alias)){
                emp_alias = 1;
            }
            obj.ref = vrs[i].children[3].children[0].children[0].checked;
            obj.field = vrs[i].children[3].children[1].children[0].checked;

            if (obj.field) {
                obj.field_type = vrs[i].children[3].children[2].children[0].children[3].value;
            }
            else {
                obj.field_type = ''
            }

            final_arr[text.toLowerCase()] = obj
        }
        console.log(final_arr);
        if (method__ != 'abbyy') {
            final_arr['h2v1'] = {};
            final_arr['h2v1'].label = $(".footerData").val();
            final_arr['h2v1'].type = "Simple Single Key-value";
            final_arr['h2v1'].del = "no"
            final_arr['h2v1'].alias = ""
            final_arr['h2v1'].ref = false
            final_arr['h2v1'].field = false
        }

        if(emp_alias == 0){
            console.log(final_arr);

            sendObj = {};
            sendObj.retrain = retrain
            if (retrain == 'yes') {
                sendObj.table_data = {}
            }
            else {
                sendObj.table_data = abbyyTrainObj.table_data
            }
            sendObj.table_data.trained_data = final_arr;
            sendObj.method = method__;
            sendObj.file_name = file_id;
            sendObj.case_id = case_id;
            sendObj.img_width = $(".showImgs").width();

            final_table_save = {}
            final_table_save.table_data = sendObj.table_data;
            final_table_save.method = method__;


            // mainDataToSend.table = final_table_save
            console.log(sendObj);
            var form = new FormData();
            form.append("file", JSON.stringify(sendObj));
            var settings11 = {
                "async": true,
                "crossDomain": true,
                "url":dynamicUrl+"/predict_with_ui_data",
                "method": "POST",
                "processData": false,
                "contentType": "application/json",
                "data": JSON.stringify(sendObj)
            };
            $.ajax(settings11).done(function (msg) {
                console.log(msg);
                if (msg.flag) {
                    msg = msg.data.table[0][0];
                    $(".displayTrainedTable").remove();
                    $(".allTableResults").append('<div class="displayTrainedTable" style="overflow-x: auto;"></div>')
                    table_generate_display(msg, "displayTrainedTable")
                    $(".extraBtns").remove();
                    $(".allTableResults").append('<div class="extraBtns mr-b-20"><button class="addFieldMap" onclick="return false;">Add Field Mapping</button><div class="row field_map_rows"></div></div>')
                }
                else {
                    alert(msg.message);
                }
            });
        }
        else{
            alert("Alias should not be empty");
        }


    })

    $("body").on("click", ".addFieldMap", function () {

        alt_title = 'fieldmap'

        for (var i = 0; i < nofiles; i++) {
            width_ = $(".imagesCountNum"+i).width();
            $("#imageCountNum"+i).selectAreas({
                onChanged: debugHeaderAreas,
                width: width_
            });
        }
    })

    $("body").on("click", ".saveBtn", function () {
        totalboxess =  $(".field_map_rows")
        if (totalboxess.length>0) {
            totalboxess = $(".field_map_rows")[0].children.length;

            empt___ = 0;
            mainArr_ = []
            for (var ii = 0; ii < totalboxess; ii++) {
                id = $(".field_map_rows")[0].children[ii].attributes['id'].value;
                target = $(".field_map_rows")[0].children[ii].attributes['target'].value;
                box_id = id+"-"+target;
                var areas = $('#imageCountNum'+target).selectAreas('areas');

                if (areas.length > 0) {
                    inx = areas.findIndex(x => x.id==id)
                    codd = areas[inx];

                    mainObj = {};
                    mainObj.field = $(".field_map_rows .keyword-"+box_id).val();
                    if (!nullCheck($(".field_map_rows .keyword-final-"+box_id).val()) && !nullCheck($(".field_map_rows .value-final-"+box_id).val())) {
                        mainObj.keyword = '';
                        if ($(".field_map_rows .parent_input_here-"+box_id).attr('title') == undefined) {
                            title = ''
                        }
                        else {
                            title = $(".field_map_rows .parent_input_here-"+box_id).attr('title');
                        }
                        mainObj.value = title;
                    }
                    else {
                        $(".field_map_rows .value-final-"+box_id).val()

                        if (!nullCheck($(".field_map_rows .keyword-final-"+box_id).val())) {
                            keyword = ''
                        }
                        else {
                            keyword =$(".field_map_rows .keyword-final-"+box_id).val();
                        }
                        mainObj.keyword = keyword;

                        if (!nullCheck($(".field_map_rows .value-final-"+box_id).val())) {
                            value = ''
                        }
                        else {
                            value = $(".field_map_rows .value-final-"+box_id).val();
                        }
                        mainObj.value = value;
                    }
                    mainObj.type = $(".field_map_rows .validationtype-"+box_id).val();
                    mainObj.coordinates = codd;
                    mainObj.width = width_;
                    mainObj.page = areas[inx].page;

                    if (nullCheck(mainObj.keyword) || nullCheck(mainObj.value)) {
                        mainArr_.push(mainObj);
                    }
                    if (!nullCheck(mainObj.field) || (!nullCheck(mainObj.value) && !nullCheck(mainObj.keyword))) {
                        empt___ = 1;
                    }

                }
            }
            mainDataToSend.field_map = Object.assign({}, mainArr_);
        }


        mainDataToSend.table = $.isEmptyObject(tableTrainedArr) ? [final_table_save] : tableTrainedArr

        mainDataToSend.trained_table = JSON.stringify(trained_table);
        // console.log(mainDataToSend, JSON.stringify(mainDataToSend));
        if(retrain == 'yes'){
            mainDataToSend.template_name = template_name_retrain;
            mainDataToSend.file_name = file_id;
            mainDataToSend.case_id = case_id;
            mainDataToSend.img_width = $("#imageCountNum0").width();
            mainDataToSend.resize_factor = $("#imageCountNum0").width()/670;
            mainDataToSend.retrain = retrain;

            console.log(mainDataToSend);
            var form = new FormData();
            form.append("file", JSON.stringify(mainDataToSend));
            var settings11 = {
                "async": true,
                "crossDomain": true,
                "url": dynamicUrl+"/retrain",
                "method": "POST",
                "processData": false,
                "contentType": "application/json",
                "data": JSON.stringify(mainDataToSend)
            };
            $.ajax(settings11).done(function (msg) {
                console.log(msg);
                if(msg.flag){
                    alert("Sucessfully Updated")
                    closePage()
                }
                else{
                    alert(msg.message)
                }
            });
        }
        else{
            var template_name = prompt("Please enter Template name", "");
            if (nullCheck(template_name)) {
                mainDataToSend.template_name = template_name;
                mainDataToSend.file_name = file_id;
                mainDataToSend.case_id = case_id;
                mainDataToSend.img_width = $("#imageCountNum0").width();
                mainDataToSend.resize_factor = $("#imageCountNum0").width()/670;
                mainDataToSend.retrain = retrain;

                console.log(mainDataToSend);
                var form = new FormData();
                form.append("file", JSON.stringify(mainDataToSend));
                var settings11 = {
                    "async": true,
                    "crossDomain": true,
                    "url": dynamicUrl+"/train",
                    "method": "POST",
                    "processData": false,
                    "contentType": "application/json",
                    "data": JSON.stringify(mainDataToSend)
                };
                $.ajax(settings11).done(function (msg) {
                    console.log(msg);
                    if(msg.flag){
                        alert("Sucessfully Updated")
                        closePage()
                    }
                    else{
                        alert(msg.message)
                    }
                });
            }
        }
    })

    $("body").on("click", ".closeBtn", function(){
        closePage()
    })

    function closePage() {
        docUrl = (window.location != window.parent.location) ? document.referrer : document.location.href
        docArr = docUrl.split('/');
        url_ = ''
        for (i = 0; i<6; i++){
            url_ += docArr[i] + '/';
        }
        window.top.location = url_;
    }

    $("body").on("click", ".swaping", function () {
        id = $(this).attr('key');
        target = $(this).attr('target');
        a = $(".keyword-final-"+id+"-"+target).val()
        b = $(".value-final-"+id+"-"+target).val()
        $(".keyword-final-"+id+"-"+target).val(b);
        $(".value-final-"+id+"-"+target).val(a)
    })

    function get_Ocr(reslt, box_id) {
        text = '';
        for (var i = 0; i < reslt.length; i++) {
            text = text +' '+ reslt[i].word;
        }
        text_= $.trim(text);
        // text_ = "This is sample input text"

        $(".inputLabel-"+box_id).val(text_)
        $(".parent_input_here-"+box_id).html('');
        $(".parent_input_here-"+box_id).attr('title', text_)
        for (var i = 0; i < text_.length; i++) {
            $(".parent_input_here-"+box_id).append('<span class="span'+i+'">'+text_[i]+'</span>');
        }
        console.log(alt_title);
        sliderdrag(box_id, "unlock");
    }

    var keywordDraged = '';

    function sliderdrag(id, state){
        if (alt_title == 'fieldmap') {
            class_name_drag = '.field_map_rows '
        }
        else {
            class_name_drag = ''
        }
        if(state=="unlock"){
            $(class_name_drag+".drag-"+id).draggable({
                containment: class_name_drag+".parent_main-"+id,
                axis: "x",
                stop: function(e){
                    key = $(this).attr('key');
                    target = $(this).attr('target');
                    inputVal = $(class_name_drag+".inputLabel-"+key+"-"+target).val();

                    style = $(this).css("left")
                    xPos = style.replace('left: ','').replace('px','');
                    xPos = Number(xPos)-21-4;

                    len = $(class_name_drag+".parent_input_here-"+key+"-"+target+" span").length;

                    spanCount = 0;

                    for (i = 0; i < len; i++) {
                        spanCount = spanCount + $(class_name_drag+".parent_input_here-"+key+"-"+target+" .span"+i).width();
                        if (spanCount>xPos) {
                            break;
                        }
                    }
                    string1 = inputVal.substring(0, i);
                    keywordDraged = string1
                    string2 = inputVal.substring(i, inputVal.length)

                    $(class_name_drag+".keyword-final-"+id).val($.trim(string1))
                    $(class_name_drag+".value-final-"+id).val($.trim(string2))

                }
            });
        }
        else {
            $(class_name_drag+".drag-"+id).draggable("destroy");
        }
    }


    function showRetrinedData(dt__){
        alt_title = 'field'

        noPages = $(".imageCount").length;
        pagesObj = {};
        for (i = 0; i < noPages; i++){
            pagesObj[i] = []
        }
        $.each(dt__, function(k, v){
            if(nullCheck(k)){
                v.field = k
                v.validation = nullCheck(v.validation) ? v.validation : 'NONE'
                pagesObj[v.box['page']].push(v)
                console.log(JSON.stringify(pagesObj))
            }
        })

        default_op_optns = '<option value="">Select Field</option>'

        for (var i = 0; i < default_Output_fields.length; i++) {
            if (default_Output_fields[i].indexOf('Table.') == -1) {
                if (Object.values(already_selected).indexOf(default_Output_fields[i][0]) == -1) {
                    default_op_optns = default_op_optns + '<option value="'+default_Output_fields[i]+'">'+default_Output_fields[i]+'</option>';
                }
            }
        }

        class_name_field = 'displayresults';
        valid_options = '<option value="NONE">Select Validation</option><option value="Remove Junk">Remove Junk</option>';
        // for (var i = 0; i < validationsArr.length; i++) {
        //     if (validationsArr[i] != 'NONE') {
        //         valid_options = valid_options + '<option value="'+validationsArr[i]+'">'+validationsArr[i]+'</option>'
        //     }
        // }
        width_ = $(".imageCount").width();

        $.each(pagesObj, function(k , v){
            fieldsArrData = []
            for(i = 0; i < v.length; i++){
                obj = {};
                obj.x = resizeFactor(width_, v[i].box.x) - 5;
                obj.y = resizeFactor(width_, v[i].box.y) - 5;
                obj.z = 0;
                obj.page = v[i].box.page;
                obj.width = resizeFactor(width_, v[i].box.width) + 10;
                obj.height = resizeFactor(width_, v[i].box.height) + 10;
                obj.id = i;
                console.log(obj)
                fieldsArrData.push(obj)

                tr = '<div class="col-sm-12 fieldTrain recd-'+i+'-'+k+'" id="'+i+'" target="'+k+'" ty="new" split="no" >'
                tr += '<div class="outputBody">'
                tr += '<div class="row fieldValid-'+i+'-'+k+'" style="border-bottom: 1px solid #c9c9c9;height: 30px !important;">'
                tr += '<div class="col-sm-6 padding0">'
                tr += '<select class="mods_inputs keywordSelect keyword-'+i+'-'+k+'">'+default_op_optns+'</select>'
                tr += '</div>'
                tr += '<div class="col-sm-6 padding0">'
                tr += '<select key="'+i+'" target="'+k+'" class="mods_inputs validationLabel validationLabel-'+i+'-'+k+'">'+valid_options+'</select>'
                tr += '</div>'
                tr += '</div>'
                tr += '<div class="parent_main parent_main-'+i+'-'+k+'" style="height: 31px;">'
                tr += '<input type="text" class="inputLabel inputLabel-'+i+'-'+k+' hideInput" value="'+v[i].box_value+'"> '
                tr += '<div class="parent_input_here parent_input_here-'+i+'-'+k+'" title="'+v[i].box_value+'">'

                for(j = 0; j < v[i].box_value.length; j++){
                    tr += '<span class="span'+j+'">'+v[i].box_value[j]+'</span>'
                }

                tr += '</div>'
                tr += '<div class="drag drag-'+i+'-'+k+'" key="'+i+'" target="'+k+'">'
                tr += '<div class="triangle-down"></div>'
                tr += '<div class="triangle-up"></div>'
                tr += '</div>'
                tr += '</div>'
                tr += '<div class="row s99p keyValRow-'+i+'-'+k+'">'
                tr += '<div class="col-sm-6">'
                tr += '<input class="mods_inputs keyword-final-'+i+'-'+k+'" placeholder="Keyword">'
                tr += '</div>'
                tr += '<div class="col-sm-6">'
                tr += '<input class="mods_inputs value-final-'+i+'-'+k+'" placeholder="Value">'
                tr += '</div>'
                tr += '</div>'
                tr += '<img src="images/md-swap.svg" class="swaping swap-'+i+'-'+k+'" key="'+i+'" target="'+k+'" width="15px">'

                tr += '<img src="images/2D.png" class="extraCrps croping2d" key="'+i+'" target="'+k+'" title="2D Training">'
                tr += '<img src="images/CT.png" class="extraCrps cropingContext" key="'+i+'" target="'+k+'" title="Context Training">'
                tr += '</div>'
                tr += '</div>'

                $("."+class_name_field).append(tr);

                $('.keyword-'+i+'-'+k).val(v[i].field)

                sliderdrag(i+'-'+k, "unlock");
                // vld = v[i].validation == "" ? "NONE" : v[i].validation
                $('.validationLabel-'+i+'-'+k).val(v[i].validation)
                $('.inputLabel-'+i+'-'+k).val(v[i].box_value)
                $('.keyword-final-'+i+'-'+k).val(v[i].keyword)
                $('.value-final-'+i+'-'+k).val(v[i].value)

            }


            $("#imageCountNum"+k).selectAreas({
                onChanged: debugHeaderAreas,
                width: width_,
                areas: fieldsArrData
            });
        })
        $("select").formSelect();
    }

    $("body").on("dblclick", ".parent_main", function (e) {
        // var splt = confirm("Are you sure want to split?");
        splt = true;
        if(splt == true) {
            boxData = $(this).parent().parent();
            id = boxData.attr('id');
            target = boxData.attr('target');
            $('.splitDiv-'+id+'-'+target).remove()

            $(".fieldValid-"+id+'-'+target).addClass('displayNone')
            $(".keyValRow-"+id+'-'+target).addClass('visibilityHidden')
            $(".swap-"+id+'-'+target).addClass('displayNone')

            $(this).parent().append('<span class="splitThis splitThis-'+id+'-'+target+'" id="'+id+'" target="'+target+'">Split</span>');

            spltsCount = $('.spltsNew-'+id+'-'+target).length;
            e.stopPropagation();
            wrapper = $(this).parent();
            parentOffset = wrapper.offset();
            lft = e.pageX - parentOffset.left + wrapper.scrollLeft() + 21 - 5;

            fieldSplits += 1;

            // $(this).append('<div class="drag spltsNew-'+id+'-'+target+' drag-'+id+'-'+target+'-'+spltsCount+'" key="'+id+'" target="'+target+'" count="'+spltsCount+'" style="left:'+lft+'px"><div class="triangle-down"></div><div class="triangle-up"></div><img src="images/redDelete.svg" class="splitDelete"></div>')
            $(this).append('<div class="drag spltsNew-'+id+'-'+target+' drag-'+id+'-'+target+'-'+spltsCount+'" key="'+id+'" target="'+target+'" count="'+spltsCount+'" style="left:'+lft+'px"><div class="triangle-down"></div><div class="triangle-up"></div></div>')

            sliderdrag(id+'-'+target+'-'+spltsCount, "unlock");
        }
        else {

        }
    })

    $("body").on("click", ".splitDelete", function () {
        $(this).parent().remove();
    })

    $("body").on("click", ".splitThis", function () {
        thiss = $(this);
        id = $(this).attr('id');
        target = $(this).attr('target');
        v = '';
        string2 = ''

        $(".recd-"+id+"-"+target).attr('split', 'yes')
        $('.splitDiv-'+id+'-'+target).remove();
        tltSplits = $('.spltsNew-'+id+'-'+target).length

        default_op_optns = '<option value="">Select Field</option>'

        for (var i = 0; i < default_Output_fields.length; i++) {
            if (default_Output_fields[i].indexOf('Table.') == -1) {
                if (Object.values(already_selected).indexOf(default_Output_fields[i][0]) == -1) {
                    default_op_optns = default_op_optns + '<option value="'+default_Output_fields[i]+'">'+default_Output_fields[i]+'</option>';
                }
            }
        }

        valid_options = '<option value="NONE">Select Validation</option><option value="Remove Junk">Remove Junk</option>';
        // for (var i = 0; i < validationsArr.length; i++) {
        //     if (validationsArr[i] != 'NONE') {
        //         valid_options = valid_options + '<option value="'+validationsArr[i]+'">'+validationsArr[i]+'</option>'
        //     }
        // }

        validation_select = '<select key="'+id+'" target="'+target+'" class="mods_inputs validationLabel validationLabel-'+id+'-'+target+'">'+valid_options+'</select>'
        prevVal = 0;
        for(i = 0; i <= tltSplits; i++){
            tr = '<div class="col-sm-12 splitDiv-'+id+'-'+target+' recd-'+id+'-'+target+'-'+i+'" splitId="'+i+'" id="'+id+'" target="'+target+'" ty="new">'
            tr += '<div class="outputBody">'
            tr += '<div class="row fieldValid-'+id+'-'+target+'" style="border-bottom: 1px solid #c9c9c9;height: 30px !important;">'
            tr += '<div class="col-sm-6 padding0">'
            tr += '<select class="mods_inputs keywordSelect keyword-'+id+'-'+target+'-'+i+'">'+default_op_optns+'</select>'
            tr += '</div>'
            tr += '<div class="col-sm-6 padding0">'
            tr += '<select key="'+id+'" target="'+target+'" class="mods_inputs validationLabel validationLabel-'+id+'-'+target+'">'+valid_options+'</select>'
            tr += '</div>'
            tr += '</div>'
            tr += '<div class="parent_main parent_main-'+id+'-'+target+'" style="height: 31px;">'
            tr += '<input type="text" class="inputLabel inputLabel-'+id+'-'+target+' hideInput" value=""> '

            v = $(".inputLabel-"+id+"-"+target).val();
            strtfrom = 0;
            if (i > 0) {
                style = $('.drag-'+key+'-'+target+'-'+(i-1)).css("left");
                // if (nullCheck(style)) {
                startFrom = style.replace('left: ','').replace('px','')-25;
                prevVal = startFrom
                // }
                // else {
                //     startFrom = prevVal
                // }
            }
            else {
                style = $('.drag-'+key+'-'+target).css("left");
                startFrom = style.replace('left: ','').replace('px','')-25;
                prevVal = startFrom
            }
            endPoint = 0
            got = 0;
            if (i == tltSplits) {
                endPoint = $(".parent_input_here-"+id+'-'+target).width()-25;
            }
            else {
                // ij_c = i
                // while (!nullCheck($('.drag-'+id+'-'+target+'-'+ij_c).css("left"))) {
                //     if(ij_c <= tltSplits){
                //         ij_c++
                //     }
                //     else {
                //         got = 1;
                //         endPoint = $(".parent_input_here-"+id+'-'+target).width()-25;
                //         break;
                //     }
                // }
                // if (got == 0) {
                style = $('.drag-'+id+'-'+target+'-'+i).css("left");
                endPoint = style.replace('left: ','').replace('px','')-25;
                // }
            }

            console.log(i +'-start-'+ Number(startFrom)+' ---end-'+Number(endPoint));

            spanCount1 = 0;
            for (ij1 = 0; ij1 < v.length; ij1++) {
                spanCount1 = spanCount1 + $(".parent_input_here-"+key+"-"+target+" .span"+ij1).width();
                if (spanCount1 > startFrom) {
                    break;
                }
            }
            spanCount2 = 0;
            for (ij2 = 0; ij2 < v.length; ij2++) {
                spanCount2 = spanCount2 + $(".parent_input_here-"+key+"-"+target+" .span"+ij2).width();
                if(spanCount2 > endPoint){
                    break;
                }
            }

            string2 = v.substring(ij1, ij2)
            // string2 = string2.substring(0, ij2)

            keywordDraged = $.trim(keywordDraged)
            string2 = $.trim(string2)

            console.log(v,"-----------" ,string2)
            tr += '<div class="parent_input_here parent_input_here-'+id+'-'+target+' parent_input_here-'+id+'-'+target+'-'+i+'" title="'+keywordDraged+' '+string2+'">'

            for (j = 0; j < keywordDraged.length; j++) {
                tr += '<span>'+keywordDraged[j]+'</span>'
            }
            for (j = 0; j < string2.length; j++) {
                tr += '<span>'+string2[j]+'</span>'
            }

            // for(j = strtfrom; j < v.length; j++){
            //     tr += '<span>'+v[j]+'</span>'
            // }

            tr += '</div>'
            tr += '<div class="drag drag-'+id+'-'+target+'" key="'+id+'" target="'+target+'">'
            tr += '<div class="triangle-down"></div>'
            tr += '<div class="triangle-up"></div>'
            tr += '</div>'
            tr += '</div>'
            tr += '<div class="row s99p keyValRow-'+id+'-'+target+'">'
            tr += '<div class="col-sm-6">'
            tr += '<input class="mods_inputs keyword-final-'+id+'-'+target+'-'+i+'" placeholder="Keyword" value="'+keywordDraged+'">'
            tr += '</div>'
            tr += '<div class="col-sm-6">'
            tr += '<input class="mods_inputs value-final-'+id+'-'+target+'-'+i+'" placeholder="Value" value="'+string2+'">'
            tr += '</div>'
            tr += '</div>'
            tr += '<img src="images/trash.svg" class="deleteSplitField" key="'+id+'" target="'+target+'" split="'+i+'" width="15px">'
            tr += '</div>'
            tr += '</div>'

            sessionStorage.setItem('validation-'+id+'-'+target+'-'+i, JSON.stringify({"pattern":"NONE","globalCheck":false}));

            // thiss.parent().parent().append(tr);
            $(tr).insertAfter(thiss.parent().parent())
        }
        $("select").formSelect();

    })

    $("body").on("click", ".deleteSplitField", function () {
        $(this).parent().parent().remove()
    })

    $("body").on("click", ".backToHeader", function () {
        nofiles = $(".imageCount").length;
        if (!nullCheck(all_cropped_data_history['field'])) {
            all_cropped_data_history['field'] = {};
        }
        for (var i = 0; i < nofiles; i++) {
            all_cropped_data_history['field'][i] = $('#imageCountNum'+i).selectAreas('areas');
            $('#imageCountNum'+i).selectAreas('destroy');
        }

        if (nullCheck(all_cropped_data_history['header'])) {
            header_areas = all_cropped_data_history['header'];
        }
        else {
            header_areas = []
        }

        alt_title = 'header'

        for (var i = 0; i < nofiles; i++) {
            width_ = $(".imagesCountNum"+i).width();
            $("#imageCountNum"+i).selectAreas({
                onChanged: debugHeaderAreas,
                width: width_,
                areas: header_areas[i]
            });
        }
        console.log(all_cropped_data_history);
    });

    function rte(box, w) {
        //console.log(box, w);
        key = box.page;
        ui_box = Object.assign({}, box);
        words_in_box = [];
        resize_factor1 = w/default_width;

        ui_box["width"] = Number(ui_box["width"] / resize_factor1)
        ui_box["height"] = Number(ui_box["height"] / resize_factor1)
        ui_box["y"] = Number(ui_box["y"] / resize_factor1)
        ui_box["x"] = Number(ui_box["x"] / resize_factor1)

        box_t = ui_box['y']
        box_r = ui_box['x'] + ui_box['width']
        box_b = ui_box['y'] + ui_box['height']
        box_l = ui_box['x']

        words_in_box = []
        // img_ocr_data = JSON.parse(localStorage.getItem('ocr'))
        for (var i = 0; i < img_ocr_data[key].length; i++) {
            word_t = img_ocr_data[key][i]['top']
            word_r = img_ocr_data[key][i]['left'] + img_ocr_data[key][i]['width']
            word_b = img_ocr_data[key][i]['top'] + img_ocr_data[key][i]['height']
            word_l = img_ocr_data[key][i]['left']
            if ((box_l <= word_l && word_r <= box_r) && (box_t <= word_t && word_b <= box_b)){
                words_in_box.push(img_ocr_data[key][i])
            }
        }
        //console.log(words_in_box);
        return words_in_box;
    }

    function table_rte(box, imgWidth) {
        key = nullCheck(box.page) ? box.page : 0;
        ui_box = Object.assign({}, box);
        words_in_box = [];
        resize_factor1 = imgWidth/default_width;

        ui_box["w"] = Number(ui_box["w"] / resize_factor1)
        ui_box["h"] = Number(ui_box["h"] / resize_factor1)
        ui_box["t"] = Number(ui_box["t"] / resize_factor1)
        ui_box["l"] = Number(ui_box["l"] / resize_factor1)

        box_t = ui_box['t']
        box_r = ui_box['l'] + ui_box['w']
        box_b = ui_box['t'] + ui_box['h']
        box_l = ui_box['l']

        words_in_box = []
        // img_ocr_data = JSON.parse(localStorage.getItem('ocr'))
        for (var i = 0; i < img_ocr_data[key].length; i++) {
            word_t = img_ocr_data[key][i]['top']
            word_r = img_ocr_data[key][i]['left'] + img_ocr_data[key][i]['width']
            word_b = img_ocr_data[key][i]['top'] + img_ocr_data[key][i]['height']
            word_l = img_ocr_data[key][i]['left']
            if ((box_l-(0.25 * img_ocr_data[key][i]['width']) <= word_l && word_r <= box_r + (0.25 * img_ocr_data[key][i]['width'])) && (box_t <= word_t && word_b <= box_b)){
                words_in_box.push(img_ocr_data[key][i])
            }
        }
        return words_in_box;
    }

    //All needed from plugins

    //pdf to image
    function previewPdfFile(file) {
        loadXHR(file).then(function(blob) {
            var reader = new FileReader();
            reader.onload = function (e) {
                pdftoimg(e.target.result)
            }
            reader.readAsDataURL(blob);
        });
    }

    function loadXHR(url) { return new Promise(function(resolve, reject) {
        try {
            var xhr = new XMLHttpRequest();
            xhr.open("GET", url);
            xhr.responseType = "blob";
            xhr.onerror = function() {reject("Network error.")};
            xhr.onload = function() {
                if (xhr.status === 200) {
                    resolve(xhr.response)}
                    else {reject("Loading error:" + xhr.statusText)}
                };
                xhr.send();
            }
            catch(err) {reject(err.message)}
        });
    }

    function pdftoimg(file) {
        imagesArr = [];
        window.PDFJS = window.pdfjsLib;
        PDFJS.disableWorker = true;
        PDFJS.getDocument(file).then(function getPdfHelloWorld(pdf) {
            const go = async function(){
                let h = 0;
                for(var pageN = 1; pageN <= pdf.numPages; pageN++){
                    const page = await pdf.getPage(pageN);
                    var scale = 2;
                    var viewport = page.getViewport(scale);
                    //
                    // Prepare canvas using PDF page dimensions
                    //
                    var canvas = document.createElement('canvas');
                    //document.body.appendChild(canvas);
                    var context = canvas.getContext('2d');
                    canvas.height += viewport.height;
                    canvas.width = viewport.width;
                    //
                    // Render PDF page into canvas context
                    //
                    var task = page.render({ canvasContext: context, viewport: viewport })
                    await task.promise;
                    pages = canvas.toDataURL('image/jpeg');
                    imagesArr.push(pages)
                    if (pageN == pdf.numPages) {
                        displayImage(imagesArr)
                    }
                }
            };
            go();
        }, function(error){
            //console.log(error);
        });
    }

    // tiff to image
    function previewTiffFile(file) {
        var xhr = new XMLHttpRequest();
        xhr.responseType = 'arraybuffer';
        xhr.open('GET', file);
        xhr.onload = function (e) {
            var tiff = new Tiff({buffer: xhr.response});
            imagefiles = [];
            tiff_count = tiff.countDirectory();
            //console.log(tiff_count);
            for (var i = 0; i < tiff_count; i++) {
                tiff.setDirectory(i);
                var canvas = tiff.toCanvas();
                imagefiles.push(canvas.toDataURL())
                //console.log(tiff.countDirectory(), imagefiles);
            }
            var canvas = tiff.toCanvas();
            displayImage(imagefiles)
            // //console.log(canvas.toDataURL());
        };
        xhr.send();
    }


    $("body").on("click", ".delete_col", function () {
        del = $(this).hasClass('trash');
        if (del) {
            id = $(this).parent().attr('id')
            // delete table_alias_already_selected[id];
            $(this).parent().addClass('disabledcol');
            $(this).removeClass('trash');
            $(this).attr('src', 'images/redo-solid.svg');
            $(this).addClass('repeat');
            $(this).parent().attr('del', 'yes')
        }
        else {
            $(this).parent().removeClass('disabledcol');
            $(this).removeClass('repeat');
            $(this).attr('src', 'images/trash.svg');
            $(this).addClass('trash');
            $(this).parent().attr('del','no')
        }
    })

    selectedExtraCrop = ''
    selectedExtraCropBox = '';
    changedAreasCount = []

    $("body").on("click", ".croping2d", function(){
        $(".invoiceName").html(file_name)
        id = $(this).attr('key');
        target = $(this).attr('target');
        splitId = $(this).attr('split');

        key = id+'-'+target
        if (nullCheck(splitId)) {
            key += '-'+splitId
        }
        selectedExtraCropBox = key

        extraTrainingFields[key] = {}
        extraTrainingFields[key].type = '2D';
        extraTrainingFields[key].coordinates = [];
        console.log(extraTrainingFields)
        imgs = $(".imageCount")
        for (var i = 0; i < imgs.length; i++) {
            $(".displayHereImages").append('<img src="'+imgs[i].attributes.src.value+'" id="imgCount-'+i+'" class="newImgCount imgCount-'+i+'" alt="'+i+'" width="100%">')
            console.log(imgs[i].attributes.src.value);
        }

        for (var i = 0; i < imgs.length; i++) {
            width_ = $("#imgCount-"+i).width();

            $("#imgCount-"+i).selectAreas({
                onChanged: debugAreas,
                width: width_,
                maxAreas: 4
            });
        }

        $(".extraTrainingDiv").show()
        t_ = 0;
        for (var i = 0; i < target; i++) {
            t_ += $('imgCount-'+i).height();
        }
        allCrops = $('#imageCountNum'+target).selectAreas('areas')
        oldWidth = $('#imageCountNum'+target).width();
        crp = allCrops[id];
        w = newCord(crp['width'])
        h = newCord(crp['height'])
        t = newCord(crp['y']) + t_
        l = newCord(crp['x'])
        $(".highlighted").remove();
        $(".displayHereImages").append('<div class="highlighted" style="left:'+l+'px; top:'+t+'px; width:'+w+'px; height:'+h+'px; "></div>')

    })

    $("body").on("click", ".cropingContext", function(){
        $(".invoiceName").html(file_name)
        id = $(this).attr('key');
        target = $(this).attr('target');
        splitId = $(this).attr('split');

        key = id+'-'+target
        if (nullCheck(splitId)) {
            key += '-'+splitId
        }
        selectedExtraCropBox = key

        extraTrainingFields[key] = {}
        extraTrainingFields[key].type = 'Context';
        extraTrainingFields[key].coordinates = [];
        console.log(extraTrainingFields)

        imgs = $(".imageCount")
        for (var i = 0; i < imgs.length; i++) {
            $(".displayHereImages").append('<img src="'+imgs[i].attributes.src.value+'" id="imgCount-'+i+'" class="newImgCount imgCount-'+i+'" alt="'+i+'" width="100%">')
            console.log(imgs[i].attributes.src.value);
        }

        for (var i = 0; i < imgs.length; i++) {
            width_ = $("#imgCount-"+i).width();

            $("#imgCount-"+i).selectAreas({
                onChanged: debugAreas,
                width: width_,
                maxAreas: 1
            });
        }

        $(".extraTrainingDiv").show()
        t_ = 0;
        for (var i = 0; i < target; i++) {
            t_ += $('imgCount-'+i).height();
        }
        allCrops = $('#imageCountNum'+target).selectAreas('areas')
        oldWidth = $('#imageCountNum'+target).width();
        crp = allCrops[id];
        w = newCord(crp['width'])
        h = newCord(crp['height'])
        t = newCord(crp['y']) + t_
        l = newCord(crp['x'])
        $(".highlighted").remove();
        $(".displayHereImages").append('<div class="highlighted" style="left:'+l+'px; top:'+t+'px; width:'+w+'px; height:'+h+'px; "></div>')

    })

    function newCord(value){
        oldWidth = $('#imageCountNum0').width();
        newWidth = $("#imgCount-0").width();
        return value*(newWidth/oldWidth)
    }

    function newCord1(value){
        oldWidth = $('#imageCountNum0').width();
        newWidth = $("#imgCount-0").width();
        return value*(oldWidth/newWidth)
    }

    debugAreas = function debugAreas (event, id, areas) {
        target = event.target.alt;
        if (nullCheck(areas[id])) {
            areas[id].page = target;

            rteData = rte(areas[id], $("#imgCount-0").width());

            console.log(rteData);
            // rteData = rte();
            text = '';
            for (var i = 0; i < rteData.length; i++) {
                text = text +' '+ rteData[i].word;
            }
            text_= $.trim(text);

            if($(".freeText-"+id+"-"+target).length == 0){
                $(".displayHereContent").append('<div class="freeText freeText-'+id+'-'+target+'">'+text_+'</div>')
            }
            else {
                $(".freeText-"+id+"-"+target).html(text_)
            }

        }
        changedAreasCount = areas
        console.log("debugAreas", text, event, id, JSON.stringify(areas), extraTrainingFields[selectedExtraCropBox])
    }

    $("body").on("click", ".extraTrainingDivCancel", function () {
        changedAreasCount = []
        for (var i = 0; i < imgs.length; i++) {
            width_ = $("#imgCount-"+i).width();

            $("#imgCount-"+i).selectAreas('destroy');
        }

        $(".recd-"+selectedExtraCropBox).find('.extraCrps').removeClass('active');

        if(extraTrainingFields[selectedExtraCropBox].type == '2D' && extraTrainingFields[selectedExtraCropBox].coordinates.length > 0) {
            $(".recd-"+selectedExtraCropBox).find('.croping2d').addClass('active');
        }
        else if(extraTrainingFields[selectedExtraCropBox].type == 'Context' && extraTrainingFields[selectedExtraCropBox].coordinates.length > 0) {
            $(".recd-"+selectedExtraCropBox).find('.cropingContext').addClass('active');
        }

        $(".displayHereImages").html('');
        $(".displayHereContent").html('');
        $(".extraTrainingDiv").hide();
    })

    $("body").on("click", ".extraTrainingDivSave", function () {
        areas_C = Object.assign({}, {'key': changedAreasCount})
        areasC = areas_C.key;
        arr = []
        for (var i = 0; i < areasC.length; i++) {
            obj = {}
            obj.x = newCord1(areasC[i].x)
            obj.y = newCord1(areasC[i].y)
            obj.width = newCord1(areasC[i].width)
            obj.height = newCord1(areasC[i].height)
            obj.page = areasC[i].page;
            obj.id = areasC[i].id;
            obj.z = 0;
            arr.push(obj)
        }
        console.log(arr, changedAreasCount);
        extraTrainingFields[selectedExtraCropBox].coordinates = arr
        console.log(extraTrainingFields);
        for (var i = 0; i < imgs.length; i++) {
            width_ = $("#imgCount-"+i).width();

            $("#imgCount-"+i).selectAreas('destroy');
        }

        $(".recd-"+selectedExtraCropBox).find('.extraCrps').removeClass('active');

        if(extraTrainingFields[selectedExtraCropBox].type == '2D') {
            $(".recd-"+selectedExtraCropBox).find('.croping2d').addClass('active');
        }
        else if(extraTrainingFields[selectedExtraCropBox].type == 'Context') {
            $(".recd-"+selectedExtraCropBox).find('.cropingContext').addClass('active');
        }
        $(".displayHereImages").html('');
        $(".displayHereContent").html('');
        $(".extraTrainingDiv").hide();
    })


    function displayTableTrainedData(tblData) {
        $(".allTableResults").append('<div class="stage2"></div><div class="stage2Btns"><button method="tnox" class="waves-effect waves-light btn-small mr-t-10 light-blue mr-r-20 mr-b-20 proceedVers removeThis" onclick="return false;">Train</button></div>')
        headerTrainedData = {}
        footerTrainedData = {}
        $.each(tblData, function (k, v) {
            if (k.toLowerCase().indexOf('v') == 0) {
                headerTrainedData[k] = v
            }
            else {
                footerTrainedData[k] = v
            }
        })
        optns = '<option value="">Select Alias</option>'
        console.log(default_Output_fields);
        for (var i = 0; i < default_Output_fields.length; i++) {
            if (default_Output_fields[i].indexOf('Table.') > -1) {
                tableField = default_Output_fields[i].replace('Table.', '')
                optns += '<option value="'+tableField+'">'+tableField+'</option>'
            }
        }

        $.each(headerTrainedData, function (k, v) {
            cc = k.split('v');
            cc_ = cc[1].split('.');
            sub = 'splits="no"'
            if (cc_.length > 1) {
                sub = 'splits="yes" sub="'+cc_[1]+'"'
            }
            cls = ''
            if (v['del'] == 'yes') {
                cls = 'disabledcol'
            }
            vv  = '<div class="removeAllHeaders box '+cls+' box-v box-'+k+'" del="'+v['del']+'" id="'+cc_[0]+'" '+sub+'>'
            vv += '<div class="">'
            vv += '<p style="float: left;">'+k+'</p>'
            vv += '<input type="text" placeholder="Label" name="" value="'+v['label']+'" class="label_inputs label_name">'
            vv += '<div class="clear__"></div>'
            vv += '</div>'
            vv += '<div class="">'
            vv += '<select class="label_inputs alias_change alias_change'+k+' thisOpt mr-b-0">'+optns+'</select>'
            vv += '</div>'
            if(v['del'] == 'yes') {
                vv += '<image src="images/redo-solid.svg" class="delete_col repeat">'
            }
            else {
                vv += '<image src="images/trash.svg" class="delete_col trash">'
            }
            vv += '<div>'
            vv += '<label>'
            chk = v['ref'] ? 'checked' : ''
            vv += '<input class="with-gap" name="group1" type="radio" '+chk+'/>'
            vv += '<span>Ref key</span>'
            vv += '</label>'
            vv += '<label class="mr-l-20">'
            chk1 = v['field'] ? 'checked' : ''
            vv += '<input type="checkbox" class="filled-in markField" '+chk1+'/>'
            vv += '<span>Mark as field</span>'
            vv += '</label>'
            vv += '<div class="fieldSelectDiv">'
            if (chk1) {
                field_opts = '<option value="">Select Type</option>'
                field_opts = '<option value="kh_vh">Key, Values in Header</option>'
                field_opts += '<option value="kh_vc">Key in Header, Value in Column</option>'
                vv += '<select class="label_inputs fieldOpts'+k+' mr-b-0">'+field_opts+'</select>'
            }
            vv += '</div>'
            vv += '</div>'
            vv += '</div>'
            $(".stage2").append(vv);

            $(".alias_change"+k).val(v['alias'].replace('Table.', ''))
            if (chk1) {
                $(".fieldOpts"+k).val(v['field_type'])
            }

        })

        $.each(footerTrainedData, function (k, v) {
            i = k.toLowerCase().split('v')[1]
            vv  = '<div class="removeAllHeaders box" del="no">'
            vv += '<div class="">'
            vv += '<p style="float: left;">Footer'+i+'</p>'
            vv += '<input type="text" placeholder="Label" name="" value="'+v['label']+'" class="label_inputs label_name footerData">'
            vv += '<div class="clear__"></div>'
            vv += '</div>'
            vv += '</div>'
            $(".stage2").append(vv);
        })

        $("select").formSelect();
        console.log(headerTrainedData, footerTrainedData);
    }
})

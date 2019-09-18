$(document).ready(function () {
    logThis(2, "Page Loaded")

    var nextClicked = false;
    var footerData;

    var default_Output_fields = ["PO Number","Table.Base Amount","Table.Total Amount", "Invoice Number", "Invoice Date", "Invoice Total","CGST Amount","SGST Amount","Invoice Base amount","Table.GST %","IGST Amount","DRL GSTIN","Vendor GSTIN","Billed To (DRL Name)","DC Number","Document heading","Table.HSN/SAC","Table.Product description","GST %","HSN/SAC","Table.Quantity","Table.Rate","Table.CGST %","Table.SGST %", "Table.CGST Amount","Table.SGST Amount","Table.IGST %","Table.IGST Amount","Vendor name","Table.PO Number"]

    var headerCropAreas = {}, vendor_crop_data={}, tableCrops = {};
    var tableFinalCrops;
    var all_cropped_data_history = {};
    var mainAreasCount=[];
    var already_selected = {};
    var initial_training_arr = ["header_ocr", "address_ocr", "footer_ocr"];

    var last_selected = 'header';
    var alt_title = 'header';

    var mainDataToSend = {};
    var ocr_data;

    var file_id = getUrlParameter('file_name');
    var case_id = getUrlParameter('case_id');
    case_id = case_id.split('.')[0];

    file_name = 'images/invoices/'+file_id;
    if (nullCheck(file_name)) {
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


        sendObj = {};
        sendObj.file_name = file_id;
        sendObj.case_id = case_id;

        console.log(sendObj);

        var form = new FormData();
        form.append("file", JSON.stringify(sendObj));
        var settings11 = {
            "async": true,
            "crossDomain": true,
            "url": "http://192.168.0.147:5002/get_ocr_data",
            "method": "POST",
            "processData": false,
            "contentType": false,
            "mimeType": "multipart/form-data",
            "data": form
        };
        $.ajax(settings11).done(function (msg) {
            // msg = '{"flag": true, "data": [[]]}'
            console.log(msg);
            msg = JSON.parse(msg)

            if (msg.flag) {
                // if (nullCheck(msg.fields)) {
                //     default_Output_fields = msg.fields;
                // }
                console.log(default_Output_fields);
                ocr_data = JSON.parse(msg.ocr_data);
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
                    rteData = rte(ocr_data, areas[area_indx], $("#imageCountNum0").width());

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
                        ht += '<div class="input-field col s11">'
                        ht += '<select class="mods_inputs getcropvendor getcropvendor-'+id+'-'+target+'" key="'+id+'" target="'+target+'" style="margin-bottom: 20px;">'
                        ht += '<option value="" disabled selected>Select Crop</option>'
                        ht += '<option value="header_ocr">Header</option>'
                        ht += '<option value="address_ocr">Address</option>'
                        ht += '<option value="footer_ocr">Footer</option>'
                        ht += '</select>'
                        // ht += '<label>Select Type</label>'
                        ht += '</div>'
                        // ht += '<div class="input-field col s1">'
                        // ht += '<img typ="vndr" class="delete_crop_field" src="images/trash.svg" width="17px" id="'+id+'" target="'+target+'">'
                        // ht += '</div>'
                        ht += '</div>'
                        $(".vendorValidation").append(ht);
                        $('.getcropvendor-'+id+'-'+target).val(initial_training_arr[inital_ct]);

                        inital_ct += 1;
                    }
                }
                else if ((a < b)  && nullCheck(areas)) {
                    $(".vndr-"+id+"-"+target).remove();
                    vendor_crop_data[initial_training_arr[inital_ct]] = {};
                    inital_ct = inital_ct - 1;
                }
            }
            else if (alt_title == 'field') {
                box_id = id+"-"+target;
                arrCount = $(".displayresults")[0].children.length;
                mainAreasCount[target] = areas;
                for (var i = 0; i < mainAreasCount.length; i++) {
                    if (!nullCheck(mainAreasCount[i])) {
                        mainAreasCount[i] = [];
                    }
                    a += mainAreasCount[i].length
                }
                if (arrCount < a) {
                    valid_options = '<option value="NONE">Select Validation</option><option value="NONE">NONE</option>';
                    // for (var i = 0; i < validationsArr.length; i++) {
                    //     if (validationsArr[i] != 'NONE') {
                    //         valid_options = valid_options + '<option value="'+validationsArr[i]+'">'+validationsArr[i]+'</option>'
                    //     }
                    // }
                    console.log(default_Output_fields);
                    default_op_optns = '<option value="">Select Field</option>'
                                array.push(obj)
            array.push(obj)
//            array.push(obj)
            array.push(obj)
//            array.push(obj)
            array.push(obj)
//            array.push(obj)
            array.push(obj)
//            array.push(obj)
            array.push(obj)
//debugger
                    for (var i = 0; i < default_Output_fields.length; i++) {
                        // if (Object.values(already_selected).indexOf(default_Output_fields[i][0]) == -1) {
                        // if (default_Output_fields[i][1] == selectedFile[14] || default_Output_fields[i][1] == 'All') {
                        //     default_op_optns = default_op_optns + '<option value="'+default_Output_fields[i][0]+'">'+default_Output_fields[i][0]+'</option>';
                        // }
                        // else {
                        if (default_Output_fields[i].indexOf('Table.') == -1) {
                            default_op_optns = default_op_optns + '<option value="'+default_Output_fields[i]+'">'+default_Output_fields[i]+'</option>';
                        }
                        // }
                        // }
                    }
                    // <select class="mods_inputs keyword-'+id+'-'+target+'"></select>
                    $(".displayresults").append('<div class="col-sm-12 recd-'+id+'-'+target+'" id="'+id+'" target="'+target+'" ty="new"> <div class="outputBody"> <div class="row" style="border-bottom: 1px solid #c9c9c9;height: 30px !important;"> <div class="col-sm-6 padding0"> <select class="mods_inputs keywordSelect keyword-'+id+'-'+target+'">'+default_op_optns+'</select> </div><div class="col-sm-6 padding0"> <select key="'+id+'" target="'+target+'" class="mods_inputs validationLabel validationLabel-'+id+'-'+target+'">'+valid_options+'</select> </div></div><div class="parent_main parent_main-'+id+'-'+target+'" style="height: 31px;"> <input type="text" class="inputLabel inputLabel-'+id+'-'+target+' hideInput" value=""> <div class="parent_input_here parent_input_here-'+id+'-'+target+'"></div><div class="drag drag-'+id+'-'+target+'" key="'+id+'" target="'+target+'"> <div class="triangle-down"></div><div class="triangle-up"></div></div></div><div class="row s99p"> <div class="col-sm-6"> <input class="mods_inputs keyword-final-'+id+'-'+target+'" placeholder="Keyword"> </div><div class="col-sm-6"> <input class="mods_inputs value-final-'+id+'-'+target+'" placeholder="Value"> </div></div><img src="images/md-swap.svg" class="swaping swap-'+id+'-'+target+'" key="'+id+'" target="'+target+'" width="15px"><img class="delete_crop_field" src="images/trash.svg" width="17px" id="'+id+'" target="'+target+'"></div></div>');

                    $("select").formSelect();

                    sessionStorage.setItem('validation-'+id+'-'+target, JSON.stringify({"pattern":"NONE","globalCheck":false}));
                    ar_ind = areas.findIndex(x => x.id==id);
                    areas[ar_ind].page = target;
                    areas[ar_ind].record = 'new';

                    croped = areas[ar_ind];
                    reslt = rte(ocr_data, croped, $("#imageCountNum0").width());
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
                    reslt = rte(ocr_data, croped, $("#imageCountNum0").width());
                    //console.log(reslt);

                    get_Ocr(reslt, box_id)
                }
            }
            else if (alt_title == 'table') {
                tableCrops[target] = areas
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
                    tableFinalCrops = Object.assign({}, areas);
                    tbl = '<p>'
                    tbl += '<label>'
                    tbl += '<input type="checkbox" class="filled-in headerCheck"/>'
                    tbl += '<span>Is Header is repeatable?</span>'
                    tbl += '</label>'
                    tbl += '</p>'
                    tbl += '<p>'
                    tbl += '<label>'
                    tbl += '<input type="checkbox" class="filled-in footerCheck"/>'
                    tbl += '<span>Are you want to show Footer?</span>'
                    tbl += '</label>'
                    tbl += '</p>'
                    tbl += '<button class="waves-effect waves-light btn-small mr-t-10 tryAbbyTable"  onclick="return false;">Proceed</button>'

                    $(".intialTableConfirm").html(tbl)
                }
            }
            $("select").formSelect();
        }
    }


    $("body").on("click", ".nextToFields", function () {
        nextClicked = true
        nofiles = $(".imageCount").length;

        mainDataToSend.template = Object.assign({}, vendor_crop_data);

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

    })

    $("body").on("click", ".nextToTable", function () {
        nextClicked = true
        mainArr = [];
        totalboxess = $(".displayresults")[0].children.length;

        empt___ = 0;

        for (var ii = 0; ii < totalboxess; ii++) {
            id = $(".displayresults")[0].children[ii].attributes['id'].value;
            target = $(".displayresults")[0].children[ii].attributes['target'].value;
            box_id = id+"-"+target;
            var areas = $('#imageCountNum'+target).selectAreas('areas');

            if (areas.length > 0) {
                inx = areas.findIndex(x => x.id==id)
                codd = areas[inx];

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
                mainObj.coordinates = codd;
                mainObj.width = width_;
                mainObj.page = areas[inx].page;

                if (nullCheck(mainObj.keyword) || nullCheck(mainObj.value)) {
                    mainArr.push(mainObj);
                }
                if (!nullCheck(mainObj.field) || (!nullCheck(mainObj.value) && !nullCheck(mainObj.keyword))) {
                    empt___ = 1;
                }

            }
        }
        mainDataToSend.field = Object.assign({}, mainArr);

        for (var i = 0; i < nofiles; i++) {
            $('#imageCountNum'+i).selectAreas('destroy');
        }

        console.log(mainDataToSend);

        $(".allTableResults").html('<p>Crop the Header and Footer of the table</p><div class="intialTableConfirm mr-t-10"></div><div class="allTablesShow mr-t-20" style="overflow-x: auto;"></div><div class="anyBtns mr-t-20"></div>')

        setTimeout(function () {
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
        }, 1000);
    })

    // tableResponse = [[[[[['<b>SR. NO.</b>', 1, 1], ['<b>PRODUCT DESCRIPTION</b>', 1, 1], ['<b>ITEM CODE</b>', 1, 1], ['<b>HSN CODE</b>', 1, 1], ['<b>BATCH NUMBER</b>', 1, 1], ['<b>EXPIRY DATE</b>', 1, 1], ['<b>TOTAL QUANTITY</b>', 1, 1], ['<b>PKG/ DRUM</b>', 1, 1], ['<b>UOM</b>', 1, 1], ['<b>MRP</b>', 1, 1], ['<b>UNIT PRICE</b>', 1, 1], ['<b>TAXABLE VALUE</b>', 1, 1], ['<b>FREIGHT</b>', 1, 1], ['<b>TOTAL TAXABLE VALUE</b>', 1, 1], ['<b>IGST RATE AMOUNT</b>', 1, 1], ['<b>CGST RATE AMOUNT</b>', 1, 1], ['<b>SGST RATE AMOUNT</b>', 1, 1]], [['', 1, 1], [' 1 ATARAX 6MG/ML 15ML DRO IN', 1, 1], [' FDA00001', 1, 1], [' 30049099', 1, 1], [' LI0418015', 1, 1], [' suspicious11/2020', 1, 1], [' 96240.00', 1, 1], [' 401', 1, 1], [' EA', 1, 1], [' 48.00', 1, 1], [' 8.02', 1, 1], [' 771845.00', 1, 1], ['', 1, 1], [' 771845.00', 1, 1], [' 12.00 92621.00', 1, 1], ['', 1, 1], ['', 1, 1]]], [[[' Total', 1, 1], [' 96240.00 771845.00 771845.00 92621.00', 1, 1]]]],["SR. NO.","PRODUCT DESCRIPTION","ITEM CODE","HSN CODE","BATCH NUMBER","EXPIRY DATE","TOTAL QUANTITY","PKG/ DRUM","UOM","MRP","UNIT PRICE","TAXABLE VALUE","FREIGHT","TOTAL TAXABLE VALUE","IGST RATE AMOUNT","CGST RATE AMOUNT","SGST RATE AMOUNT"], {'hors': [[[13, 195], [655, 195]], [[13, 212], [655, 212]], [[13, 232], [655, 232]]], 'vers': [[[13, 195], [13, 232]], [[16, 195], [16, 232]], [[135, 195], [135, 232]], [[166, 195], [166, 232]], [[193, 195], [193, 232]], [[230, 195], [230, 232]], [[256, 195], [256, 232]], [[289, 195], [289, 232]], [[311, 195], [311, 232]], [[331, 195], [331, 232]], [[352, 195], [352, 232]], [[380, 195], [380, 232]], [[420, 195], [420, 232]], [[448, 195], [448, 232]], [[480, 195], [480, 232]], [[541, 195], [541, 232]], [[598, 195], [598, 232]], [[655, 195], [655, 232]]]}]]

    abbyyTrainObj = {}
    $("body").on("click", ".tryAbbyTable", function () {
        sendObj = {};
        sendObj.table_data = {};
        sendObj.table_data.coordinates = tableFinalCrops;
        sendObj.table_data.headerCheck = $(".headerCheck").is(":checked");
        sendObj.table_data.footerCheck = $(".footerCheck").is(":checked");
        // sendObj.ocr_data = ocr_data;
        sendObj.file_name = file_id;
        sendObj.case_id = case_id;
        sendObj.method = 'abbyy'
        sendObj.img_width = $(".showImgs ").width();
        abbyyTrainObj = sendObj
        console.log(sendObj);
        var form = new FormData();
        form.append("file", JSON.stringify(sendObj));
        var settings11 = {
            "async": true,
            "crossDomain": true,
            "url": "http://192.168.0.147:5018/predict_with_ui_data",
            "method": "POST",
            "processData": false,
            "contentType": false,
            "mimeType": "multipart/form-data",
            "data": form
        };
        $.ajax(settings11).done(function (msg) {
            console.log(msg);
            tableResponse = JSON.parse(msg);

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
    $("body").on("click", ".confirm_table", function(){
        $(".displayTrainedTable").remove();
        header_lines = [];
        header_lines_temp = [];
        split_lines_temp = [];
        ver_splt_lines_temp = [];

        ver_splits=[];
        initial_hor = [];
        hor_init = []

        $(".allTableResults").append('<div class="stage2"></div>')

        width_ = $(".imageCountNum0").width();

        hor_init = $(".hor_gen_ver");

        firstLine = {}

        firstLine.h= hor_init[0].offsetHeight
        firstLine.l = hor_init[0].offsetLeft
        firstLine.t = hor_init[0].offsetTop
        firstLine.w = hor_init[0].offsetWidth
        firstLine.page = hor_init[0].attributes.page.value;

        secondline = {}

        secondline.h= hor_init[1].offsetHeight
        secondline.l = hor_init[1].offsetLeft
        secondline.t = hor_init[1].offsetTop
        secondline.w = hor_init[1].offsetWidth
        secondline.page = hor_init[1].attributes.page.value;

        thirdline = {}

        thirdline.h= hor_init[2].offsetHeight
        thirdline.l = hor_init[2].offsetLeft
        thirdline.t = hor_init[2].offsetTop
        thirdline.w = hor_init[2].offsetWidth
        thirdline.page = hor_init[2].attributes.page.value;

        forthline = {}

        forthline.h= hor_init[3].offsetHeight
        forthline.l = hor_init[3].offsetLeft
        forthline.t = hor_init[3].offsetTop
        forthline.w = hor_init[3].offsetWidth
        forthline.page = hor_init[3].attributes.page.value;

        header_hors = [firstLine, secondline, thirdline, forthline]

        // console.log(hor_init, header_hors);

        ver_init = $(".vertical_line");
        ver_lines = []

        for (var i = 0; i < ver_init.length; i++) {
            // ver_init[i]
            obj = {}
            obj.h= ver_init[i].offsetHeight
            obj.l = ver_init[i].offsetLeft
            obj.t = ver_init[i].offsetTop
            obj.w = ver_init[i].offsetWidth
            obj.page = ver_init[i].attributes.page.value;
            ver_lines.push(obj)
        }

        console.log(header_hors, ver_lines);

        getHeaderLines(header_hors, ver_lines)


    })

    function getHeaderLines(hors, vers) {
        var headerVerSplits = [];
        var footerVerSplits = [];
        for (var i = 0; i < vers.length; i++) {
            if (vers[i].t <= hors[1].t) {
                headerVerSplits.push(vers[i])
            }
            else {
                footerVerSplits.push(vers[i])
            }
        }
        console.log(headerVerSplits, footerVerSplits);

        headers = []
        finalCrops = []
        for (var i = 0; i < headerVerSplits.length-1; i++) {
            obj = {};
            obj.t = hors[0].t + 5;
            obj.h = hors[1].t - hors[0].t;
            obj.w = headerVerSplits[i+1].l - headerVerSplits[i].l;
            obj.l = headerVerSplits[i].l + 5;
            obj.page = hors[0].page;
            finalCrops.push(obj)

            reslt = table_rte(ocr_data, obj, $("#imageCountNum0").width());
            // reslt = ["Sample text"];
            console.log(obj, reslt);
            text = ''
            for (var jk = 0; jk < reslt.length; jk++) {
                text = text +' '+ reslt[jk].word+ ' ';
            }
            prev_value = text;

            headers.push(prev_value)
            console.log(headers);

            $(".showImgs").append('<div class="pos_ab" style="border: 1px solid blue; top:'+obj.t+'px; left:'+obj.l+'px; width:'+obj.w+'px; height:'+obj.h+'px"></div>');
            // $(".header_crop").hide()
        }

        footers = []
        for (var i = 0; i < footerVerSplits.length; i++) {
            obj = {};
            obj.t = hors[2].t + 5;
            obj.h = hors[3].t - hors[2].t;
            obj.w = footerVerSplits[i].l - hors[2].l;
            obj.l = hors[i].l + 5;
            obj.page = hors[2].page;
            finalCrops.push(obj)

            reslt = table_rte(ocr_data, obj, $("#imageCountNum0").width());
            // reslt = ["Sample text"];
            console.log(obj, reslt);
            text = ''
            for (var jk = 0; jk < reslt.length; jk++) {
                text = text +' '+ reslt[jk].word+ ' ';
            }
            prev_value = $.trim(text);

            footers.push(prev_value)
        }
        console.log(footers);
        footerData = footers
        displayHeaders(headers, "tnox")
    }

    function displayHeaders(headers, method_) {
        optns = '<option value="">Select Alias</option>'
        console.log(default_Output_fields);
        for (var i = 0; i < default_Output_fields.length; i++) {
            if (default_Output_fields[i].indexOf('Table.') > -1) {
                optns += '<option value="'+default_Output_fields[i]+'">'+default_Output_fields[i]+'</option>'
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
        for (var i = 0; i < vrs.length; i++) {
            text = vrs[i].children[0].children[0].innerText;
            obj = {};
            obj.label = vrs[i].children[0].children[1].value;
            obj.del = vrs[i].attributes.del.value;
            obj.alias = vrs[i].children[1].children[0].children[3].value;
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

        if (method__ != 'abbyy') {
            final_arr['h2v1'] = {};
            final_arr['h2v1'].label = footerData[0];
            final_arr['h2v1'].type = "";
            final_arr['h2v1'].del = "no"
            final_arr['h2v1'].alias = ""
            final_arr['h2v1'].ref = false
            final_arr['h2v1'].field = false
        }

        console.log(final_arr);
        sendObj = {};
        sendObj.table_data = abbyyTrainObj.table_data
        sendObj.table_data.trained_data = final_arr;
        sendObj.method = method__;
        sendObj.file_name = file_id;
        sendObj.case_id = case_id;
        sendObj.img_width = $(".showImgs ").width();

        final_table_save = {}
        final_table_save.table_data = sendObj.table_data;
        final_table_save.method = method__;


        mainDataToSend.table = final_table_save
        console.log(sendObj);
        var form = new FormData();
        form.append("file", JSON.stringify(sendObj));
        var settings11 = {
            "async": true,
            "crossDomain": true,
            "url": "http://192.168.0.147:5018/predict_with_ui_data",
            "method": "POST",
            "processData": false,
            "contentType": false,
            "mimeType": "multipart/form-data",
            "data": form
        };
        $.ajax(settings11).done(function (msg) {
            console.log(msg);
            msg = JSON.parse(msg)[0][0];
            $(".displayTrainedTable").remove();
            $(".allTableResults").append('<div class="displayTrainedTable" style="overflow-x: auto;"></div>')
            table_generate_display(msg, "displayTrainedTable")
        });

    })

    $("body").on("click", ".saveBtn", function () {
        console.log(mainDataToSend);
        var template_name = prompt("Please enter Template name", "");
        if (nullCheck(template_name)) {
            mainDataToSend.template_name = template_name;
            mainDataToSend.file_name = file_id;
            mainDataToSend.case_id = case_id;
            mainDataToSend.img_width = $("#imageCountNum0").width();
            var form = new FormData();
            form.append("file", JSON.stringify(mainDataToSend));
            var settings11 = {
                "async": true,
                "crossDomain": true,
                "url": "http://192.168.0.147:5003/update_database",
                "method": "POST",
                "processData": false,
                "contentType": false,
                "mimeType": "multipart/form-data",
                "data": form
            };
            $.ajax(settings11).done(function (msg) {
                console.log(msg);
                alert("Sucessfully Updated")
            });
        }
    })

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
        sliderdrag(box_id, "unlock");
    }

    function sliderdrag(id, state){
        if(state=="unlock"){
            $(".drag-"+id).draggable({
                containment: ".parent_main-"+id,
                axis: "x",
                stop: function(e){
                    key = $(this).attr('key');
                    target = $(this).attr('target');
                    inputVal = $(".inputLabel-"+key+"-"+target).val();

                    style = $(this).attr('style')
                    stylrArr = style.split('; ')
                    xPos = stylrArr[0].replace('left: ','').replace('px','');
                    xPos = xPos-21-4;

                    len = $(".parent_input_here-"+key+"-"+target+" span").length;

                    spanCount = 0;

                    for (i = 0; i < len; i++) {
                        spanCount = spanCount + $(".parent_input_here-"+key+"-"+target+" .span"+i).width();
                        if (spanCount>xPos) {
                            break;
                        }
                    }
                    String1 = inputVal.substring(0, i);
                    String2 = inputVal.substring(i, inputVal.length)

                    $(".keyword-final-"+id).val($.trim(String1))
                    $(".value-final-"+id).val($.trim(String2))

                }
            });
        }
        else {
            $(".drag-"+id).draggable("destroy");
        }
    }



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


    //from OCR rte


    // function rte() {
    //     return ["this is sample text"]
    // }

    function rte(ocr_data_, box, w) {
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
        for (var i = 0; i < ocr_data_[key].length; i++) {
            word_t = ocr_data_[key][i]['top']
            word_r = ocr_data_[key][i]['left'] + ocr_data_[key][i]['width']
            word_b = ocr_data_[key][i]['top'] + ocr_data_[key][i]['height']
            word_l = ocr_data_[key][i]['left']
            if ((box_l <= word_l && word_r <= box_r) && (box_t <= word_t && word_b <= box_b)){
                words_in_box.push(ocr_data_[key][i])
            }
        }
        //console.log(words_in_box);
        return words_in_box;
    }

    function table_rte(ocr_data_, box, imgWidth) {
        key = box.page;
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
        for (var i = 0; i < ocr_data_[key].length; i++) {
            word_t = ocr_data_[key][i]['top']
            word_r = ocr_data_[key][i]['left'] + ocr_data_[key][i]['width']
            word_b = ocr_data_[key][i]['top'] + ocr_data_[key][i]['height']
            word_l = ocr_data_[key][i]['left']
            if ((box_l-(0.25 * ocr_data_[key][i]['width']) <= word_l && word_r <= box_r + (0.25 * ocr_data_[key][i]['width'])) && (box_t <= word_t && word_b <= box_b)){
                words_in_box.push(ocr_data_[key][i])
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




})

default_width = 670;
var logs = []

var getUrlParameter = function getUrlParameter(sParam) {
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
};


var nullCheck = function nullCheck(val) {
    if (val == undefined || val == null || val == "") {
        return false;
    } else {
        return true;
    }
}

var logThis = function logThis(line, content) {
    console.log("Line: " + line, content)
}

function resizeFactor(width_, value) {
    return value * (width_ / 670);
    // return value*1;
}

function resizeFactor1(width_, value) {
    return value * 1;
}

function logIntoPage(message, color) {
    var today = new Date();
    var time = today.getHours() + ":" + today.getMinutes() + ":" + today.getSeconds();

    $(".log_details").append("<div style='color:" + color + "'>" + time + "  -  " + message + "</div>")
}

var highlight_list = {
    "Billed To (DRL Name)": {
        "width": "74.6269",
        "height": "20.9403",
        "y": "308",
        "x": "16",
        "page": "0"
    },
    "Document Heading": {
        "width": "74.6269",
        "height": "20.9403",
        "y": "308",
        "x": "100",
        "page": "0"
    },
    "Invoice Category": {
        "width": "74.6269",
        "height": "20.9403",
        "y": "308",
        "x": "96",
        "page": "0"
    }
}



function hovering(highlight_list) {
    $("body").on("click", ".hovering", function () {
        // console.log(f_crop_clicked);

        hvr = $(this).find('label').html();
        hvr = $.trim(hvr)
        // console.log(hvr);
        v = highlight_list[hvr];
        $(".selectCropShow2").remove();
        if (nullCheck(v)) {
            adj_top_ = v.page;
            adj_top = 0;
            zoom = 1;
            blb = $(".imageCountNum" + adj_top_).attr("src");
            for (var i = 0; i < adj_top_; i++) {
                adj_top += $(".imageCountNum" + i).height();
            }
            // width_ = $(".HorZOn").width() * zoom;
            width_ = $(".HorZOn").width() * zoom;
            x = resizeFactor(width_, v.x) - 10;
            top_check = resizeFactor(width_, v.y);
            top_ = adj_top + (top_check) - 10;
            y = resizeFactor(width_, v.y) - 7;
            w = resizeFactor(width_, v.width) + 25 + 25;
            h = resizeFactor(width_, v.height) + 15 + 15;

            $(".HorZOn").append("<div class='selectCropShow2'></div>");

            glass = $(".selectCropShow2");
            console.log(glass, x, y, w, h);
            // glass.css("background", "url('" + blb + "')")

            // ww = $(".selectCropShow").width()/2;
            // hh = $(".selectCropShow").height()/2;

            glass.css({
                "left": x + "px",
                "top": top_ + "px",
                "width": w + "px",
                "height": h + "px"
            })
            // glass.style.backgroundPosition =
            // $(".scrollingPos").animate({scrollTop: (top_ - 300)},500);
        }


    });

}




function hovering2(highlight_list) {
 
    var  index=0;
    $.each(highlight_list,function(k,v){

        if (nullCheck(v)) {
            adj_top_ = v.page;
            adj_top = 0;
            zoom = 1;
            blb = $(".imageCountNum" + adj_top_).attr("src");
            for (var i = 0; i < adj_top_; i++) {
                adj_top += $(".imageCountNum" + i).height();
            }
            // width_ = $(".HorZOn").width() * zoom;
            width_ = $(".HorZOn").width() * zoom;
            x = resizeFactor(width_, v.x) - 10;
            top_check = resizeFactor(width_, v.y);
            top_ = adj_top + (top_check) - 10;
            y = resizeFactor(width_, v.y) - 7;
            w = resizeFactor(width_, v.width) + 25 + 25;
            h = resizeFactor(width_, v.height) + 15 + 15;

            $(".HorZOn").append("<div class='selectCropShow' id=selectCropShow"+index+"></div>");

            glass = $("#selectCropShow"+index);


            glass.css({
                "left": x + "px",
                "top": top_ + "px",
                "width": w + "px",
                "height": h + "px"
            })

        }
        index=index+1;
    })
}


function toast(msg, type) {
    switch (type) {
        case 'error':
            toastr.error(msg)
            break;
        case 'success':
            toastr.success(msg)
            break;
        default:
            toastr.info(msg)
    }
}

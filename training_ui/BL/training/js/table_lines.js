var m_t, m_r, m_b, m_l;

function table_line_draw(tableData) {
    m_t = 0, m_r = 0; m_b = 0, m_l = 0;
    width_ = $(".imageCount")[0].width;
    console.log(width_);

    if (nullCheck(tableData.hors)) {
        ww = resizeFactor1(width_, tableData.hors[0][1][0]);

        m_l = resizeFactor1(width_, tableData.hors[0][0][0]);
        m_r = ww - m_l;

        for (var i = 0; i < tableData.hors.length; i++) {
            x1 = resizeFactor1(width_, tableData.hors[i][0][0]);
            y1 = resizeFactor1(width_, tableData.hors[i][0][1]);
            x2 = resizeFactor1(width_, tableData.hors[i][1][0]);
            y2 = resizeFactor1(width_, tableData.hors[i][1][1]);

            hor_width = x2-x1;
            if (hor_width == 0) {
                hor_width = 2;
            }
            hor_height = 12
            hor_left = x1;
            hor_top = y1;
            points = {};
            points.top = hor_top - 7
            points.left = hor_left
            points.height = hor_height
            points.width = hor_width;

            drawHorLines(i, points, "top", 0, "inital_res")
        }
    }
    if (nullCheck(tableData.vers)) {
        hh = resizeFactor1(width_, tableData.vers[0][1][1]);
        m_t = resizeFactor1(width_, tableData.vers[0][0][1]);
        m_b = hh - m_t;
        for (var i = 0; i < tableData.vers.length; i++) {
            points = {};
            x1 = resizeFactor1(width_, tableData.vers[i][0][0]);
            y1 = resizeFactor1(width_, tableData.vers[i][0][1]);
            x2 = resizeFactor1(width_, tableData.vers[i][1][0]);
            y2 = resizeFactor1(width_, tableData.vers[i][1][1]);
            ver_width = 10;
            ver_height = y2-y1;
            if (ver_height == 0) {
                ver_height = 2;
            }
            ver_left = x1;
            ver_top = y1;
            points.top = ver_top-5
            points.left = ver_left
            points.height = ver_height+11
            points.width = ver_width
            drawVerLines(i, points, 0)
        }
    }
}

function adjtop(id) {
    adj_top = 0;
    for (var i = 0; i < id; i++) {
        adj_top += $('img.imageCountNum'+i).height();
    }
    return adj_top
}

function drawHorLines(i, points, tp='null', idd, cls__) {
    delll = ''
    if(!nullCheck(cls__)){
        delll = '<i class="fa fa-trash delete_line del_hor" key="'+i+'" aria-hidden="true"></i>'
    }
    $(".showImgs").append('<div class="'+cls__+' header_crop table_crop hor_gen_ver horizontal_line drawThis horizontal_line'+i+'" page="'+idd+'" tp="'+tp+'" id="'+i+'" style="top: '+(adjtop(idd)+points.top)+'px; left: '+points.left+'px; height: '+points.height+'px; width: '+points.width+'px;"><div class="hor_line">'+delll+'<img src="images/arrow.svg" alt="" class="left_move" width="15px"><img src="images/arrow.svg" alt="" class="right_move" width="15px"></div></div>');
    resize_hor();
    drag_y();
    return '';
}
function drawVerLines(i, points) {
    $(".displayImages").width();
    $(".showImgs").append('<div class="header_crop table_crop vertical_line vertical_line'+i+'" id="'+i+'" style="cursor: col-resize; top: '+(points.top)+'px; left: '+points.left+'px; height: '+points.height+'px; width: '+points.width+'px; z-index: 999;"><div class="ver_line"><i class="fa fa-trash delete_line del_ver" key="'+i+'" aria-hidden="true"></i><img src="images/arrow.svg" width="15px" alt="" class="top_move"><img src="images/arrow.svg" width="15px" alt="" class="bottom_move"></div></div>')
    $(".delete_line").hide();
    resize_ver();
    drag_x();
    return '';
}
function resize_hor() {
    $(".horizontal_line").resizable({
        handles: "w, e",
        containment: $(".image_box"),
        minHeight: 5
    });
}

function drag_y() {
    $(".horizontal_line").draggable({
        axis: "y",
        containment: $(".image_box")
    });
}

function resize_ver() {
    $(".vertical_line").resizable({
        handles: "n, s",
        containment: $(".image_box"),
        minHeight: 5
    });
}

function drag_x() {
    $(".vertical_line").draggable({
        axis: "x",
        containment: $(".image_box")
    });
}

$("body").on("click", ".del_ver",function () {
    $(this).parent().parent().remove();
});

$("body").on("click", ".del_hor", function () {
    $(this).parent().parent().remove();
});

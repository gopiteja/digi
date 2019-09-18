var href='second.html'
function openModal() {
    $("#ruleModal").modal()
}
//
// function getStensilLable(){
//     var stensilLable=[
//         "Process 1","Process 2","Process 3"
//     ]
//     return stensilLable;
// }

$("body").on("click", ".testCheck", function () {
    // $("#testModal").modal();
    window.open(href);
})

$("body").on("click", ".testBtn", function () {
    testJson = $(".testTextArea").val();
    console.log(testJson)
    // app = new App.MainView({ el: '#app' })
    console.log(App.config.sampleGraphs.emergencyProcedure);
    app.graph.fromJSON(App.config.sampleGraphs.emergencyProcedure);
})

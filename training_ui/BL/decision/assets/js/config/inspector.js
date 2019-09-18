

var App = App || {};
App.config = App.config || {};


var options = {

    colorPalette: [
        { content: 'transparent', icon: 'assets/transparent-icon.svg' },
        { content: '#f6f6f6' },
        { content: '#dcd7d7' },
        { content: '#8f8f8f' },
        { content: '#c6c7e2' },
        { content: '#feb663' },
        { content: '#fe854f' },
        { content: '#b75d32' },
        { content: '#31d0c6' },
        { content: '#7c68fc' },
        { content: '#61549c' },
        { content: '#6a6c8a' },
        { content: '#4b4a67' },
        { content: '#3c4260' },
        { content: '#33334e' },
        { content: '#222138' }
    ],

    colorPaletteReset: [
        { content: undefined, icon: 'assets/no-color-icon.svg' },
        { content: '#f6f6f6' },
        { content: '#dcd7d7' },
        { content: '#8f8f8f' },
        { content: '#c6c7e2' },
        { content: '#feb663' },
        { content: '#fe854f' },
        { content: '#b75d32' },
        { content: '#31d0c6' },
        { content: '#7c68fc' },
        { content: '#61549c' },
        { content: '#6a6c8a' },
        { content: '#4b4a67' },
        { content: '#3c4260' },
        { content: '#33334e' },
        { content: '#222138' }
    ],

    fontWeight: [
        { value: '300', content: '<span style="font-weight: 300">Light</span>' },
        { value: 'Normal', content: '<span style="font-weight: Normal">Normal</span>' },
        { value: 'Bold', content: '<span style="font-weight: Bolder">Bold</span>' }
    ],

    fontFamily: [
        { value: 'Alegreya Sans', content: '<span style="font-family: Alegreya Sans">Alegreya Sans</span>' },
        { value: 'Averia Libre', content: '<span style="font-family: Averia Libre">Averia Libre</span>' },
        { value: 'Roboto Condensed', content: '<span style="font-family: Roboto Condensed">Roboto Condensed</span>' }
    ],

    strokeStyle: [
        { value: '0', content: 'Solid' },
        { value: '2,5', content: 'Dotted' },
        { value: '10,5', content: 'Dashed' }
    ],

    side: [
        { value: 'top', content: 'Top Side' },
        { value: 'right', content: 'Right Side' },
        { value: 'bottom', content: 'Bottom Side' },
        { value: 'left', content: 'Left Side' }
    ],

    portLabelPositionRectangle: [
        { value: { name: 'top', args: { y: -12 }}, content: 'Above' },
        { value: { name: 'right', args: { y: 0 }}, content: 'On Right' },
        { value: { name: 'bottom', args: { y: 12 }}, content: 'Below' },
        { value: { name: 'left', args: { y: 0 }}, content: 'On Left' }
    ],

    portLabelPositionEllipse: [
        { value: 'radial' , content: 'Horizontal' },
        { value: 'radialOriented' , content: 'Angled' }
    ],

    imageIcons: [
        { value: 'assets/image-icon1.svg', content: '<img height="42px" src="assets/image-icon1.svg"/>' },
        { value: 'assets/image-icon2.svg', content: '<img height="80px" src="assets/image-icon2.svg"/>' },
        { value: 'assets/image-icon3.svg', content: '<img height="80px" src="assets/image-icon3.svg"/>' },
        { value: 'assets/image-icon4.svg', content: '<img height="80px" src="assets/image-icon4.svg"/>' }
    ],

    imageGender: [
        { value: 'assets/member-male.png', content: '<img height="50px" src="assets/member-male.png" style="margin: 5px 0 0 2px;"/>' },
        { value: 'assets/member-female.png', content: '<img height="50px" src="assets/member-female.png" style="margin: 5px 0 0 2px;"/>' }
    ],

    arrowheadSize: [
        { value: 'M 0 0 0 0', content: 'None' },
        { value: 'M 0 -3 -6 0 0 3 z', content: 'Small' },
        { value: 'M 0 -5 -10 0 0 5 z', content: 'Medium' },
        { value: 'M 0 -10 -15 0 0 10 z', content: 'Large' },
    ],

    strokeWidth: [
        { value: 1, content: '<div style="background:#fff;width:2px;height:30px;margin:0 14px;border-radius: 2px;"/>' },
        { value: 2, content: '<div style="background:#fff;width:4px;height:30px;margin:0 13px;border-radius: 2px;"/>' },
        { value: 4, content: '<div style="background:#fff;width:8px;height:30px;margin:0 11px;border-radius: 2px;"/>' },
        { value: 8, content: '<div style="background:#fff;width:16px;height:30px;margin:0 8px;border-radius: 2px;"/>' }
    ],

    router: [
        { value: 'normal', content: '<p style="background:#fff;width:2px;height:30px;margin:0 14px;border-radius: 2px;"/>' },
        { value: 'orthogonal', content: '<p style="width:20px;height:30px;margin:0 5px;border-bottom: 2px solid #fff;border-left: 2px solid #fff;"/>' },
        { value: 'oneSide', content: '<p style="width:20px;height:30px;margin:0 5px;border: 2px solid #fff;border-top: none;"/>' }
    ],

    connector: [
        { value: 'normal', content: '<p style="width:20px;height:20px;margin:5px;border-top:2px solid #fff;border-left:2px solid #fff;"/>' },
        { value: 'rounded', content: '<p style="width:20px;height:20px;margin:5px;border-top-left-radius:30%;border-top:2px solid #fff;border-left:2px solid #fff;"/>' },
        { value: 'smooth', content: '<p style="width:20px;height:20px;margin:5px;border-top-left-radius:100%;border-top:2px solid #fff;border-left:2px solid #fff;"/>' }
    ],

    labelPosition: [
        { value: 30, content: 'Close to source' },
        { value: 0.5, content: 'In the middle' },
        { value: -30, content: 'Close to target' },
    ],

    portMarkup: [
        {
            value: [{
                tagName: 'rect',
                selector: 'portBody',
                attributes: {
                    'width': 20,
                    'height': 20,
                    'x': -10,
                    'y': -10
                }
            }],
            content: 'Rectangle'
        }, {
            value: [{
                tagName: 'circle',
                selector: 'portBody',
                attributes: {
                    'r': 10
                }
            }],
            content: 'Circle'
        }, {
            value: [{
                tagName: 'path',
                selector: 'portBody',
                attributes: {
                    'd': 'M -10 -10 10 -10 0 10 z'
                }
            }],
            content: 'Triangle'
        }],

        ruleOptions: [{
            content: "New Rule",
            value: "new"
        }],
        ruleCheck:[{
            content: "No Rule",
            value: "{}"
        }]
    };

    App.config.inspector = {

        'app.Link': {
            inputs: {
                attrs: {


                },
                router: {

                },
                connector: {

                },
                labels: {
                }
            },
            groups: {
                connection: {
                    label: 'Connection',
                    index: 1
                },
                'marker-source': {
                    label: 'Source marker',
                    index: 2
                },
                'marker-target': {
                    label: 'Target marker',
                    index: 3
                },
                labels: {
                    label: 'Labels',
                    index: 4
                }
            }
        },
        'standard.Rectangle': {
            inputs: {
                attrs: {
                    label: {
                        text: {
                            type: 'content-editable',
                            label: 'Text',
                            group: 'text',
                            index: 1
                        },
                        rule: {
                            type: 'select-button-group',
                            options: options.ruleOptions,
                            label: 'Rule',
                            group: 'text',
                            when: {ne: { 'attrs/label/text': '' }},
                            index: 6,
                            events: {
                                'click': function () {
                                    console.log(this);
                                    openModal();
                                }
                            }
                        }
                    },
                    body: {
                        ruleCheck: {
                            type: 'onlyText',
                            label: 'Bussiness Rule',
                            options: options.ruleCheck,
                            group: 'text',
                            when: {ne: { 'attrs/label/text': '' }},
                            index: 7,
                        }
                    }
                }
            },
            groups: {
                text: {
                    label: 'Text',
                    index: 2
                }
            }
        },
        'standard.Ellipse': {
            inputs: {
                attrs: {
                    label: {
                        text: {
                            type: 'content-editable',
                            label: 'Text',
                            group: 'text',
                            index: 1
                        },
                        rule: {
                            type: 'select-button-group',
                            options: options.ruleOptions,
                            label: 'Rule',
                            group: 'text',
                            when: {ne: { 'attrs/label/text': '' }},
                            index: 6,
                            events: {
                                'click': function () {
                                    console.log(this);
                                    openModal();
                                }
                            }
                        }
                    },
                    body: {
                        ruleCheck: {
                            type: 'onlyText',
                            label: 'Bussiness Rule',
                            options: options.ruleCheck,
                            group: 'text',
                            when: {ne: { 'attrs/label/text': '' }},
                            index: 7,
                        }
                    }
                }
            },
            groups: {
                presentation: {
                    label: 'Presentation',
                    index: 1
                },
                text: {
                    label: 'Text',
                    index: 2
                }
            }
        },
        'standard.Polygon': {
            inputs: {
                attrs: {
                    label: {
                        text: {
                            type: 'content-editable',
                            label: 'Text',
                            group: 'text',
                            index: 1
                        },
                        rule: {
                            type: 'select-button-group',
                            options: options.ruleOptions,
                            label: 'Rule',
                            group: 'text',
                            when: {ne: { 'attrs/label/text': '' }},
                            index: 6,
                            events: {
                                'click': function () {
                                    console.log(this);
                                    openModal();
                                }
                            }
                        }
                    },
                    body: {
                        ruleCheck: {
                            type: 'onlyText',
                            label: 'Bussiness Rule',
                            options: options.ruleCheck,
                            group: 'text',
                            when: {ne: { 'attrs/label/text': '' }},
                            index: 7,
                        }
                    }
                }
            },
            groups: {
                presentation: {
                    label: 'Presentation',
                    index: 1
                },
                text: {
                    label: 'Text',
                    index: 2
                }
            }
        },

    };

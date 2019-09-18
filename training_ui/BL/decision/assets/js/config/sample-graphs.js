/*! Rappid v2.4.0 - HTML5 Diagramming Framework - TRIAL VERSION

Copyright (c) 2015 client IO

2019-05-29


This Source Code Form is subject to the terms of the Rappid Trial License
, v. 2.0. If a copy of the Rappid License was not distributed with this
file, You can obtain one at http://jointjs.com/license/rappid_v2.txt
or from the Rappid archive as was distributed by client IO. See the LICENSE file.*/


var App = App || {};
App.config = App.config || {};

(function() {

    'use strict';

    App.config.sampleGraphs = {

        emergencyProcedure: {
            "cells": [
                {
                    "type": "standard.Rectangle",
                    "position": {
                        "x": 270,
                        "y": 430
                    },
                    "size": {
                        "width": 90,
                        "height": 54
                    },
                    "angle": 0,
                    "id": "70f2031a-4482-4470-bb07-ae8eee456c23",
                    "z": 1,
                    "attrs": {
                        "body": {
                            "stroke": "#31d0c6",
                            "fill": "transparent",
                            "rx": 2,
                            "ry": 2,
                            "width": 50,
                            "height": 30,
                            "strokeDasharray": "0",
                            "ruleCheck": "{'condition':'AND','rules':[{'id':'category','field':'category','type':'integer','input':'select','operator':'equal','value':1}],'valid':'true'}"
                        },
                        "label": {
                            "fontSize": 11,
                            "fill": "#c6c7e2",
                            "text": "Process",
                            "fontFamily": "Roboto Condensed",
                            "fontWeight": "Normal",
                            "strokeWidth": 0
                        },
                        "root": {
                            "dataTooltipPosition": "left",
                            "dataTooltipPositionSelector": ".joint-stencil"
                        }
                    }
                },
                {
                    "type": "standard.Rectangle",
                    "angle": 0,
                    "id": "05b0b070-e64e-413d-84d3-0370804b6523",
                    "z": 2,
                    "attrs": {
                        "body": {
                            "stroke": "#31d0c6",
                            "fill": "transparent",
                            "rx": 2,
                            "ry": 2,
                            "width": 50,
                            "height": 30,
                            "strokeDasharray": "0",
                            "ruleCheck": ""
                        },
                        "label": {
                            "fontSize": 11,
                            "fill": "#c6c7e2",
                            "text": "Process",
                            "fontFamily": "Roboto Condensed",
                            "fontWeight": "Normal",
                            "strokeWidth": 0
                        },
                        "root": {
                            "dataTooltipPosition": "left",
                            "dataTooltipPositionSelector": ".joint-stencil"
                        }
                    }
                },
                {
                    "type": "app.Link",
                    "router": {
                        "name": "normal"
                    },
                    "connector": {
                        "name": "rounded"
                    },
                    "labels": [],
                    "source": {
                        "id": "70f2031a-4482-4470-bb07-ae8eee456c23"
                    },
                    "target": {
                        "id": "05b0b070-e64e-413d-84d3-0370804b6523"
                    },
                    "id": "e1790009-f6be-4587-8a45-3df4819ad842",
                    "z": 3,
                    "attrs": {}
                }
            ]
        }
    };
})();


var App = App || {};
App.config = App.config || {};

(function() {

    'use strict';

    App.config.toolbar = {
        groups: {
            'zoom': { index: 8 },
        },
        tools: [
            {
                type: 'zoom-out',
                name: 'zoom-out',
                group: 'zoom',
                attrs: {
                    button: {
                        'data-tooltip': 'Zoom Out',
                        'data-tooltip-position': 'top',
                        'data-tooltip-position-selector': '.toolbar-container'
                    }
                }
            },
            {
                type: 'label',
                name: 'zoom-slider-label',
                group: 'zoom',
                text: 'Zoom:'
            },
            {
                type: 'zoom-slider',
                name: 'zoom-slider',
                group: 'zoom'
            },
            {
                type: 'zoom-in',
                name: 'zoom-in',
                group: 'zoom',
                attrs: {
                    button: {
                        'data-tooltip': 'Zoom In',
                        'data-tooltip-position': 'top',
                        'data-tooltip-position-selector': '.toolbar-container'
                    }
                }
            }

        ]
    };
})();

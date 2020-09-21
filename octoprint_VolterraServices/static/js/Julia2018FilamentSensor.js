$(function() {
    function JFSViewModel(parameters) {
        var self = this;

        self.popup = undefined;
        self.sensorConfigDialog = undefined;

        self.Config = undefined;
        self.VM_settings = parameters[0];
        self.VM_printerState = parameters[1];
        self.VM_printerProfiles = parameters[2];

        self.sensorEnabled = ko.observable(false);
        self.showExtruder0 = ko.observable(false);
        self.hasExtruder1 = ko.observable(false);
        self.showExtruder1 = ko.observable(false);
        self.showDoor = ko.observable(false);

        var status_text_extruder = function(x) {
            switch (x) {
                case -1:
                    return "Sensor disabled";
                case 0:
                    return "Outage!";
                case 1:
                    return "Filament loaded"
                default:
                    return "Error"
            }
        };

        var status_text_door = function(x) {
            switch (x) {
                case -1:
                    return "Sensor disabled";
                case 0:
                    return "Open!";
                case 1:
                    return "Closed"
                default:
                    return "Error"
            }
        };

        self.testStatus = function(data) {
            
            $.ajax("/plugin/Julia2018FilamentSensor/status");
            // .success(function(data) {
            //     var msg = "";
            //     var type = "info"
            //     // console.log(data);

            //     if (data['sensor_enabled'] == 1) {
            //         msg += "<b>Extruder 0:</b> " + status(data['extruder0']) + "<br/>";
            //         if (data['extruder1'] != undefined)
            //             msg += "<b>Extruder 1:</b> " + status(data['extruder1']) + "<br/>";
            //         if (data['door'] != -1)
            //             msg += "<b>Door:</b> " + status_door(data['door']);
            //     } else {
            //         msg = "<b>Sensing disabled!</b>"
            //         type = "warning"
            //     }

            //     // self.onDataUpdaterPluginMessage("Julia2018FilamentSensor", {type: 'popup', msg, msgType:type, hide:false});
            // })
            // .fail(function(req, status) {
            //     console.log(status)
            //     // self.onDataUpdaterPluginMessage("Julia2018FilamentSensor", {msg: "Error", type:'error', hide:false});
            // });
        };

        self.showSensorConfig = function() {
            self.sensorConfigDialog.modal();
        };

        self.onConfigClose = function() {
            self.VM_settings.saveData();
            self.sensorConfigDialog.modal("hide");
        };


        self.showPopup = function(msg, msgType, hide=true){
            if (self.popup !== undefined){
                self.closePopup();
            }
            var data = {
                title: 'Julia Filament & Door Sensor',
                text: msg,
                type: msgType,
                hide: hide
            };
            self.popup = new PNotify(data);
        };

        self.closePopup = function() {
            if (self.popup !== undefined) {
                self.popup.remove();
            }
        };

        self.onStartup = function() {
            self.sensorConfigDialog = $("#settings_j18fs_config");
        };

        self.onBeforeBinding = function() {
            console.log('Binding JFSViewModel')

            self.Config = self.VM_settings.settings.plugins.Julia2018FilamentSensor;

            var currentProfileData = self.VM_printerProfiles.currentProfileData();
            if (currentProfileData && currentProfileData.hasOwnProperty('extruder')) {
                currentProfileData.extruder.count.subscribe(function(value) {
                    self.hasExtruder1(value >= 2);
                    self.showExtruder1Config(self.hasExtruder1() && self.Config.enabled_extruder1() == 1);
                });
            } else {
                self.hasExtruder1(false);
            }

            self.Config.sensor_enabled.subscribe(function(value) {
                self.sensorEnabled(value == 1);
            });
            self.Config.enabled_extruder0.subscribe(function(value) {
                self.showExtruder0(value == 1);
            });
            self.Config.enabled_extruder1.subscribe(function(value) {
                self.showExtruder1(self.hasExtruder1() && value == 1);
            });
            self.Config.enabled_door.subscribe(function(value) {
                self.showDoor(value == 1);
            });

            console.log(self.VM_settings);

            self.testStatus();
        };

        self.onSettingsShown = function() {
            var currentProfileData = self.VM_printerProfiles.currentProfileData();

            if (currentProfileData && currentProfileData.hasOwnProperty('extruder')) {
                self.hasExtruder1(currentProfileData.extruder.count() >= 2);
            } else {
                self.hasExtruder1(false);
            }
            // self.hasExtruder1(self.VM_printerProfiles.currentProfileData.extruder.count == 2);

            self.sensorEnabled(self.Config.sensor_enabled() == 1);
            self.showExtruder0(self.Config.enabled_extruder0() == 1);
            self.showExtruder1(self.hasExtruder1() && self.Config.enabled_extruder1() == 1);
            self.showDoor(self.Config.enabled_door() == 1);
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "Julia2018FilamentSensor")
                return;

            var msg = "";
            var msgType = "info"
            var hide = true;

            if (data.hasOwnProperty('type') && data.type == "popup") {
                msg = data.msg;
                msgType = data.msgType;
                hide = data.hasOwnProperty('hide') ? data.hide : true;
            } else {
                if (data['sensor_enabled'] == 1) {
                    msg += "<b>Extruder 0:</b> " + status_text_extruder(data['extruder0']) + "<br/>";
                    if (data['extruder1'] != undefined)
                        msg += "<b>Extruder 1:</b> " + status_text_extruder(data['extruder1']) + "<br/>";
                    if (data['door'] != -1)
                        msg += "<b>Door:</b> " + status_text_door(data['door']);
                } else {
                    msg = "<b>Sensing disabled!</b>"
                    type = "warning"
                }
            }

            // self.showPopup(data.msg, data.msgType, (data && data.hasOwnProperty('hide') ? data.hide : true));
            self.showPopup(msg, msgType, hide);
        };
    };


    // This is how our plugin registers itself with the application, by adding some configuration
    // information to the global variable OCTOPRINT_VIEWMODELS
    ADDITIONAL_VIEWMODELS.push([
        // This is the constructor to call for instantiating the plugin
        JFSViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request
        // here is the order in which the dependencies will be injected into your view model upon
        // instantiation via the parameters argument
        ["settingsViewModel", "printerStateViewModel", "printerProfilesViewModel"],

        // Finally, this is the list of selectors for all elements we want this view model to be bound to.
        ["#settings_j18fs"]
    ]);
});
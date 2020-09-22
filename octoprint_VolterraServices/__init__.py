# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.events import Events
import RPi.GPIO as GPIO
from time import sleep
# import flask
from flask import jsonify
from octoprint.server import NO_CONTENT
# import json

'''
Uses Pi's internal pullups.

GPIO states
Open    - HIGH
Closed  - LOW
'''


class VolterraServicesPlugin(octoprint.plugin.StartupPlugin,
                                    octoprint.plugin.EventHandlerPlugin,
                                    octoprint.plugin.TemplatePlugin,
                                    octoprint.plugin.SettingsPlugin,
                                    octoprint.plugin.BlueprintPlugin,
                                    octoprint.plugin.AssetPlugin):
    '''
                      BCM   BOARD
    PIN_EXTRUDER0   = 5     29
    PIN_EXTRUDER1   = 6     31
    PIN_DOOR        = 26    37
    '''

    PIN_EXTRUDER0 = 5
    PIN_EXTRUDER1 = 6
    PIN_DOOR = 26

    '''
    Popup messages
    '''
    def log_info(self, txt):
        self._logger.info(str(txt))

    def log_error(self, txt):
        self._logger.error(txt)

    def popup_notice(self, txt):
        self.log_info(txt)
        self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", msgType="notice", msg=str(txt)))

    def popup_success(self, txt):
        self.log_info(txt)
        self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", msgType="success", msg=str(txt)))

    def popup_error(self, txt):
        self.log_error(txt)
        self._plugin_manager.send_plugin_message(self._identifier, dict(type="popup", msgType="error", hide=False, msg=str(txt)))

    '''
    Settings
    '''
    def format_gcode(self, txt):
        if not self._settings.has([txt]):
            return None
        gcode = self._settings.get([txt])
        if gcode is not None:
            return str(gcode).split(";")

    @property
    def sensor_enabled(self):
        return self._settings.get_boolean(["sensor_enabled"])

    @property
    def enabled_extruder0(self):
        return self._settings.get_boolean(["enabled_extruder0"])

    @property
    def bounce_extruder0(self):
        return self._settings.get_int(["bounce_extruder0"])

    @property
    def contact_extruder0(self):
        return self._settings.get_int(["contact_extruder0"])

    @property
    def gcode_extruder0(self):
        return self.format_gcode("gcode_extruder0")

    @property
    def enabled_extruder1(self):
        return self._settings.get_boolean(["enabled_extruder1"])

    @property
    def bounce_extruder1(self):
        return self._settings.get_int(["bounce_extruder1"])

    @property
    def contact_extruder1(self):
        return self._settings.get_int(["contact_extruder1"])

    @property
    def gcode_extruder1(self):
        return self.format_gcode("gcode_extruder1")

    @property
    def enabled_door(self):
        return self._settings.get_boolean(["enabled_door"])

    @property
    def bounce_door(self):
        return self._settings.get_int(["bounce_door"])

    @property
    def contact_door(self):
        return self._settings.get_int(["contact_door"])

    @property
    def gcode_door(self):
        return self.format_gcode("gcode_door")

    @property
    def pause_print(self):
        return self._settings.get_boolean(["pause_print"])

    '''
    IPC
    '''

    def get_status(self):
        sensor_enabled = 0
        extruder0 = -1
        extruder1 = None if not self.has_extruder1() else -1
        door = -1

        if self.sensor_enabled:
            sensor_enabled = 1
            if self.enabled_extruder0:
                extruder0 = 0 if self.outage_extruder0() else 1
            if self.has_extruder1() and self.enabled_extruder1:
                    extruder1 = 0 if self.outage_extruder1() else 1
            if self.enabled_door:
                door = 0 if self.outage_door() else 1

        return dict(sensor_enabled=sensor_enabled, extruder0=extruder0, 
                    extruder1=extruder1, door=door, active_tool=self.active_tool,
                    pause_print=self.pause_print)

    def send_status_to_hmi(self):
        self._plugin_manager.send_plugin_message(self._identifier, self.get_status())

    '''
    REST endpoints
    '''
    @octoprint.plugin.BlueprintPlugin.route("/ping", methods=["GET"])
    def route_ping(self):
        return NO_CONTENT

    @octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
    def route_check_status(self):
        self.send_status_to_hmi()
        return jsonify(self.get_status())

    @octoprint.plugin.BlueprintPlugin.route("/toggle", methods=["GET"])
    def route_set_filament_sensor(self):
        # self._logger.info(flask.request.values["sensor_enabled"])
        # state = flask.request.values["sensor_enabled"]
        x1 = self.sensor_enabled
        self._settings.set_boolean(["sensor_enabled"], not self.sensor_enabled)
        self._settings.save()
        # octoprint.plugin.SettingsPlugin.on_settings_save(self, {"sensor_enabled": self.sensor_enabled})
        x2 = self.sensor_enabled
        self._logger.info("Old = {} New = {}".format(x1, x2))
        self._gpio_setup()
        return jsonify(sensor_enabled=self.sensor_enabled)

    '''
    Sensor states
    '''
    # def extruder0_enabled(self):
    #     return self.enabled_extruder0 == 1

    def has_extruder1(self):
        if not self._printer_profile_manager.get_current():
            return False
        return self._printer_profile_manager.get_current().get('extruder').get('count') >= 2

    def outage_extruder0(self):
        try:
            return GPIO.input(self.PIN_EXTRUDER0) == self.contact_extruder0
        except Exception as e:
            self.popup_error(e)
            return False

    def outage_extruder1(self):
        try:
            return GPIO.input(self.PIN_EXTRUDER1) == self.contact_extruder1
        except Exception as e:
            self.popup_error(e)
            return False

    def outage_door(self):
        try:
            return GPIO.input(self.PIN_DOOR) == self.contact_door
        except Exception as e:
            self.popup_error(e)
            return False

    '''
    Sensor Initialization
    '''
    # def _gpio_pinout(self, mode):
    #     if mode == GPIO.BOARD:
    #         self.PIN_EXTRUDER0 = 29
    #         self.PIN_EXTRUDER1 = 31
    #         self.PIN_DOOR = 37
    #     else:
    #         self.PIN_EXTRUDER0 = 5
    #         self.PIN_EXTRUDER1 = 6
    #         self.PIN_DOOR = 26

    def _gpio_clean_pin(self, pin):
        try:
            GPIO.cleanup(pin)
        except:
            pass

    def _gpio_setup(self):
        self.log_info("_gpio_setup")
        try:
            # mode = GPIO.getmode()
            # if mode is None or mode is GPIO.UNKNOWN:
            #     GPIO.setmode(GPIO.BCM)
            #     mode = GPIO.getmode()
            GPIO.setmode(GPIO.BCM)

            # self._gpio_pinout(mode)

            self._gpio_clean_pin(self.PIN_EXTRUDER0)
            self._gpio_clean_pin(self.PIN_EXTRUDER1)
            self._gpio_clean_pin(self.PIN_DOOR)

            # GPIO.remove_event_detect(self.PIN_EXTRUDER0)
            # GPIO.remove_event_detect(self.PIN_EXTRUDER1)
            # GPIO.remove_event_detect(self.PIN_DOOR)

            if self.sensor_enabled and (self.enabled_extruder0 or self.enabled_extruder1 or self.enabled_door):
                if self.enabled_extruder0:
                    self.log_info("Filament Sensor active on Extruder 0, GPIO Pin [%s]" % self.PIN_EXTRUDER0)
                    GPIO.setup(self.PIN_EXTRUDER0, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.remove_event_detect(self.PIN_EXTRUDER0)
                    GPIO.add_event_detect(
                        self.PIN_EXTRUDER0, GPIO.BOTH,
                        callback=self.callback_extruder0,
                        bouncetime=self.bounce_extruder0
                    )
                self.log_info("Has extruder 1 [%s]" % self.has_extruder1())
                self.log_info("self.enabled_extruder1 [%s]" % self.enabled_extruder1)
                if self.has_extruder1() and self.enabled_extruder1:
                    self.log_info("Filament Sensor active on Extruder 1, GPIO Pin [%s]" % self.PIN_EXTRUDER1)
                    GPIO.setup(self.PIN_EXTRUDER1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.remove_event_detect(self.PIN_EXTRUDER1)
                    GPIO.add_event_detect(
                        self.PIN_EXTRUDER1, GPIO.BOTH,
                        callback=self.callback_extruder1,
                        bouncetime=self.bounce_extruder1
                    )
                if self.enabled_door:
                    self.log_info("Door Sensor active, GPIO Pin [%s]" % self.PIN_DOOR)
                    GPIO.setup(self.PIN_DOOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                    GPIO.remove_event_detect(self.PIN_DOOR)
                    GPIO.add_event_detect(
                        self.PIN_DOOR, GPIO.BOTH,
                        callback=self.callback_door,
                        bouncetime=self.bounce_door
                    )
            else:
                self.log_info("Sensor disabled")
        except Exception as e:
            self.log_error(e)
            self.popup_error(e)

        self.send_status_to_hmi()

    '''
    Callbacks
    '''
    def on_event(self, event, payload):
        # Early abort in case of out ot filament when start printing, as we
        # can't change with a cold nozzle
        if event is Events.PRINT_STARTED:
            if not self.sensor_enabled:
                return

            if (self.enabled_extruder0 and self.outage_extruder0()) or \
               (self.has_extruder1() and self.enabled_extruder1 and self.outage_extruder1()) or \
               (self.enabled_door and self.outage_door()):
                self.send_status_to_hmi()

            if (self.enabled_extruder0 and self.outage_extruder0()) or \
               (self.enabled_door and self.outage_door()):
                self._printer.pause_print()

        if event is Events.TOOL_CHANGE:
            self.active_tool = int(payload["new"])
            self.send_status_to_hmi()

    def callback_extruder0(self, _):
        sleep(self.bounce_extruder1 / 1000)  # Debounce

        if not self.outage_extruder0():
            return self.popup_success("Filament inserted in extruder 0!")

        self.send_status_to_hmi()
        self.popup_error("Filament outage on extruder 0!")  # Debounce

        if self.has_extruder1() and self.active_tool != 0:
            return

        if self.pause_print:
            self._printer.pause_print()
        if self.gcode_extruder0:
            self._printer.commands(self.gcode_extruder0)

    def callback_extruder1(self, _):
        if not self.has_extruder1():
            return

        sleep(self.bounce_extruder1 / 1000)

        if not self.outage_extruder1():
            return self.popup_success("Filament inserted in extruder 1!")

        self.send_status_to_hmi()
        self.popup_error("Filament outage on extruder 1!")

        if self.active_tool != 1:
            return

        if self.pause_print:
            self._printer.pause_print()

        if self.gcode_extruder1:
            self._printer.commands(self.gcode_extruder1)

    def callback_door(self, _):
        sleep(self.bounce_door / 1000)

        if not self.outage_door():
            return self.popup_success("Door closed!")

        self.send_status_to_hmi()
        self.popup_error("Door open!")

        # if self.pause_print:
        #     self._printer.pause_print()

        if self.gcode_door:
            self._printer.commands(self.gcode_door)

    '''
    Update Management
    '''
    def get_update_information(self):
        return dict(
            octoprint_VolterraServices=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="FracktalWorks",
                repo="OctoPrint-VolterraServices",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/FracktalWorks/OctoPrint-VolterraServices/archive/{target_version}.zip"
            )
        )

    '''
    Plugin Management
    '''
    def initialize(self):
        self.log_info("Julia Filament Sensor started")
        self.log_info("Running RPi.GPIO version '{0}'".format(GPIO.VERSION))
        if GPIO.VERSION < "0.6":       # Need at least 0.6 for edge detection
            raise Exception("RPi.GPIO must be greater than 0.6")
        GPIO.setwarnings(False)        # Disable GPIO warnings
        self.active_tool = 0
        # self.send_status_to_hmi()

    def on_after_startup(self):
        self._gpio_setup()

    def get_assets(self):
        return dict(js=["js/VolterraServices.js"])

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=True)]

    def get_settings_version(self):
        return 2

    def get_settings_defaults(self):
        return dict(
            sensor_enabled=True,           # global sensing state

            enabled_extruder0=False,        # Default disabled
            bounce_extruder0=250,           # Debounce 250ms
            contact_extruder0=0,            # Normally Open
            gcode_extruder0=None,

            enabled_extruder1=False,        # Default is disabled
            bounce_extruder1=250,           # Debounce 250ms
            contact_extruder1=0,            # Normally Open
            gcode_extruder1=None,

            enabled_door=False,                # Default is disabled
            bounce_door=250,                # Debounce 250ms
            contact_door=0,                 # Normally Open
            gcode_door=None,

            pause_print=True,               # pause on outage
        )

    def on_settings_migrate(self, target, current=None):
        self._logger.warn(
            "######### current settings version %s target settings version %s #########", current, target)
        if (current is None or current < 2) and target == 2:
            if self._settings.has(["pin"]):
                self._settings.set_boolean(["enabled_extruder0"], self._settings.get_int(["pin"]) != -1)
            if self._settings.has(["bounce"]):
                self._settings.set_int(["bounce_extruder0"], self._settings.get_int(["bounce"]))
            if self._settings.has(["switch"]):
                self._settings.set_int(["contact_extruder0"], self._settings.get_int(["switch"]))
            if self._settings.has(["gcode_pin"]) and self._settings.get(["gcode_pin"]) is not None:
                self._settings.set(["gcode_extruder0"], str(self._settings.get(["gcode_pin"])).replace("\n", ";"))
            if self._settings.has(["pin2"]):
                self._settings.set_boolean(["enabled_extruder0"], self._settings.get_int(["pin2"]) != -1)
            if self._settings.has(["bounce2"]):
                self._settings.set_int(["bounce_extruder0"], self._settings.get_int(["bounce2"]))
            if self._settings.has(["switch2"]):
                self._settings.set_int(["contact_extruder0"], self._settings.get_int(["switch2"]))
            if self._settings.has(["gcode_pin2"]) and self._settings.get(["gcode_pin2"]) is not None:
                self._settings.set(["gcode_extruder0"], str(self._settings.get(["gcode_pin2"])).replace("\n", ";"))

    def on_settings_save(self, data):
        try:
            # self._logger.info("on_settings_save: " + str(data))
            octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
            self.popup_success('Settings saved!')
            self._gpio_setup()
        except Exception as e:
            self.log_error(e)
        self.send_status_to_hmi()


__plugin_name__ = "Volterra Services"
__plugin_version__ = "0.0.1"


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = VolterraServicesPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

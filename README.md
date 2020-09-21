# OctoPrint-VolterraServices
[OctoPrint](http://octoprint.org/) plugin that integrates with a filament sensor hooked up to a Raspberry Pi GPIO pin and allows the filament spool to be changed during a print if the filament runs out.

Initial work based on the [Octoprint-Filament](https://github.com/MoonshineSG/Octoprint-Filament) and [Octoprint-Filament-Reloaded](https://github.com/kontakt/Octoprint-Filament-Reloaded) plugins.

## Required sensor

Using this plugin requires a filament sensor. The code is set to use the Raspberry Pi's internal Pull-Up resistors, so the switch should be between your detection pin and a ground pin.

This plugin is using the GPIO.BOARD numbering scheme, the pin being used needs to be selected by the physical pin number.

## Features

* Configurable GPIO pin.
* Debounce noisy sensors.
* Support normally open and normally closed sensors.
* Execution of custom GCODE when out of filament detected.
* Optionally pause print when out of filament.

An API is available to check the filament sensor status via a GET method to `/plugin/Julia2018FilamentSensor/status` which returns a JSON

* `{filament: "-1"}` if the sensor is not setup
* `{filament: "0"}` if filament is not present
* `{filament: "1"}` if filament is present

## Debug 

Run `tail -n 100 -f ~/.octoprint/logs/octoprint.log` on pi.

## Installation

* Manually using this URL: https://github.com/FracktalWorks/OctoPrint-Julia2018FilamentSensor/archive/master.zip

## Configuration

After installation, configure the plugin via OctoPrint Settings interface.

# CanBusHacker
This is a project to make a real time CAN packet monitoring system using Arduino and CAN BUS shield hardware. This makes a very affordable and reliable CAN packet monitor and injector.

## Prerequisites
### Hardware
* Arduino UNO
* CAN BUS Shield: Currently this project supports Can Bus Shield v1.1 product (http://www.jayconsystems.com/can-bus-shield.html). You can also purchase this from eBay.
 * Probably other product will work without modification or minor tweak. We will add support for other products as we have access to them

* OBD-II to DB9 Cable: something similar to this https://www.sparkfun.com/products/10087
* USB to PC Cable to program and transfer serial data to and from Arduino

### Software
* Python 2.7.x: http://python.org
* Pyside: https://pypi.python.org/pypi/PySide (pip install pyside)
* PySerial: https://pypi.python.org/pypi/pyserial (pip install pyserial)

## How to Install
###Arudino Programming
* First assemble your Arduino and CanBusShield, refer to your CanBusShield's manufacturer's manual for more details.
* Download Arduino Library from CanBusShield's vendor site.
 * For example, for JayConSystems product, I could download it from http://www.jayconsystems.com/fileuploader/download/download/?d=0&file=custom%2Fupload%2FFile-1363136372.zip. But, you need to modify the code to gather raw packets. 
 * The "CANBridge\Arduino Library" folder contains the library for JayCon product. It has some modifications in the code to support raw level packet collection. 
 * If you want to support your board, you should go through similar code change. To get some idea how you modify your library code, please look at this change: https://github.com/ohjeongwook/CanBusHacker/commit/36e3019e95acba9e92f10366f415be9ebad8a710
* Next, import the library using the method described here: http://arduino.cc/en/guide/libraries
* Open CanBridge.ino file, compile and upload to your device

###CanBusHacker.py
This program is for Windows program that communicates with Arduino board through serial port. 
* Install dependencies and run CanBusHacker.py.
* Now connect you Arduino device to your laptop.
* Connect your OBD-II cable to your car
* Select Arduino -> Start Capture menu. You need to select serial port that is connected to your Aruino and need to specify output database file. 
 * If you didn't start your engine, now is the good time to start it, you will see various packets coming up
* The database file format is SQLite and you can open it up later using File -> Open Log menu.

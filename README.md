# toml
Read and write .toml files. works in MicroPython and CircuitPython

## Usage:
Method one (defaults to using the file `/settings.toml`):
```
import toml

toml.getenv("key") # defaults to ./settings.toml file
toml.getenv("key",file="/my_file.toml",default="value to use if key not found")
toml.getenv("WIFI",cache=True,subst=True) # replace any $VARIABLES found inside the key (e.g. welcome="Hi from $HOSTNAME >>>" etc)

toml.setenv("key","value") # put None for value to delete the key. # accepts file=
toml.subst_env("Put a $key in a string") # accepts default= file== and ${key} syntax
```
Method two (specify your own .toml file)
```
import toml
t = toml.toml("my_settings_tst.toml")
t.getenv("USER")
t.getenv("WIFI",subst=True)
t.setenv("PASSWORD","mypass")
t.subst_env("My password is $PASSWORD !")
```

## Features/Drawbacks

*. Makes backups before overwriting when changing/adding new toml values (adds _old to the end of the filename)
*. Can handle multi-line strings and escape characters etc
*. Only handles basic formatting of numbers, strings (does do multi-line), dict, list, and tuples *uses json to load/save the latter 3)
*. Extends the .toml standard by allowing $VARIABLES to be expanded (`subst=True`) 
*. Allows for `#include otherfile.toml` nested toml files as well (and even `#include $SOMEVAR` if the caller does `subst=True`)

## How to install

1. Grab the toml.py file (or the binary toml.mpy if you're using micropython 1.24)
2. Upload it into / or /lib folder

### Example

```
MicroPython v1.24.0-preview.114.g652083de6 on 2024-07-19; ESP32S CAM module no SPIRAM and OV2640 with ESP32
Type "help()" for more information.
>>> import toml
>>> toml.getenv("dir")
'ls -Flatr'
>>> toml.setenv("fred","wilma")
>>> toml.getenv("fred")
'wilma'
>>> import sh
Time set to: 2024-07-20 23:54:04
Esp32cam72:/ mpy$ tail settings.toml

dir = "ls -Flatr"
foo = [{"ssid": "mynet0", "channel": 9, "password": "hithere", "hidden": true}, {"ssid": "mynet1", "channel": 9, "password": "hithere", "hidden": false}]
fred = "wilma"
Esp32cam72:/ mpy$ 
```


# ACE-pro-standalone-dryer
Instructions on how to gut your Anycubic ace pro of its motors and a script to control the drying features from a pc.
allows you to just use it as a standalone drying box because they suck as a multi material system but have fairly good drying.

1. Clear your ACE pro of its filament feeding qeuipment:
   To do this all you need is some allen keys. i wont go into detail on how to do this part can figure it out yourself.
   unscrew and take off all the filament sensers mounted to the barrel. unplug and do whatever with the small sensors themselves but leave the main module.
   take off the brackets holding in the barrels then and cut the belts. take out the barrels, they are not needed. figure out the rest until you have the bare holes that filament can go into and the single board that drived the filament sensors plugged in (if u remove it the ACE will throw errors when you use the program)

2. make a cable: cut off the 4 pin part of an ace pro cable and the non usb-a part of a usb data cable and splice them together. just match the colours. red to red, white to white, etc.
   
3. Download python then run pip install pyserial in a command prompt.
   
4. download ace_dryer_control.py and ace_dryer_gui.pyw
   
5. run ace_dryer_gui.pyw
   
6. Done! select the correct port that your ace pro is plugged into and set your drying time and temp then hit start

   credits to szkrisz/ACEPROSV08 for the logic and claude for making this

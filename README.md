# ACE-pro-standalone-dryer
Instructions on how to gut your Anycubic ace pro of its motors and a script to control the drying features from a pc
1. Clear your ACE pro of its filament feeding qeuipment.
   To do this all you need is some allen keys. i wont go into detail on how to do this part can figure it out urself.
   unscrew and take off all the filament sensers mounted to the barrel. unplug and do whatever with the small sensors themselves but leave the main module.
   take off the brackets holding in the barrels then and cut the belts. take out the barrels, they are not needed. figure out the rest until you have the bear holes that filament can go into and a single board plugged in (if u remove it the program wont work)
2. Download python then run pip install pyserial in a command prompt.
3. download ace_dryer_control.py and ace_dryer_gui.pyw
4. run ace_dryer_gui.pyw
5. Done! set the right port that your ace pro is plugged into and set your drying time and temp then hit start

   credits to szkrisz/ACEPROSV08 for the logic

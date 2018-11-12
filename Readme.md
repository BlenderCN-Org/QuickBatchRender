# Quick Batch Render Addon For Blender


Render sequences in the timeline to individual files and automatically create a new copy of the current scene with these strips replaced with the rendered versions.  
Effects and unprocessed strips will still be in copied scene and unaffected.

Can be found in the sequence editor properties panel.


Development for this script is supported by my multimedia and video production business, [Creative Life Productions](http://www.creativelifeproductions.com)  
But, time spent working on this addon is time I cannot spend earning a living, so if you find this addon useful, consider donating:  

PayPal | Bitcoin
------ | -------
[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=XHRXZBQ3LGLH6) | ![Bitcoin Donate QR Code](http://www.snuq.com/snu-bitcoin-address.png) <br> 1JnX9ZFsvUaMp13YiQgr9V36EbTE2SA8tz  

Or support me by hiring Creative Life Productions if you have a need for the services provided.


## Installation
* Download 'QuickBatchRender.py', or download the release zip and extract this file.  
* Open Blender, and from the 'File' menu, select 'User Preferences'.
* In this new window, click on the "Add-ons" tab at the top.
* Click the 'Install Add-on from File...' button at the bottom of this window.
* Browse to and select the 'QuickBatchRender.py' file, click the 'Install Add-on from File' button.
* You should now see the addon displayed in the preferences window, click the checkbox next to the name to enable it.
* Now, below the addon information, disable or enable features by clicking the checkbox next to the name of the feature.
* Click the 'Save User Settings' button to ensure this addon is loaded next time Blender starts.



## Usage

Panel Details

* __Batch Render__

   Begin the batch render process using the settings below.

* __Render Directory__

   Type in, or select the directory to render the files into.  
   If left blank, the default scene render directory will be used.

* __Render Only Selected__

   Only process selected strips, others will not be replaced.

* __Render Modifiers__

   Apply modifiers to rendered strips.  
   Uncheck this to copy the modifiers to the rendered strip instead.

* __Render Audio__

   Check this to process audio strips as separate strips.  
   Uncheck to not process audio strips.

* __Render Meta Strips__

   Drop-down menu to decide what is done with meta strips:

   * Ignore

      Meta strips will not be processed, only copied over.

   * Individual Substrips

      Process and replace all strips inside meta strips.  
      The rendered strips will remain grouped in a meta strip in the new scene.

   * Single Strip

      Process the entire meta strip as one strip, and replace it with a single rendered strip.

#### Render Presets
Preset render settings for various types of strips.  Each type has a 'Scene Setting' option that will simply use the render settings of the current scene.

* __Opaque Strips__

   Strips with no transparency set.

* __Transparent Strips__

   Strips with transparency set.  
   Several render settings will not render any transparency information, be careful when selecting these!

* __Audio Strips__

   File type to use for rendering an audio strip.



# Changelog
### 1.0
   * Split off from VSEQF into separate addon.

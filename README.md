# Campies
*A little script to help you download the BootCamp package right for your Mac*

![Campies Logo](https://raw.githubusercontent.com/fgimian/campies/master/images/campies-logo.png)

Awesome artwork provided courtesy of
[Open Clip Art Library](https://openclipart.org/detail/225405/camp-fire)

This little script was inspired by [brigadier](https://github.com/timsutton/brigadier)
but attempts to be a cleaner and is a far simpler implementation.

## Using the Scripts

1. Run the package finder script with no arguments to obtain the appropriate 
   URL that you'll need to download to get BootCamp drivers for your machine:

    ```bash
    ./campies-finder.py
    ```

2. Download the URL provided using your browser or a download manager such as
   [DownloadThemAll](http://www.downthemall.net/) for Firefox.

3. Run the extract package script to extract the drivers from the package
   and prepare them as a ZIP file for use on Windows.

    ```bash
    ./campies-extractor.sh ~/Downloads/BootCampESD.pkg
    ```

    **Note**: Please replace the path of BootCampESD if required.

4. You'll now be given the location of your BootCamp.zip file which may be used
   in Windows to install your BootCamp drivers.

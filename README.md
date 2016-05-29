# BootCamp Package Finder

*A little script to help you download the BootCamp package right for your Mac*

This little script was inspired by [brigadier](https://github.com/timsutton/brigadier)
but attempts to be a cleaner and far simpler implementation.

However, unlike brigadier, this script does have some dependencies.

## Installing Required Dependencies

Firstly, ensure you have Python 2.x installed via Homebrew along with
virtualenv:

```bash
brew install python
pip2 install virtualenv
```

Now create a virtualenv for the project and install dependencies:

```bash
mkdir ~/.virtualenvs
virtualenv ~/.virtualenvs/bootcamp-package-finder
source ~/.virtualenvs/bootcamp-package-finder/bin/activate
pip install -r requirements.txt
```

## Using the Scripts

1. Run the package finder script with no arguments to obtain the appropriate 
   URL that you'll need to download to get BootCamp drivers for your machine:

    ```bash
    ./bootcamp-package-finder.py
    ```

2. Download the URL provided using your browser or a download manager such as
   [DownloadThemAll](http://www.downthemall.net/) for Firefox.

3. Run the extract package script to extract the drivers from the package
   and prepare them as a ZIP file for use on Windows.

    ```bash
    ./bootcamp-package-extractor.sh ~/Downloads/BootCampESD.pkg
    ```

    **Note**: Please replace the path of BootCampESD if required.

4. You'll now be given the location of your BootCamp.zip file which may be used
   in Windows to install your BootCamp drivers.

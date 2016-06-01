Campies
=======

|License|

.. image:: https://raw.githubusercontent.com/fgimian/campies/master/images/campies-logo.png
   :alt: Campies Logo

.. |License| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://github.com/fgimian/campies/blob/master/LICENSE

Artwork courtesy of `Open Clip Art
Library <https://openclipart.org/detail/225405/camp-fire>`_

Introduction
------------

Campies determines your Mac model and downloads the appropriate BootCamp
package for you. It was inspired by
`brigadier <https://github.com/timsutton/brigadier>`_ but attempts to
be a cleaner and is a far simpler implementation.

Quick Start
-----------

1. Dowload the campies script

   .. code:: bash

       curl -O https://raw.githubusercontent.com/fgimian/campies/master/campies.py
       chmod +x campies.py

2. Run the find command with no arguments to obtain the appropriate URL
   that you'll need to download to get BootCamp drivers for your
   machine:

   .. code:: bash

       ./campies.py find

3. Download the URL provided using your browser or a download manager
   such as `DownloadThemAll <http://www.downthemall.net/>`_ for
   Firefox.

4. Run the build command to extract the drivers from the package and
   prepare them as a ZIP file for use on Windows.

   .. code:: bash

       ./campies.py build ~/Downloads/BootCampESD.pkg

   **Note**: Please replace the path of BootCampESD.pkg file if
   required.

5. You'll now be given the location of your BootCamp ZIP file which may
   be used in Windows to install your BootCamp drivers.

You may see detailed help for each command using the ``--help`` argument
if you wish to override your Mac model and such.

License
-------

Campies is released under the **MIT** license. Please see the
`LICENSE <https://github.com/fgimian/campies/blob/master/LICENSE>`_
file for more details.

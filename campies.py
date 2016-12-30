#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import argparse
from gettext import gettext
import json
import os
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree
import xml
# Imports that differ between Python 2.x and Python 3.x
try:
    from plistlib import readPlistFromString as loads_plist
    from urllib2 import urlopen, URLError, HTTPError
except ImportError:
    from plistlib import loads as loads_plist
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError


# The main Apple catalog URL containing all products and download links
APPLE_CATALOG_URL = (
    'http://swscan.apple.com/content/catalogs/others/'
    'index-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog'  # noqa
)

# Colours
BOLD = '\033[1m'
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'

# Whether or not we are using Python 3.x
PY3 = sys.version_info[0] == 3

# Define an iteritems function for both Pythons
# (pinched from six at https://github.com/kelp404/six)
if PY3:
    def iteritems(d, **kw):
        return iter(d.items(**kw))
else:
    def iteritems(d, **kw):
        return iter(d.iteritems(**kw))


class DetailedArgumentParser(argparse.ArgumentParser):
    """
    Overrides the default argparse ArgumentParser to display detailed help
    upon error instead of the shorter help
    """
    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(2, gettext('\n%s: error: %s\n') % (self.prog, message))


class CampiesError(Exception):
    """A high-level exception that is used for all Campies errors"""


class CampiesSubprocessError(CampiesError):
    """An exception for any errors encountered when running a sub-process"""


def run(command, **kwargs):
    """A simple wrapper around subprocess used to run commands"""
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs
        )
        stdout, stderr = process.communicate()
    except OSError as e:
        raise CampiesSubprocessError(e)

    if process.returncode != 0:
        raise CampiesSubprocessError(stderr)

    return stdout


def get_model():
    """Obtain's the user's Mac model"""

    # Obtain and parse the output of the system profiler command
    try:
        hardware_type_xml = run([
            'system_profiler', 'SPHardwareDataType', '-xml'
        ])
    except CampiesSubprocessError:
        raise CampiesError(
            'Unable to run the command required to obtain the model'
        )
    try:
        hardware_type = loads_plist(hardware_type_xml)
    except xml.parsers.expat.ExpatError:
        raise CampiesError(
            'Unable to parse hardware XML to obtain the model'
        )

    # We now need to grab the machine model which is buried in the data
    # [{
    #   '_items': [
    #     {
    #       '_name': 'hardware_overview',
    #       'machine_model': 'MacBookPro11,5',
    #       'machine_name': 'MacBook Pro',
    try:
        model = hardware_type[0]['_items'][0]['machine_model']
    except IndexError:
        raise CampiesError(
            'Unable to find model in the hardware XML'
        )

    return model


def get_catalog(catalog_url):
    """Obtaines the Apple software catalog as a dict"""
    try:
        catalog_request = urlopen(catalog_url)
    except (IOError, URLError, HTTPError):
        raise CampiesError(
            'Unable to download catalog URL {catalog_url}'.format(
                catalog_url=catalog_url
            )
        )

    catalog_xml = catalog_request.read()
    try:
        catalog = loads_plist(catalog_xml)
    except xml.parsers.expat.ExpatError:
        raise CampiesError(
            'Unable to parse catalog XML to obtain software details'
        )
    return catalog


def get_supported_models(distribution_url):
    """Gets all supported Mac models for a particular package"""

    # Obtain the distribution XML
    try:
        distribution_request = urlopen(distribution_url)
    except (IOError, URLError, HTTPError):
        raise CampiesError(
            'Unable to download distribution URL {distribution_url}'.format(
                distribution_url=distribution_url
            )
        )

    distribution_xml = distribution_request.read()
    try:
        distribution = ElementTree.fromstring(distribution_xml)
    except xml.etree.ElementTree.ParseError:
        raise CampiesError(
            'Unable to parse distribution XML to obtain the supported model '
            'script'
        )

    # Obtain the installer script (in JavaScript)
    try:
        script = distribution.findall('script')[1].text
    except IndexError:
        raise CampiesError(
            'Unable to find supported model script in distribution XML'
        )

    # Find the line which declares the array that contains all the supported
    # models
    models_js = None
    for line in script.split('\n'):
        if 'var models' in line:
            models_js = line
            break

    # If this declaration is not found, we assume no models are supported
    # (this should never happen)
    if models_js is None:
        raise CampiesError(
            'Unable to find models definition in the distribution script at '
            '{distribution_url}'.format(
                distribution_url=distribution_url
            )
        )

    # Convert the JavaScript variable definition to JSON
    # JavaScript: var models = ['MacBookPro9,1','MacBookPro9,2',];
    # JSON: ["MacBookPro9,1","MacBookPro9,2"]
    models_json = models_js \
        .replace('var models =', '') \
        .replace("'", '"') \
        .replace(',]', ']') \
        .replace(';', '') \
        .strip()

    try:
        models = json.loads(models_json)
    except ValueError:
        raise CampiesError(
            'Unable to parse models in the distribution script at '
            '{distribution_url}'.format(
                distribution_url=distribution_url
            )
        )

    return models


def get_package_urls(catalog, model):
    """Gets all possible package URLs for a particular Mac model"""
    package_urls = []

    try:
        for id, product in iteritems(catalog['Products']):
            for package in product['Packages']:
                package_url = package['URL']

                # Skip packages that are not BootCamp
                if not package_url.endswith('BootCampESD.pkg'):
                    continue

                # Determine if the user's model is supported by the package
                # and add that package's URL to our list
                distribution_url = product['Distributions']['English']
                supported_models = get_supported_models(distribution_url)
                if model in supported_models:
                    package_urls.append(package_url)
    except IndexError:
        raise CampiesError(
            'Encountered a problem while attempting to find suitable '
            'packages for a given Mac model'
        )

    return package_urls


def find(model=None, catalog_url=None):
    """Finds the appropriate BootCamp package for the user's Mac model"""

    # Get the Mac model using system profiler
    if model is None:
        model = get_model()
        print(
            GREEN +
            'Detected your Mac model as {model}'.format(model=model) +
            ENDC
        )
    else:
        print(
            GREEN +
            'Using provided Mac model {model}'.format(model=model) +
            ENDC
        )

    # Obtain the Apple software catalog
    if catalog_url is None:
        catalog_url = APPLE_CATALOG_URL
    else:
        print(
            BLUE +
            'Using custom catalog URL {catalog_url}'.format(
                catalog_url=catalog_url
            ) +
            ENDC
        )

    print(BLUE + 'Obtaining the Apple software catalog' + ENDC)
    catalog = get_catalog(catalog_url)

    # Determine the possible packages based on the user's model
    package_urls = get_package_urls(catalog, model)
    if len(package_urls) == 1:
        print(
            GREEN +
            'A BootCamp package for your Mac model was found at '
            '{package_url}'.format(package_url=package_urls[0]) +
            ENDC
        )
    elif package_urls:
        print(
            YELLOW +
            'More than one BootCamp package matched your Mac model at the '
            'following URLs:' +
            ENDC
        )
        for package_url in package_urls:
            print(
                YELLOW +
                '* {package_url}'.format(package_url=package_url) +
                ENDC
            )
    else:
        raise CampiesError(
            'No BootCamp packages could be found for your Mac model'
        )


def build(bootcamp_package):
    """Extracts a BootCamp package and builds a ZIP file containing drivers"""

    # Verify that the Boot Camp volume is not already mounted
    if os.path.exists('/Volumes/Boot Camp'):
        raise CampiesError(
            'The Boot Camp volume (/Volumes/Boot Camp) already appears to '
            'be mounted; please eject this volume and try again'
        )

    # Verify that the BootCamp package location provided actually exists
    if not os.path.isfile(bootcamp_package):
        raise CampiesError(
            'Unable to find file {bootcamp_package}'.format(
                bootcamp_package=bootcamp_package
            )
        )

    bootcamp_extract_dir = tempfile.mkdtemp(prefix='campies')
    print(
        GREEN +
        'Using temporary directory {bootcamp_extract_dir}'.format(
            bootcamp_extract_dir=bootcamp_extract_dir
        ) +
        ENDC
    )

    print(BLUE + 'Extracting the BootCampESD package' + ENDC)
    try:
        run([
            'pkgutil', '--expand', bootcamp_package,
            '{bootcamp_extract_dir}/BootCampESD'.format(
                bootcamp_extract_dir=bootcamp_extract_dir
            )
        ])
    except CampiesSubprocessError:
        raise CampiesError('Unable to extract the BootCampESD package')

    print(BLUE + 'Extracting the Payload from the BootCampESD package' + ENDC)
    try:
        run([
            'tar', 'xfz', '{bootcamp_extract_dir}/BootCampESD/Payload'.format(
                bootcamp_extract_dir=bootcamp_extract_dir
            ), '--strip', '3', '-C', bootcamp_extract_dir
        ])
    except CampiesSubprocessError:
        raise CampiesError(
            'Unable to extract Payload from the BootCampESD package'
        )

    print(BLUE + 'Attaching the Windows Support DMG image' + ENDC)
    try:
        run([
            'hdiutil', 'attach', '-quiet',
            '{bootcamp_extract_dir}/BootCamp/WindowsSupport.dmg'.format(
                bootcamp_extract_dir=bootcamp_extract_dir
            )
        ])
    except CampiesSubprocessError:
        raise CampiesError('Unable to attach the Windows Support DMG image')

    try:
        if os.path.exists('/Volumes/Boot Camp/BootCamp/BootCamp.xml'):
            bootcamp_xml = '/Volumes/Boot Camp/BootCamp/BootCamp.xml'
        else:
            bootcamp_xml = '/Volumes/Boot Camp/BootCamp.xml'

        bootcamp_etree = ElementTree.parse(bootcamp_xml)
        bootcamp = bootcamp_etree.getroot()
    except xml.etree.ElementTree.ParseError:
        raise CampiesError(
            'Unable to parse BootCamp XML to obtain the software version'
        )

    try:
        bootcamp_version = bootcamp.find('MsiInfo').find('ProductVersion').text
    except AttributeError:
        raise CampiesError('Unable to determine BootCamp version')

    print(
        GREEN +
        'Determined your BootCamp version to be {bootcamp_version}'.format(
            bootcamp_version=bootcamp_version
        ) +
        ENDC
    )

    bootcamp_package_dir = os.path.dirname(os.path.abspath(bootcamp_package))
    bootcamp_archive = (
        '{bootcamp_package_dir}/BootCamp {bootcamp_version}'.format(
            bootcamp_package_dir=bootcamp_package_dir,
            bootcamp_version=bootcamp_version
        )
    )

    print(
        BLUE +
        'Creating a ZIP archive of the BootCamp Windows installer' +
        ENDC
    )
    try:
        shutil.make_archive(bootcamp_archive, 'zip', '/Volumes/Boot Camp')
    except OSError:
        raise CampiesError(
            'Unable to create ZIP archive of the BootCamp Windows installer'
        )

    print(BLUE + 'Detaching the Windows Support DMG image' + ENDC)
    try:
        run(['hdiutil', 'detach', '-quiet', '/Volumes/Boot Camp'])
    except CampiesSubprocessError:
        raise CampiesError('Unable to detach the Windows Support DMG image')

    print(BLUE + 'Cleaning up temporary directory' + ENDC)
    try:
        shutil.rmtree(bootcamp_extract_dir)
    except OSError:
        print(YELLOW + 'Unable to clean temporary directory' + ENDC)

    print(GREEN + 'All processing was completed successfully!' + ENDC)
    print(
        GREEN +
        'Your BootCamp archive is available at '
        '"{bootcamp_archive}.zip"'.format(bootcamp_archive=bootcamp_archive) +
        ENDC
    )


def main():
    # Print script header
    print(BOLD + 'Campies by Fotis Gimian' + ENDC)
    print(BOLD + '(https://github.com/fgimian/campies)' + ENDC)
    print()

    # Create the top-level parser
    parser = DetailedArgumentParser()
    subparsers = parser.add_subparsers(title='commands', dest='command')
    subparsers.required = True

    # Create the parser for the find command
    find_parser = subparsers.add_parser(
        'find', help='find a suitable BootCamp package for your mac'
    )
    find_parser.set_defaults(command_function=find)
    find_parser.add_argument(
        '-m', '--model', help='explicitly specify the Mac model to search for'
    )
    find_parser.add_argument(
        '-u', '--catalog_url', help='override the default catalog URL'
    )

    # Create the parser for the build command
    build_parser = subparsers.add_parser(
        'build',
        help='build a ZIP driver archive using a downloaded BootCamp package'
    )
    build_parser.set_defaults(command_function=build)
    build_parser.add_argument(
        'bootcamp_package',
        help='the full path of the downloaded BootCampESD.pkg package'
    )

    args = parser.parse_args()

    # Pass arguments to the relevant function (excluding the function itself)
    args_dict = vars(args).copy()
    del args_dict['command']
    del args_dict['command_function']

    # Run the appropriate command function
    try:
        args.command_function(**args_dict)
    except CampiesError as e:
        print(RED + str(e) + ENDC)
        exit(1)
    except KeyboardInterrupt:
        print(YELLOW + 'User cancelled operation' + ENDC)
    except Exception as e:
        print(RED + 'An unexpected error occurred: ' + str(e) + ENDC)
        exit(1)


if __name__ == '__main__':
    main()

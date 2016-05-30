#!/usr/bin/env python
import argparse
from gettext import gettext
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import urllib2
from xml.etree import ElementTree


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


class DetailedArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_help(sys.stderr)
        self.exit(2, gettext('\n%s: error: %s\n') % (self.prog, message))


def get_model():
    # Obtain and parse the output of the system profiler command
    devnull = open(os.devnull, 'w')
    system_profiler_process = subprocess.Popen(
        ['system_profiler', 'SPHardwareDataType', '-xml'],
        stdout=subprocess.PIPE, stderr=devnull
    )
    hardware_type_xml, _ = system_profiler_process.communicate()
    hardware_type = plistlib.readPlistFromString(hardware_type_xml)

    # We now need to grab the machine model which is buried in the data
    # [{
    #   '_items': [
    #     {
    #       '_name': 'hardware_overview',
    #       'machine_model': 'MacBookPro11,5',
    #       'machine_name': 'MacBook Pro',
    return hardware_type[0]['_items'][0]['machine_model']


def get_catalog(catalog_url):
    catalog_request = urllib2.urlopen(catalog_url)
    catalog_xml = catalog_request.read()
    catalog = plistlib.readPlistFromString(catalog_xml)
    return catalog


def get_supported_models(distribution_url):
    distribution_request = urllib2.urlopen(distribution_url)
    distribution_xml = distribution_request.read()
    distribution = ElementTree.fromstring(distribution_xml)

    # Obtain the installer script (in JavaScript)
    script = distribution.findall('script')[1].text

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
        return []

    # Convert the JavaScript variable definition to JSON
    # JavaScript: var models = ['MacBookPro9,1','MacBookPro9,2',];
    # JSON: ["MacBookPro9,1","MacBookPro9,2"]
    models_json = models_js \
        .replace('var models =', '') \
        .replace("'", '"') \
        .replace(',]', ']') \
        .replace(';', '') \
        .strip()
    models = json.loads(models_json)
    return models


def find(model=None, catalog_url=None, verbose=False):
    # Get the Mac model using system profiler
    if model is None:
        model = get_model()
        print (
            GREEN +
            'Detected your Mac model as {model}'.format(model=model) +
            ENDC
        )
    else:
        print (
            GREEN +
            'Using provided Mac model {model}'.format(model=model) +
            ENDC
        )

    # Obtain the Apple software catalog
    if catalog_url is None:
        catalog_url = APPLE_CATALOG_URL
    else:
        print (
            BLUE +
            'Using custom catalog URL {catalog_url}'.format(
                catalog_url=catalog_url
            ) +
            ENDC
        )

    print BLUE + 'Obtaining the Apple software catalog' + ENDC
    catalog = get_catalog(catalog_url)

    # Determine the possible packages based on the user's model
    package_urls = []
    for id, product in catalog['Products'].iteritems():
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

    # Let the user know what they should download
    if len(package_urls) == 1:
        print (
            GREEN +
            'A BootCamp package for your Mac model was found at '
            '{package_url}'.format(package_url=package_urls[0]) +
            ENDC
        )
        print
    elif package_urls:
        print (
            YELLOW +
            'More than one BootCamp package matched your Mac model at the '
            'following URLs:' +
            ENDC
        )
        for package_url in package_urls:
            print (
                YELLOW +
                '* {package_url}'.format(package_url=package_url) +
                ENDC
            )
        print
    else:
        print (
            RED +
            'No BootCamp packages could be found for your Mac model' +
            ENDC
        )
        print
        exit(1)


class CommandError(Exception):
    """Raised when a command fails to run successfully"""


def run_quietly(command, **kwargs):
    devnull = open(os.devnull, 'w')

    try:
        process = subprocess.Popen(
            command, stdout=devnull, stderr=subprocess.PIPE, **kwargs
        )
        _, stderr = process.communicate()
    except OSError as e:
        raise CommandError(e)

    if process.returncode != 0:
        raise CommandError(stderr)


def build(bootcamp_package, verbose=False):
    if os.path.exists('/Volumes/Boot Camp'):
        print (
            RED +
            'The Boot Camp volume (/Volumes/Boot Camp) already appears to '
            'be mounted' +
            ENDC
        )
        print RED + 'Please eject this volume and try again' + ENDC
        print
        exit(1)

    if not os.path.isfile(bootcamp_package):
        print (
            RED +
            'Unable to find file {bootcamp_package}'.format(
                bootcamp_package=bootcamp_package
            ) +
            ENDC
        )
        print
        exit(1)

    bootcamp_package_dir = os.path.dirname(bootcamp_package)
    bootcamp_extract_dir = tempfile.mkdtemp(prefix='campies')

    print (
        GREEN +
        'Using temporary directory {bootcamp_extract_dir}'.format(
            bootcamp_extract_dir=bootcamp_extract_dir
        ) +
        ENDC
    )

    print BLUE + 'Extracting the BootCampESD package' + ENDC
    run_quietly([
        'pkgutil', '--expand', bootcamp_package,
        '{bootcamp_extract_dir}/BootCampESD'.format(
            bootcamp_extract_dir=bootcamp_extract_dir
        )
    ])

    print BLUE + 'Extracting the Payload from BootCampESD package' + ENDC
    run_quietly([
        'tar', 'xfz', '{bootcamp_extract_dir}/BootCampESD/Payload'.format(
            bootcamp_extract_dir=bootcamp_extract_dir
        ),
        '--strip', '3', '-C', bootcamp_extract_dir
    ])

    print BLUE + 'Attaching the Windows Support DMG image' + ENDC
    run_quietly([
        'hdiutil', 'attach', '-quiet',
        '{bootcamp_extract_dir}/BootCamp/WindowsSupport.dmg'.format(
            bootcamp_extract_dir=bootcamp_extract_dir
        )
    ])

    bootcamp_etree = ElementTree.parse(
        '/Volumes/Boot Camp/BootCamp/BootCamp.xml'
    )
    bootcamp = bootcamp_etree.getroot()
    bootcamp_version = bootcamp.find('MsiInfo').find('ProductVersion').text
    print (
        GREEN +
        'Determined your BootCamp version to be {bootcamp_version}'.format(
            bootcamp_version=bootcamp_version
        ) +
        ENDC
    )

    bootcamp_archive = (
        '{bootcamp_package_dir}/BootCamp {bootcamp_version}'.format(
            bootcamp_package_dir=bootcamp_package_dir,
            bootcamp_version=bootcamp_version
        )
    )

    print (
        BLUE +
        'Creating a ZIP archive of the BootCamp Windows installer' +
        ENDC
    )
    shutil.make_archive(bootcamp_archive, 'zip', '/Volumes/Boot Camp')

    print BLUE + 'Detaching the Windows Support DMG image' + ENDC
    run_quietly(['hdiutil', 'detach', '-quiet', '/Volumes/Boot Camp'])

    print BLUE + 'Cleaning up temporary directory' + ENDC
    shutil.rmtree(bootcamp_extract_dir)

    print GREEN + 'All processing was completed successfully!' + ENDC
    print (
        GREEN +
        'Your BootCamp archive is available at '
        '"{bootcamp_archive}.zip"'.format(bootcamp_archive=bootcamp_archive) +
        ENDC
    )
    print


def main():
    print
    print BOLD + 'Campies by Fotis Gimian' + ENDC
    print BOLD + '(https://github.com/fgimian/campies)' + ENDC
    print
    # Create the top-level parser
    parser = DetailedArgumentParser()
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='increase verbosity'
    )
    subparsers = parser.add_subparsers(title='commands')

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
    del args_dict['command_function']
    args.command_function(**args_dict)


if __name__ == '__main__':
    main()

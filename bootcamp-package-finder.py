#!/usr/bin/env python
import json
import os
import plistlib
import subprocess
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


def main():
    print
    print (
        BOLD +
        'BootCamp Package Finder by Fotis Gimian '
        '(https://github.com/fgimian/bootcamp-package-finder)' +
        ENDC
    )
    print

    # Get the Mac model using system profiler
    model = get_model()
    print (
        GREEN +
        'Detected your Mac model as {model}'.format(model=model) +
        ENDC
    )

    # Obtain the Apple software catalog
    print BLUE + 'Obtaining the Apple software catalog. please wait...' + ENDC
    catalog = get_catalog(APPLE_CATALOG_URL)

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


if __name__ == '__main__':
    main()

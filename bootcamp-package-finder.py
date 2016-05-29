#!/usr/bin/env python
import json
import os
import subprocess

import biplist
import requests
import xmltodict


# The main Apple catalog URL containing all products and download links
APPLE_CATALOG_URL = (
    'http://swscan.apple.com/content/catalogs/others/'
    'index-10.11-10.10-10.9-mountainlion-lion-snowleopard-leopard.merged-1.sucatalog'  # noqa
)

# Colours
bold = lambda s: '\033[1m' + s + '\033[0m'
red = lambda s: '\033[91m' + s + '\033[0m'
green = lambda s: '\033[92m' + s + '\033[0m'
yellow = lambda s: '\033[93m' + s + '\033[0m'
blue = lambda s: '\033[94m' + s + '\033[0m'


def get_model():
    # Obtain and parse the output of the system profiler command
    devnull = open(os.devnull, 'w')
    system_profiler_process = subprocess.Popen(
        ['system_profiler', 'SPHardwareDataType', '-xml'],
        stdout=subprocess.PIPE, stderr=devnull
    )
    hardware_type_xml, _ = system_profiler_process.communicate()
    hardware_type = biplist.readPlistFromString(hardware_type_xml)

    # We now need to grab the machine model which is buried in the data
    # [{
    #   '_items': [
    #     {
    #       '_name': 'hardware_overview',
    #       'machine_model': 'MacBookPro11,5',
    #       'machine_name': 'MacBook Pro',
    return hardware_type[0]['_items'][0]['machine_model']


def get_catalog(catalog_url):
    catalog_request = requests.get(catalog_url)
    catalog_request.raise_for_status()
    catalog_xml = catalog_request.content
    catalog = biplist.readPlistFromString(catalog_xml)
    return catalog


def get_supported_models(distribution_url):
    distribution_request = requests.get(distribution_url)
    distribution_request.raise_for_status()
    distribution_xml = distribution_request.text
    distribution = xmltodict.parse(distribution_xml, dict_constructor=dict)

    # Obtain the installer script (in JavaScript)
    script = distribution['installer-gui-script']['script'][1]

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
    print bold(
        'BootCamp Package Finder by Fotis Gimian '
        '(https://github.com/fgimian/bootcamp-package-finder)'
    )
    print

    # Get the Mac model using system profiler
    model = get_model()
    print green('Detected your Mac model as {model}'.format(model=model))

    # Obtain the Apple software catalog
    print blue('Obtaining the Apple software catalog. please wait...')
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
        print green(
            'A BootCamp package for your Mac model was found at '
            '{package_url}'.format(package_url=package_urls[0])
        )
        print
    elif package_urls:
        print yellow(
            'More than one BootCamp package matched your Mac model at the '
            'following SRLs:'
        )
        for package_url in package_urls:
            print yellow('* {package_url}'.format(package_url=package_url))
        print
    else:
        print red('No BootCamp packages could be found for your Mac model')
        print
        exit(1)


if __name__ == '__main__':
    main()

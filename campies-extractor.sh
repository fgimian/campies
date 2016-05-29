#!/bin/bash

# Colours
BOLD='\033[1m'
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
ENDC='\033[0m'

echo
echo -e "${BOLD}Campies by Fotis Gimian${ENDC}"
echo -e "${BOLD}(https://github.com/fgimian/campies)${ENDC}"
echo

if [[ -d '/Volumes/Boot Camp' ]]
then
  echo -e "${RED}The Boot Camp volume (/Volumes/Boot Camp) already appears to be mounted${ENDC}"
  echo -e "${RED}Please eject this volume and try again${ENDC}"
  echo
  exit 1
fi

if [[ $# -ne 1 ]]
then
  echo -e "${YELLOW}Usage: $0 <download-path>/BootCampESD.pkg${ENDC}"
  echo
  exit 1
fi

bootcamp_package=$1
bootcamp_package_dir=$(dirname "$1")
bootcamp_extract_dir=$(mktemp -d -t bpf)

echo -e "${GREEN}Using temporary directory ${bootcamp_extract_dir}${END}"

echo -e "${BLUE}Extracting the BootCampESD package${ENDC}"
pkgutil --expand "$bootcamp_package" "${bootcamp_extract_dir}/BootCampESD"

echo -e "${BLUE}Extracting the Payload from BootCampESD package${ENDC}"
tar xfz "${bootcamp_extract_dir}/BootCampESD/Payload" --strip 3 -C "$bootcamp_extract_dir"

echo -e "${BLUE}Attaching the Windows Support DMG image${ENDC}"
hdiutil attach -quiet "${bootcamp_extract_dir}/BootCamp/WindowsSupport.dmg"

echo -e "${BLUE}Creating a ZIP archive of the BootCamp Windows installer${ENDC}"
pushd "/Volumes/Boot Camp" > /dev/null
zip -q -r "${bootcamp_package_dir}/BootCamp.zip" .
popd > /dev/null

echo -e "${BLUE}Detaching the Windows Support DMG image${ENDC}"
hdiutil detach -quiet "/Volumes/Boot Camp"

echo -e "${BLUE}Cleaning up temporary directory${ENDC}"
rm -rf "$bootcamp_extract_dir"

echo -e "${GREEN}All processing was completed successfully!${ENDC}"
echo -e "${GREEN}Your BootCamp archive is available at ${bootcamp_package_dir}/BootCamp.zip${ENDC}"
echo

#!/bin/bash

# Based on http://wiki.github.com/dkukral/everyblock/install-everyblock

HERE=`(cd "${0%/*}" 2>/dev/null; echo "$PWD"/)`
SOURCE_ROOT=`cd $HERE/../../openblock && pwd`
echo Source root is $SOURCE_ROOT


function die {
    echo $@ >&2
    echo Exiting.
    exit 1
}


if [ ! -n "$DJANGO_SETTINGS_MODULE" ]; then
    die "Please set DJANGO_SETTINGS_MODULE to your projects settings module"
fi


# First we download a bunch of zipfiles of TIGER data.

BASEURL='ftp://ftp2.census.gov/geo/tiger/TIGER2010'
ZIPS="PLACE/2010/tl_2010_29_place10.zip EDGES/tl_2010_29019_edges.zip FACES/tl_2010_29019_faces.zip FEATNAMES/tl_2010_29019_featnames.zip"

mkdir -p tiger_data
cd tiger_data || die "couldn't cd to $PWD/tiger_data"

for fname in $ZIPS; do
    wget -N $BASEURL/$fname
    if [ $? -ne 0 ]; then
        die "Could not download $BASEURL/$fname"
    fi
done

for fname in *zip; do unzip -o $fname; done
echo Shapefiles unzipped in $PWD/tiger_data

# Now we load them into our blocks table.


IMPORTER=$SOURCE_ROOT/ebpub/ebpub/streets/blockimport/tiger/import_blocks.py
if [ ! -f "$IMPORTER" ]; then die "Could not find import_blocks.py at $IMPORTER" ; fi

echo Importing blocks, this may take several minutes ...

# Passing --city means we skip features labeled for other cities.
#$IMPORTER  --city=COLUMBIA tl_2010_29019_edges.shp tl_2010_29019_featnames.dbf tl_2010_29019_faces.dbf tl_2010_29_place10.shp || die
$IMPORTER   tl_2010_29019_edges.shp tl_2010_29019_featnames.dbf tl_2010_29019_faces.dbf tl_2010_29_place10.shp || die

#########################

echo Populating streets and fixing addresses, these can take several minutes...

cd $SOURCE_ROOT/ebpub/ebpub/streets/bin || die

./populate_streets.py -v -v -v -v streets || die
./populate_streets.py -v -v -v -v block_intersections || die
./populate_streets.py -v -v -v -v intersections || die

echo Done.

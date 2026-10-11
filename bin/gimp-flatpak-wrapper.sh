#!/bin/bash
# GIMP is installed via Flatpak (org.gimp.GIMP) on this machine, not a
# plain PATH binary — this wrapper lets core.detection / GimpAdapter
# invoke it like any normal executable.
exec flatpak run org.gimp.GIMP "$@"

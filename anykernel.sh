#!/sbin/sh
# AnyKernel3 Ramdisk Mod Script
# osm0sis @ xda-developers
# Configurado para: POCO F6 (peridot) / SM8635 / Snapdragon 8s Gen 3
# Kernel: Tepuy Load-Boost with full vendor modules

## AnyKernel setup
# begin properties
properties() { \
kernel.string=Tepuy Kernel for peridot; \
do.devicecheck=1; \
do.modules=1; \
do.systemless=0; \
do.cleanup=1; \
device.name1=peridot; \
device.name2=miproduct; \
device.name3=peridot_in; \
device.name4=peridot_global; \
supported.versions=15-17; \
supported.patchlevels=; \
}
# end properties

# shell variables
block=/dev/block/bootdevice/by-name/boot;
is_slot_device=1;
ramdisk_compression=auto;
patch_vbmeta_flag=1;

## AnyKernel methods
. tools/ak3-core.sh;

## AnyKernel file attributes
set_perm_recursive 0 0 755 644 $ramdisk/*;
set_perm_recursive 0 0 750 750 $ramdisk/init* $ramdisk/sbin;

## AnyKernel install
dump_boot;

# If you have ramdisk modifications, add them here
# Example: init.rc tweaks, init script modifications, etc.

write_boot;

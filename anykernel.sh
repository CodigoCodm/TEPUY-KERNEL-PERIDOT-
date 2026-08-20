#!/sbin/sh
# AnyKernel3 Ramdisk Mod Script
# osm0sis @ xda-developers
# Configurado para: POCO F6 (peridot) / SM8635 / Snapdragon 8s Gen 3
# Kernel: Tepuy Load-Boost

## AnyKernel setup
# begin properties
properties() { \
kernel.string=Tepuy Kernel for peridot; \
do.devicecheck=1; \
do.modules=0; \
do.systemless=1; \
do.cleanup=1; \
device.name1=peridot; \
device.name2=miproduct; \
device.name3=peridot_in; \
device.name4=peridot_global; \
supported.versions=15-17; \
supported.patchlevels=; \
; }
# end properties

# shell variables
block=/dev/block/bootdevice/by-name/boot;
is_slot_device=0;
ramdisk_compression=auto;
patch_vbmeta_flag=auto;

## AnyKernel methods (DO NOT CHANGE)
# import patching functions/variables
. tools/ak3-core.sh;

## AnyKernel file attributes
# set permissions/ownership for included ramdisk files
set_perm_recursive 0 0 755 644 $ramdisk/*;
set_perm_recursive 0 0 750 750 $ramdisk/init* $ramdisk/sbin;

## AnyKernel install
dump_boot;

write_boot;

#!/sbin/sh
# AnyKernel3 Ramdisk Mod Script - FULL MODE
# Reemplaza boot.img + vendor_dlkm + system_dlkm
# SOLO compatible con la versión de HyperOS para la que se compilaron los módulos

## AnyKernel setup
properties() {
kernel.string=Tepuy Kernel for peridot [FULL - GameMode];
do.devicecheck=1;
do.modules=1;
do.systemless=0;
do.cleanup=1;
device.name1=peridot;
device.name2=miproduct;
device.name3=peridot_in;
device.name4=peridot_global;
supported.versions=15-17;
supported.patchlevels=;
}

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

# Ramdisk modifications (si las necesitas)
# set_perm_recursive 0 0 755 755 $ramdisk/lib/modules;

write_boot;

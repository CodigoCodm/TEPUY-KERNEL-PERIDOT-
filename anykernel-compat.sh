#!/sbin/sh
# AnyKernel3 Ramdisk Mod Script - COMPAT MODE
# Compatible con CUALQUIER versión de HyperOS en Poco F6 (peridot)
# Solo reemplaza boot.img, preserva dtbo/vendor_dlkm del sistema actual

## AnyKernel setup
properties() {
kernel.string=Tepuy Kernel for peridot [COMPAT - Multi-Version];
do.devicecheck=1;
do.modules=0;
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

# Preserva el dtbo del boot actual del usuario
# AnyKernel3 lo maneja automáticamente con dump_boot/write_boot
# No modificamos ramdisk para máxima compatibilidad

write_boot;

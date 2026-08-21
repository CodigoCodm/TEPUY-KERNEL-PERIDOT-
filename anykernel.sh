### AnyKernel3 Ramdisk Mod Script — Tepuy Kernel (peridot)
## Basado en osm0sis @ xda-developers + patrones de detección dinámica

# begin properties
properties() { '
kernel.string=Tepuy Kernel for peridot
do.devicecheck=1
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=0
device.name1=peridot
device.name2=miproduct
device.name3=peridot_in
device.name4=peridot_global
supported.versions=15-17
supported.patchlevels=
'; } # end properties

ui_print " "
ui_print "=== Tepuy Kernel Installer ==="

## boot shell variables
block=boot
is_slot_device=1
ramdisk_compression=auto
patch_vbmeta_flag=auto
vendor_dlkm_partition=vendor_dlkm
vendor_boot_partition=vendor_boot

# TEPUY_MODE se define en tiempo de build (compat|full) — ver workflow
# compat: solo Image.gz -> boot. NO toca vendor_dlkm. Máxima portabilidad.
# full:   además reemplaza módulos en vendor_dlkm. Requiere match exacto de build.
TEPUY_MODE="__TEPUY_MODE__"

. tools/ak3-core.sh
split_boot

BOOTMODE=false
ps | grep zygote | grep -v grep >/dev/null && BOOTMODE=true
$BOOTMODE || ps -A 2>/dev/null | grep zygote | grep -v grep >/dev/null && BOOTMODE=true

extract_erofs() {
	local img_file=$1
	local out_dir=$2
	${bin}/extract.erofs -i $img_file -x -T8 -o $out_dir &> /dev/null
}

mkfs_erofs() {
	local work_dir=$1
	local out_file=$2
	local partition_name=$(basename $work_dir)
	${bin}/mkfs.erofs \
		--mount-point /${partition_name} \
		--fs-config-file ${work_dir}/../config/${partition_name}_fs_config \
		--file-contexts  ${work_dir}/../config/${partition_name}_file_contexts \
		-z lz4hc \
		$out_file $work_dir
}

is_mounted() { mount | grep -q " $1 "; }

resolve_modules_dir() {
	local extract_dir=$1
	local partition_name=$2
	local modules_dir
	for modules_dir in \
		"${extract_dir}/lib/modules" \
		"${extract_dir}/${partition_name}/lib/modules"; do
		[ -d "$modules_dir" ] && { echo "$modules_dir"; return 0; }
	done
	modules_dir=$(find "$extract_dir" -type d -path "*/lib/modules" | grep -v "/config/" | head -n1)
	[ -n "$modules_dir" ] || return 1
	echo "$modules_dir"
	return 0
}

resolve_erofs_root_dir() {
	local extract_dir=$1
	local partition_name=$2
	local modules_dir
	modules_dir=$(resolve_modules_dir "$extract_dir" "$partition_name") || return 1
	echo "$(dirname "$(dirname "$modules_dir")")"
	return 0
}

find_named_block() {
	local partition_name=$1
	local partition_path
	for partition_path in /dev/block/mapper /dev/block/by-name /dev/block/bootdevice/by-name; do
		[ -e ${partition_path}/${partition_name}${slot} ] && { echo ${partition_path}/${partition_name}${slot}; return 0; }
		[ -e ${partition_path}/${partition_name} ] && { echo ${partition_path}/${partition_name}; return 0; }
	done
	return 1
}

# ===================================================================
# Chequeo de snapshot: evita flashear justo después de un update A/B
# a medio aplicar (causa comun de bootloop en cualquier kernel custom)
# ===================================================================
${bin}/snapshotupdater_static dump &>/dev/null
rc=$?
if [ "$rc" != 0 ]; then
	ui_print "! No se pudo leer el estado de snapshot (rc=$rc)."
	ui_print "  Reinicia a sistema una vez antes de flashear."
	abort "Aborting..."
fi
snapshot_status=$(${bin}/snapshotupdater_static dump 2>/dev/null | grep '^Update state:' | awk '{print $3}')
ui_print "- Estado de snapshot: $snapshot_status"
if [ "$snapshot_status" != "none" ]; then
	ui_print "- Parece que acabas de instalar una actualizacion de ROM."
	ui_print "- Reinicia a sistema una vez antes de flashear el kernel."
	abort "Aborting..."
fi
unset rc snapshot_status

$BOOTMODE || setenforce 0

# ===================================================================
# MODO FULL: actualizar modulos en vendor_dlkm (requiere build exacto)
# ===================================================================
if [ "$TEPUY_MODE" = "full" ] && [ -d ${home}/_modules ] && [ -n "$(ls -A ${home}/_modules/*.ko 2>/dev/null)" ]; then

	vendor_dlkm_block=$(find_named_block ${vendor_dlkm_partition})
	[ -n "$vendor_dlkm_block" ] || abort "! No se encontro la particion ${vendor_dlkm_partition}"

	[ -d /vendor_dlkm ] || mkdir /vendor_dlkm
	is_mounted /vendor_dlkm || \
		mount /vendor_dlkm -o ro || mount ${vendor_dlkm_block} /vendor_dlkm -o ro || \
			abort "! No se pudo montar /vendor_dlkm"

	strings ${home}/Image 2>/dev/null | grep -E -m1 'Linux version.*#' > ${home}/vertmp

	version_match=false
	if [ -f /vendor_dlkm/lib/modules/vertmp ]; then
		[ "$(cat /vendor_dlkm/lib/modules/vertmp)" == "$(cat ${home}/vertmp)" ] && version_match=true
	fi
	umount /vendor_dlkm

	if $version_match; then
		ui_print "- vendor_dlkm ya coincide con esta build, se omite actualizacion de modulos."
	else
		ui_print "- Actualizando modulos en /vendor_dlkm..."
		dd if=${vendor_dlkm_block} of=${home}/vendor_dlkm.img

		extract_vendor_dlkm_dir=${home}/_extract_vendor_dlkm
		mkdir -p $extract_vendor_dlkm_dir
		vendor_dlkm_is_ext4=false
		extract_erofs ${home}/vendor_dlkm.img $extract_vendor_dlkm_dir || vendor_dlkm_is_ext4=true
		sync

		if $vendor_dlkm_is_ext4; then
			mount ${home}/vendor_dlkm.img $extract_vendor_dlkm_dir -o rw -t ext4 || \
				abort "! Filesystem de vendor_dlkm no soportado"
		fi

		extract_vendor_dlkm_modules_dir=$(resolve_modules_dir "$extract_vendor_dlkm_dir" "$vendor_dlkm_partition") || \
			abort "! No se encontro el directorio de modulos"

		cp -f ${home}/_modules/*.ko ${extract_vendor_dlkm_modules_dir}/
		cp -f ${home}/vertmp ${extract_vendor_dlkm_modules_dir}/vertmp
		sync

		if $vendor_dlkm_is_ext4; then
			set_perm 0 0 0644 ${extract_vendor_dlkm_modules_dir}/vertmp
			chcon u:object_r:vendor_file:s0 ${extract_vendor_dlkm_modules_dir}/vertmp
			umount $extract_vendor_dlkm_dir
		else
			vendor_dlkm_erofs_root_dir=$(resolve_erofs_root_dir "$extract_vendor_dlkm_dir" "$vendor_dlkm_partition")
			cat ${extract_vendor_dlkm_dir}/config/vendor_dlkm_fs_config | grep -q 'lib/modules/vertmp' || \
				echo 'vendor_dlkm/lib/modules/vertmp 0 0 0644' >> ${extract_vendor_dlkm_dir}/config/vendor_dlkm_fs_config
			cat ${extract_vendor_dlkm_dir}/config/vendor_dlkm_file_contexts | grep -q 'lib/modules/vertmp' || \
				echo '/vendor_dlkm/lib/modules/vertmp u:object_r:vendor_file:s0' >> ${extract_vendor_dlkm_dir}/config/vendor_dlkm_file_contexts
			rm -f ${home}/vendor_dlkm.img
			mkfs_erofs ${vendor_dlkm_erofs_root_dir} ${home}/vendor_dlkm.img || \
				abort "! Fallo al re-empaquetar vendor_dlkm"
			rm -rf ${extract_vendor_dlkm_dir}
		fi

		flash_generic ${vendor_dlkm_partition}
		ui_print "- Modulos actualizados correctamente."
	fi
else
	ui_print "- Modo COMPAT: no se toca vendor_dlkm (maxima compatibilidad entre builds)."
fi

# ===================================================================
# Flashear kernel a boot (dump_boot/write_boot detectan todo en runtime)
# ===================================================================
flash_boot

# DTB a vendor_boot, solo si el paquete trae uno
unzip -o "$ZIPFILE" dtb -d "$home" >/dev/null 2>&1
if [ -f "$home/dtb" ]; then
	ui_print "- Actualizando DTB en vendor_boot..."
	block=${vendor_boot_partition}
	is_slot_device=1
	ramdisk_compression=auto
	patch_vbmeta_flag=auto
	reset_ak
	dump_boot
	cp -f "$home/dtb" "$split_img/dtb"
	write_boot
else
	ui_print "! No se encontro dtb, se omite vendor_boot."
fi

flash_dtbo

ui_print " "
ui_print "=== Instalacion completa ==="

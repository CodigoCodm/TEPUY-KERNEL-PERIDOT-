#!/usr/bin/env python3
"""
Tepuy Kernel Module Organizer
Organiza los módulos compilados en _modules/ (vendor_dlkm) y _system_dlkm/ (system_dlkm)
"""

import os
import sys
import argparse
import shutil

# Lista de módulos conocidos que van en system_dlkm (GKI system modules)
# Estos son módulos del kernel genérico, no del vendor
SYSTEM_MODULES = {
    "zram.ko",
    "zsmalloc.ko",
    "zpool.ko",
    "zbud.ko",
}

# Módulos críticos del vendor para peridot que DEBEN estar presentes
# Si no se encuentran compilados, se muestra advertencia
CRITICAL_VENDOR_MODULES = {
    "qcom-cpufreq-hw.ko",
    "msm_drm.ko",
    "msm_kgsl.ko",
    "mi_thermal_interface.ko",
    "xiaomi_touch.ko",
    "goodix_ts.ko",
    "wcd_core_dlkm.ko",
    "wcd938x_dlkm.ko",
    "wcd938x_slave_dlkm.ko",
    "lpass_cdc_dlkm.ko",
    "lpass_cdc_rx_macro_dlkm.ko",
    "lpass_cdc_tx_macro_dlkm.ko",
    "snd_event_dlkm.ko",
    "spf_core_dlkm.ko",
    "gpr_dlkm.ko",
    "machine_dlkm.ko",
    "smcinvoke_dlkm.ko",
    "ipam.ko",
    "ipanetm.ko",
    "rmnet_offload.ko",
    "rmnet_shs.ko",
    "mhi.ko",
    "qrtr-mhi.ko",
    "cnss2.ko",
    "qca_cld3_qca6750.ko",
    "ucsi_glink.ko",
    "panel_event_notifier.ko",
    "qti_cpufreq_cdev.ko",
    "qti_devfreq_cdev.ko",
    "msm_performance.ko",
    "fsa4480-i2c.ko",
    "aw882xx_dlkm.ko",
    "fs19xx_dlkm.ko",
}

def find_modules(input_dir):
    """Encuentra todos los .ko en el directorio de staging"""
    modules = []
    for root, dirs, files in os.walk(input_dir):
        for f in files:
            if f.endswith(".ko"):
                modules.append(os.path.join(root, f))
    return modules

def organize_modules(input_dir, vendor_out, system_out):
    os.makedirs(vendor_out, exist_ok=True)
    os.makedirs(system_out, exist_ok=True)

    # Limpiar directorios previos
    for f in os.listdir(vendor_out):
        os.remove(os.path.join(vendor_out, f))
    for f in os.listdir(system_out):
        os.remove(os.path.join(system_out, f))

    modules = find_modules(input_dir)
    print(f"[INFO] Total modules found: {len(modules)}")

    vendor_count = 0
    system_count = 0
    critical_found = set()

    for ko_path in modules:
        ko_name = os.path.basename(ko_path)

        if ko_name in SYSTEM_MODULES:
            dest = os.path.join(system_out, ko_name)
            shutil.copy2(ko_path, dest)
            system_count += 1
            print(f"  [SYSTEM] {ko_name}")
        else:
            dest = os.path.join(vendor_out, ko_name)
            shutil.copy2(ko_path, dest)
            vendor_count += 1
            print(f"  [VENDOR] {ko_name}")

            if ko_name in CRITICAL_VENDOR_MODULES:
                critical_found.add(ko_name)

    print(f"")
    print(f"[OK] Vendor modules: {vendor_count}")
    print(f"[OK] System modules: {system_count}")

    # Verificar módulos críticos faltantes
    missing = CRITICAL_VENDOR_MODULES - critical_found
    if missing:
        print(f"")
        print(f"[WARNING] Critical vendor modules NOT found (may be built-in):")
        for m in sorted(missing):
            print(f"  - {m}")
        print(f"")
        print(f"[NOTE] If these are compiled as built-in (=y), they won't have .ko files.")
        print(f"[NOTE] For GKI compatibility, consider changing them to =m in defconfig.")

    # Verificar módulos críticos de GameMode
    gamemode_kos = ["qcom-cpufreq-hw.ko", "msm_drm.ko", "msm_kgsl.ko"]
    for ko in gamemode_kos:
        if os.path.exists(os.path.join(vendor_out, ko)):
            print(f"[OK] GameMode module present: {ko}")
        else:
            print(f"[WARNING] GameMode module MISSING: {ko} — KMI may break if built-in!")

def main():
    parser = argparse.ArgumentParser(description="Organize kernel modules for AnyKernel3")
    parser.add_argument("--input", required=True, help="Input modules staging directory")
    parser.add_argument("--vendor-out", required=True, help="Output directory for vendor modules")
    parser.add_argument("--system-out", required=True, help="Output directory for system modules")
    args = parser.parse_args()

    organize_modules(args.input, args.vendor_out, args.system_out)

if __name__ == "__main__":
    main()

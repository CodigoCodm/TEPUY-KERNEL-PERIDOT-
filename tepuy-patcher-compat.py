#!/usr/bin/env python3
"""
Tepuy GameMode Patcher - KMI-Safe v2
Copia tepuy_sysfs.c del repo y hace parches simples en otros archivos.
"""

import os
import shutil
import sys

KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# === FIX: OpenSSL 3.0 compatibility ===
extract_cert = os.path.join(KERNEL_DIR, "certs/extract-cert.c")
if os.path.exists(extract_cert):
    with open(extract_cert, "r") as file:
        content = file.read()
    old_decl = """#ifdef USE_PKCS11_ENGINE
static const char *key_pass;
#endif"""
    new_decl = "static const char *key_pass;"
    if old_decl in content:
        content = content.replace(old_decl, new_decl)
        with open(extract_cert, "w") as file:
            file.write(content)
        print("[OK] certs/extract-cert.c patched for OpenSSL 3.0")
    else:
        print("[INFO] certs/extract-cert.c already patched or different format")

# ============================================================
# 1. Copy tepuy_sysfs.c from repo to kernel
# ============================================================
src_sysfs = os.path.join(REPO_DIR, "tepuy_sysfs.c")
dst_sysfs = os.path.join(KERNEL_DIR, "kernel/tepuy_sysfs.c")

if os.path.exists(src_sysfs):
    shutil.copy2(src_sysfs, dst_sysfs)
    print("[OK] kernel/tepuy_sysfs.c copied from repo")
else:
    print("[ERROR] tepuy_sysfs.c not found in repo!")
    print("[ERROR] Please upload tepuy_sysfs.c to your repo root.")
    sys.exit(1)

# Agregar al Makefile del kernel
kernel_makefile = os.path.join(KERNEL_DIR, "kernel/Makefile")
if os.path.exists(kernel_makefile):
    with open(kernel_makefile, "r") as f:
        content = f.read()
    if "tepuy_sysfs.o" not in content:
        with open(kernel_makefile, "a") as f:
            f.write("\nobj-$(CONFIG_SYSFS) += tepuy_sysfs.o\n")
        print("[OK] kernel/Makefile actualizado")
    else:
        print("[INFO] tepuy_sysfs.o ya esta en kernel/Makefile")

# ============================================================
# 2. drivers/cpufreq/cpufreq.c - Simple boost
# ============================================================
cpufreq_core = os.path.join(KERNEL_DIR, "drivers/cpufreq/cpufreq.c")
if os.path.exists(cpufreq_core):
    with open(cpufreq_core, "r") as f:
        content = f.read()

    if "extern bool tepuy_game_mode;" not in content:
        if "#include <linux/suspend.h>" in content:
            content = content.replace(
                "#include <linux/suspend.h>",
                "#include <linux/suspend.h>\nextern bool tepuy_game_mode;"
            )
            print("[OK] cpufreq.c: declaracion extern agregada")
        else:
            print("[INFO] cpufreq.c: no se encontro lugar para insertar")
    else:
        print("[INFO] cpufreq.c: ya tiene declaracion")

    if "tepuy_game_mode" not in content:
        target = "int cpufreq_driver_target(struct cpufreq_policy *policy,"
        if target in content:
            idx = content.find(target)
            if idx != -1:
                brace_idx = content.find("{", idx)
                if brace_idx != -1:
                    insert = "\n\tif (tepuy_game_mode && policy->max < policy->cpuinfo.max_freq) {\n\t\tpolicy->max = policy->cpuinfo.max_freq;\n\t}\n"
                    content = content[:brace_idx+1] + insert + content[brace_idx+1:]
                    with open(cpufreq_core, "w") as f:
                        f.write(content)
                    print("[OK] cpufreq.c: boost agregado")
        else:
            print("[INFO] cpufreq.c: funcion target no encontrada, saltando")
    else:
        print("[INFO] cpufreq.c: ya tiene logica tepuy")
else:
    print("[WARNING] cpufreq.c no encontrado")

# ============================================================
# 3. drivers/thermal/thermal_core.c
# ============================================================
thermal_core = os.path.join(KERNEL_DIR, "drivers/thermal/thermal_core.c")
if os.path.exists(thermal_core):
    with open(thermal_core, "r") as f:
        content = f.read()

    if "extern bool tepuy_game_mode;" not in content:
        if "#include <linux/thermal.h>" in content:
            content = content.replace(
                "#include <linux/thermal.h>",
                "#include <linux/thermal.h>\nextern bool tepuy_game_mode;"
            )
            print("[OK] thermal_core.c: declaracion extern agregada")
        else:
            print("[INFO] thermal_core.c: no se encontro lugar para insertar")
    else:
        print("[INFO] thermal_core.c: ya tiene declaracion")

    if "tepuy_game_mode" not in content:
        target = "static int thermal_zone_device_set_trips(struct thermal_zone_device *tz)"
        if target in content:
            idx = content.find(target)
            if idx != -1:
                brace_idx = content.find("{", idx)
                if brace_idx != -1:
                    insert = "\n\tif (tepuy_game_mode && tz->passive_delay > 100)\n\t\ttz->passive_delay = 50;\n"
                    content = content[:brace_idx+1] + insert + content[brace_idx+1:]
                    with open(thermal_core, "w") as f:
                        f.write(content)
                    print("[OK] thermal_core.c: passive delay modificado")
        else:
            print("[INFO] thermal_core.c: funcion set_trips no encontrada, saltando")
    else:
        print("[INFO] thermal_core.c: ya tiene logica tepuy")
else:
    print("[WARNING] thermal_core.c no encontrado")

# ============================================================
# 4. kernel/sched/cpufreq_schedutil.c
# ============================================================
schedutil_paths = [
    os.path.join(KERNEL_DIR, "kernel/sched/cpufreq_schedutil.c"),
    os.path.join(KERNEL_DIR, "kernel/sched/schedutil.c"),
]

schedutil = None
for path in schedutil_paths:
    if os.path.exists(path):
        schedutil = path
        break

if schedutil:
    with open(schedutil, "r") as f:
        content = f.read()

    if "extern bool tepuy_game_mode;" not in content:
        if '#include "sched.h"' in content:
            content = content.replace(
                '#include "sched.h"',
                '#include "sched.h"\nextern bool tepuy_game_mode;'
            )
            print(f"[OK] {os.path.basename(schedutil)}: declaracion extern agregada")
        else:
            print(f"[INFO] {os.path.basename(schedutil)}: no se encontro lugar para insertar")
    else:
        print(f"[INFO] {os.path.basename(schedutil)}: ya tiene declaracion")

    if "tepuy_game_mode" not in content:
        target = "static unsigned int get_next_freq(struct sugov_policy *sg_policy,"
        if target in content:
            idx = content.find(target)
            if idx != -1:
                brace_idx = content.find("{", idx)
                if brace_idx != -1:
                    insert = "\n\tif (tepuy_game_mode)\n\t\treturn sg_policy->policy->cpuinfo.max_freq;\n"
                    content = content[:brace_idx+1] + insert + content[brace_idx+1:]
                    with open(schedutil, "w") as f:
                        f.write(content)
                    print(f"[OK] {os.path.basename(schedutil)}: boost agregado")
        else:
            print(f"[INFO] {os.path.basename(schedutil)}: funcion get_next_freq no encontrada, saltando")
    else:
        print(f"[INFO] {os.path.basename(schedutil)}: ya tiene logica tepuy")
else:
    print("[WARNING] schedutil no encontrado en ninguna ubicacion")

print("\n[OK] Todos los parches KMI-safe aplicados.")

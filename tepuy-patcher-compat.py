#!/usr/bin/env python3
"""
Tepuy GameMode Patcher - KMI-Safe (Multi-Version Compatible)
Parches simples y robustos que NO rompen la compilacion.
"""

import os
import sys

KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else '.'

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
# 1. kernel/tepuy_sysfs.c - Sysfs node (siempre funciona)
# ============================================================
tepuy_sysfs = os.path.join(KERNEL_DIR, "kernel/tepuy_sysfs.c")
if not os.path.exists(tepuy_sysfs):
    tepuy_sysfs_code = r"""
/* Tepuy GameMode Sysfs Interface */
#include <linux/kobject.h>
#include <linux/string.h>
#include <linux/sysfs.h>
#include <linux/module.h>
#include <linux/init.h>

bool tepuy_game_mode = false;
EXPORT_SYMBOL_GPL(tepuy_game_mode);

static ssize_t game_mode_show(struct kobject *kobj, struct kobj_attribute *attr,
                                char *buf)
{
    return sprintf(buf, "%u\n", tepuy_game_mode);
}

static ssize_t game_mode_store(struct kobject *kobj, struct kobj_attribute *attr,
                                const char *buf, size_t count)
{
    unsigned int val;

    if (kstrtouint(buf, 10, &val))
        return -EINVAL;
    tepuy_game_mode = !!val;
    pr_info("Tepuy GameMode: %s\n", tepuy_game_mode ? "ON" : "OFF");
    return count;
}

static struct kobj_attribute game_mode_attr = __ATTR(game_mode, 0666,
                                                     game_mode_show, game_mode_store);

static struct attribute *tepuy_boost_attrs[] = {
    &game_mode_attr.attr,
    NULL,
};

static struct attribute_group tepuy_boost_attr_group = {
    .attrs = tepuy_boost_attrs,
};

static int __init tepuy_boost_init(void)
{
    struct kobject *tepuy_boost_kobj;

    tepuy_boost_kobj = kobject_create_and_add("tepuy_boost", kernel_kobj);
    if (!tepuy_boost_kobj)
        return -ENOMEM;

    if (sysfs_create_group(tepuy_boost_kobj, &tepuy_boost_attr_group))
        pr_err("Tepuy GameMode: failed to create sysfs group\n");

    return 0;
}
late_initcall(tepuy_boost_init);

"""
    with open(tepuy_sysfs, "w") as f:
        f.write(tepuy_sysfs_code)
    print("[OK] kernel/tepuy_sysfs.c creado")
else:
    print("[INFO] kernel/tepuy_sysfs.c ya existe")

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
                "#include <linux/suspend.h>\nextern bool tepuy_game_mode;")
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
# 3. drivers/thermal/thermal_core.c - Solo si es seguro
# ============================================================
thermal_core = os.path.join(KERNEL_DIR, "drivers/thermal/thermal_core.c")
if os.path.exists(thermal_core):
    with open(thermal_core, "r") as f:
        content = f.read()

    if "extern bool tepuy_game_mode;" not in content:
        if "#include <linux/thermal.h>" in content:
            content = content.replace(
                "#include <linux/thermal.h>",
                "#include <linux/thermal.h>\nextern bool tepuy_game_mode;")
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
# 4. kernel/sched/cpufreq_schedutil.c - Solo si existe
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
                '#include "sched.h"\nextern bool tepuy_game_mode;')
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
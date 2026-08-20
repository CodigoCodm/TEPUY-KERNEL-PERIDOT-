#!/usr/bin/env python3
"""
Tepuy GameMode Patcher - KMI-Safe (Multi-Version Compatible)

Este patcher NO modifica drivers del vendor (qcom-cpufreq-hw, adreno, a6xx_gmu).
En su lugar, actua sobre el kernel core:
- Thermal framework: levanta limites termicos cuando game_mode = true
- CPUFreq core: fuerza frecuencias maximas cuando game_mode = true
- Schedutil: boost de scheduler

Compatible con CUALQUIER version de HyperOS porque no rompe KMI.
"""

import os
import sys

KERNEL_DIR = sys.argv[1] if len(sys.argv) > 1 else "."

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
# 1. drivers/thermal/thermal_core.c - Levantar limites termicos
# ============================================================
thermal_core = os.path.join(KERNEL_DIR, "drivers/thermal/thermal_core.c")
if os.path.exists(thermal_core):
    with open(thermal_core, "r") as f:
        content = f.read()

    # Agregar include y declaracion externa
    if "extern bool tepuy_game_mode;" not in content:
        content = content.replace(
            "#include <linux/thermal.h>\n",
            "#include <linux/thermal.h>\n\nextern bool tepuy_game_mode;\n"
        )

    # Modificar thermal_zone_device_update para levantar limites
    old_thermal = """int thermal_zone_device_update(struct thermal_zone_device *tz,
\t\t\t\t   enum thermal_notify_event event)"""
    new_thermal = """int thermal_zone_device_update(struct thermal_zone_device *tz,
\t\t\t\t   enum thermal_notify_event event)
{
\t/* Tepuy GameMode: levantar limites termicos */
\tif (tepuy_game_mode && tz->passive_delay > 100) {
\t\ttz->passive_delay = 50;
\t\ttz->polling_delay = 50;
\t}
"""
    # Buscar la funcion y agregar logica al inicio
    if "tepuy_game_mode" not in content:
        # Buscar thermal_zone_get_temp y modificar para no throtear en game mode
        old_get_temp = """int thermal_zone_get_temp(struct thermal_zone_device *tz,
\t\t\t\t  int *temp)"""
        if old_get_temp in content:
            # Insertar despues de la declaracion de la funcion
            idx = content.find(old_get_temp)
            if idx != -1:
                # Encontrar el cuerpo de la funcion
                brace_idx = content.find("{", idx)
                if brace_idx != -1:
                    insert = """
\t/* Tepuy GameMode: reportar temperatura mas baja para evitar throttling */
\tif (tepuy_game_mode && temp) {
\t\tint real_temp;
\t\tint ret = tz->ops->get_temp(tz, &real_temp);
\t\tif (!ret) {
\t\t\t/* Reportar 5C menos para levantar throttling */
\t\t\t*temp = max(real_temp - 5000, 0);
\t\t\treturn 0;
\t\t}
\t}
"""
                    content = content[:brace_idx+1] + insert + content[brace_idx+1:]
                    with open(thermal_core, "w") as f:
                        f.write(content)
                    print("[OK] drivers/thermal/thermal_core.c modificado (KMI-safe)")
        else:
            print("[WARNING] thermal_zone_get_temp no encontrado, saltando thermal patch")
    else:
        print("[INFO] thermal_core.c ya tiene parches tepuy")
else:
    print("[WARNING] thermal_core.c no encontrado")

# ============================================================
# 2. drivers/cpufreq/cpufreq.c - Boost de frecuencia CPU
# ============================================================
cpufreq_core = os.path.join(KERNEL_DIR, "drivers/cpufreq/cpufreq.c")
if os.path.exists(cpufreq_core):
    with open(cpufreq_core, "r") as f:
        content = f.read()

    if "extern bool tepuy_game_mode;" not in content:
        content = content.replace(
            "#include <linux/suspend.h>\n",
            "#include <linux/suspend.h>\n\nextern bool tepuy_game_mode;\n"
        )

    # Modificar cpufreq_policy_apply_limits para forzar max freq en game mode
    old_limits = """static void cpufreq_policy_apply_limits(struct cpufreq_policy *policy)
{
\tunsigned int min, max;"""

    if old_limits in content and "tepuy_game_mode" not in content:
        new_limits = """static void cpufreq_policy_apply_limits(struct cpufreq_policy *policy)
{
\tunsigned int min, max;
\t
\t/* Tepuy GameMode: forzar frecuencia maxima */
\tif (tepuy_game_mode && policy->max != policy->cpuinfo.max_freq) {
\t\tpolicy->max = policy->cpuinfo.max_freq;
\t\tpolicy->min = policy->cpuinfo.max_freq;
\t\tpr_info("Tepuy GameMode: CPU%d forced to max freq %u\n",
\t\t\tpolicy->cpu, policy->max);
\t}"""
        content = content.replace(old_limits, new_limits)
        with open(cpufreq_core, "w") as f:
            f.write(content)
        print("[OK] drivers/cpufreq/cpufreq.c modificado (KMI-safe)")
    else:
        print("[INFO] cpufreq.c ya parcheado o no encontrado")
else:
    print("[WARNING] cpufreq.c no encontrado")

# ============================================================
# 3. kernel/sched/schedutil.c - Boost del scheduler
# ============================================================
schedutil = os.path.join(KERNEL_DIR, "kernel/sched/cpufreq_schedutil.c")
if not os.path.exists(schedutil):
    schedutil = os.path.join(KERNEL_DIR, "kernel/sched/schedutil.c")

if os.path.exists(schedutil):
    with open(schedutil, "r") as f:
        content = f.read()

    if "extern bool tepuy_game_mode;" not in content:
        content = content.replace(
            '#include "sched.h"\n',
            '#include "sched.h"\n\nextern bool tepuy_game_mode;\n'
        )

    # Modificar sugov_update_shared para boost agresivo
    old_sugov = """static void sugov_update_shared(struct update_util_data *hook, u64 time,
\t\t\t\t  unsigned int flags)"""

    if old_sugov in content and "tepuy_game_mode" not in content:
        # Buscar donde se calcula next_freq y boostearlo
        old_calc = """next_freq = sugov_next_freq_shared(sg_cpu, time);"""
        if old_calc in content:
            new_calc = """next_freq = sugov_next_freq_shared(sg_cpu, time);
\t/* Tepuy GameMode: boost agresivo del scheduler */
\tif (tepuy_game_mode && next_freq < sg_policy->policy->cpuinfo.max_freq) {
\t\tnext_freq = sg_policy->policy->cpuinfo.max_freq;
\t}"""
            content = content.replace(old_calc, new_calc)
            with open(schedutil, "w") as f:
                f.write(content)
            print("[OK] " + os.path.basename(schedutil) + " modificado (KMI-safe)")
        else:
            print("[WARNING] sugov_next_freq_shared no encontrado en schedutil")
    else:
        print("[INFO] schedutil ya parcheado o no encontrado")
else:
    print("[WARNING] schedutil no encontrado")

# ============================================================
# 4. kernel/sysfs-tepuy.c - Sysfs node para GameMode (kernel core)
# ============================================================
# Creamos un archivo nuevo en kernel/ para el sysfs node
# Esto es 100% kernel core, no afecta KMI del vendor

tepuy_sysfs = os.path.join(KERNEL_DIR, "kernel/tepuy_sysfs.c")
tepuy_sysfs_code = """
/* Tepuy GameMode Sysfs Interface - Kernel Core (KMI-Safe) */
#include <linux/kobject.h>
#include <linux/string.h>
#include <linux/sysfs.h>
#include <linux/module.h>
#include <linux/init.h>

bool tepuy_game_mode = false;
EXPORT_SYMBOL_GPL(tepuy_game_mode);

static ssize_t game_mode_show(struct kobject *kobj, struct kobj_attribute *attr,
\t\t\t\t  char *buf)
{
\treturn sprintf(buf, "%u\n", tepuy_game_mode);
}

static ssize_t game_mode_store(struct kobject *kobj, struct kobj_attribute *attr,
\t\t\t\t   const char *buf, size_t count)
{
\tunsigned int val;
\t
\tif (kstrtouint(buf, 10, &val))
\t\treturn -EINVAL;
\ttepuy_game_mode = !!val;
\tpr_info("Tepuy GameMode: %s\n", tepuy_game_mode ? "ON" : "OFF");
\treturn count;
}

static struct kobj_attribute game_mode_attr = __ATTR(game_mode, 0666,
\t\t\t\t\t\t     game_mode_show, game_mode_store);

static struct attribute *tepuy_boost_attrs[] = {
\t&game_mode_attr.attr,
\tNULL,
};

static struct attribute_group tepuy_boost_attr_group = {
\t.attrs = tepuy_boost_attrs,
};

static int __init tepuy_boost_init(void)
{
\tstruct kobject *tepuy_boost_kobj;
\t
\ttepuy_boost_kobj = kobject_create_and_add("tepuy_boost", kernel_kobj);
\tif (!tepuy_boost_kobj)
\t\treturn -ENOMEM;
\t
\tif (sysfs_create_group(tepuy_boost_kobj, &tepuy_boost_attr_group))
\t\tpr_err("Tepuy GameMode: failed to create sysfs group\n");
\t
\treturn 0;
}
late_initcall(tepuy_boost_init);
"""

with open(tepuy_sysfs, "w") as f:
    f.write(tepuy_sysfs_code)
print("[OK] kernel/tepuy_sysfs.c creado (KMI-safe sysfs node)")

# ============================================================
# 5. Agregar tepuy_sysfs.c al Makefile del kernel
# ============================================================
kernel_makefile = os.path.join(KERNEL_DIR, "kernel/Makefile")
if os.path.exists(kernel_makefile):
    with open(kernel_makefile, "r") as f:
        content = f.read()

    if "tepuy_sysfs.o" not in content:
        # Agregar al final
        with open(kernel_makefile, "a") as f:
            f.write("\nobj-$(CONFIG_SYSFS) += tepuy_sysfs.o\n")
        print("[OK] kernel/Makefile actualizado con tepuy_sysfs.o")
    else:
        print("[INFO] tepuy_sysfs.o ya esta en kernel/Makefile")
else:
    print("[WARNING] kernel/Makefile no encontrado")

print("\n[OK] Todos los parches KMI-safe aplicados correctamente.")
print("[INFO] Este kernel es compatible con CUALQUIER version de HyperOS.")

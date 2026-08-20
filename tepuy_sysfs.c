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

static struct kobj_attribute game_mode_attr = __ATTR(game_mode, 0644,
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

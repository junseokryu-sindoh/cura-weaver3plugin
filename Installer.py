import os
import shutil
import errno

from UM.i18n import i18nCatalog
from UM.Logger import Logger
from UM.Message import Message
from UM.Resources import Resources 

catalog = i18nCatalog("cura")

class Installer():

    def __init__(self):
        Logger.log("i", "Installing init")

    def installFiles(self):
        Logger.log("i", "Installing printer support files.")

        # Local paths
        plugin_path = os.path.join(Resources.getStoragePath(Resources.Resources),
                "plugins", "Weaver3Plugin", "Weaver3Plugin")
        definitions_path = Resources.getStoragePath(Resources.DefinitionContainers)
        resources_path = Resources.getStoragePath(Resources.Resources)

        # Build src -> dst resource map
        resource_map = {
            "fabweaver.def.json": {
                "src": os.path.join(plugin_path, "resource", "definitions"),
                "dst": os.path.join(definitions_path)
            },
            "fabweaver_extruder_0.def.json": {
                "src": os.path.join(plugin_path, "resource", "extruders"),
                "dst": os.path.join(resources_path, "extruders")
            },
            "fabweaver_extruder_1.def.json": {
                "src": os.path.join(plugin_path, "resource", "extruders"),
                "dst": os.path.join(resources_path, "extruders")
            },
            "fabweaver_abs.xml.fdm_material": {
                "src": os.path.join(plugin_path, "resource", "materials"),
                "dst": os.path.join(resources_path, "materials")
            },
            "fabweaver_asa.xml.fdm_material": {
                "src": os.path.join(plugin_path, "resource", "materials"),
                "dst": os.path.join(resources_path, "materials")
            },
            "fabweaver_pla.xml.fdm_material": {
                "src": os.path.join(plugin_path, "resource", "materials"),
                "dst": os.path.join(resources_path, "materials")
            },
            "fabweaver_rsa.xml.fdm_material": {
                "src": os.path.join(plugin_path, "resource", "materials"),
                "dst": os.path.join(resources_path, "materials")
            },
            "fabweaver_spt.xml.fdm_material": {
                "src": os.path.join(plugin_path, "resource", "materials"),
                "dst": os.path.join(resources_path, "materials")
            },
            "fabweaver_global_normal.inst.cfg": {
                "src": os.path.join(plugin_path, "resource", "quality", "fabweaver"),
                "dst": os.path.join(resources_path, "quality", "fabweaver")
            },
            "fabweaver_normal_ABS.inst.cfg": {
                "src": os.path.join(plugin_path, "resource", "quality", "fabweaver"),
                "dst": os.path.join(resources_path, "quality", "fabweaver")
            },
            "fabweaver_normal_ASA.inst.cfg": {
                "src": os.path.join(plugin_path, "resource", "quality", "fabweaver"),
                "dst": os.path.join(resources_path, "quality", "fabweaver")
            },
            "fabweaver_normal_PLA.inst.cfg": {
                "src": os.path.join(plugin_path, "resource", "quality", "fabweaver"),
                "dst": os.path.join(resources_path, "quality", "fabweaver")
            },
            "fabweaver_normal_RSA.inst.cfg": {
                "src": os.path.join(plugin_path, "resource", "quality", "fabweaver"),
                "dst": os.path.join(resources_path, "quality", "fabweaver")
            },
            "fabweaver_normal_SPT.inst.cfg": {
                "src": os.path.join(plugin_path, "resource", "quality", "fabweaver"),
                "dst": os.path.join(resources_path, "quality", "fabweaver")
            }
        }

        # Copy all missing files from src to dst
        restart_required = False
        for f in resource_map.keys():
            src_dir, dst_dir = resource_map[f]["src"], resource_map[f]["dst"]
            src = os.path.join(src_dir, f)
            dst = os.path.join(dst_dir, f)
            if not os.path.exists(dst):
                Logger.log("i", "Installing resource '%s' into '%s'" % (src, dst))
                if not os.path.exists(dst_dir):
                    try:
                        os.makedirs(dst_dir)
                    except OSError as e:
                        if e.errno == errno.EEXIST and os.path.isdir(dst_dir):
                            pass
                        else:
                            raise
                shutil.copy2(src, dst, follow_symlinks=False)
                restart_required = True

        # Display a message to the user
        if restart_required:
            msg = catalog.i18nc("@info:status", "fabWeaver resource files were installed.")
            Message(msg).show()

        return

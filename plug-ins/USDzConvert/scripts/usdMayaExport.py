import maya.cmds as cmds
import maya.api.OpenMaya as om
import shutil
import os
import tempfile
from usdzconvert import tryProcess


def export_selection_to_usd():
    # Ensure the USD plugin is loaded
    if not cmds.pluginInfo('mayaUsdPlugin', query=True, loaded=True):
        cmds.loadPlugin('mayaUsdPlugin')
    
    # Prompt the user for the export file path
    export_path = cmds.fileDialog2(fileMode=0, caption="Export USDZ File", fileFilter="USDZ Files (*.usdz)")
    
    if not export_path:
        om.MGlobal.displayError("Export canceled.")
        return

    export_path = export_path[0]
    temp_path = os.path.join(tempfile.gettempdir(), export_path.split('/')[-1].replace('usdz', 'usd'))
    
    # Export the selection to USD
    try:
        cmds.file(temp_path, force=True, options=";", type="USD Export", exportSelected=True, preserveReferences=True)
        try:
            tryProcess([temp_path])
        except:
            pass
        os.remove(temp_path)
        shutil.copy(temp_path + 'z', export_path)
        om.MGlobal.displayInfo(f"File exported to: {export_path}")
    except Exception as e:
        om.MGlobal.displayError(f"Failed to export USDZ file: {str(e)}")
        return


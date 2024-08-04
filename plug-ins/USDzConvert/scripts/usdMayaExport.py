import maya.cmds as cmds
import maya.api.OpenMaya as om
import shutil
import os
import tempfile
from usdzconvert import tryProcess
import maya.mel


def export_selection_to_usdz():
    # Ensure the USD plugin is loaded
    if not cmds.pluginInfo('mayaUsdPlugin', query=True, loaded=True):
        cmds.loadPlugin('mayaUsdPlugin')

    # Prompt the user for the export file path
    export_path = cmds.fileDialog2(fileMode=0, caption="Export USDZ File", fileFilter="USDZ Files (*.usdz)")

    if not export_path:
        om.MGlobal.displayError("Export canceled.")
        return

    export_path = export_path[0]
    temp_path_usd = os.path.join(tempfile.gettempdir(), export_path.split('/')[-1].replace('usdz', 'usd'))

    # Export the selection to USD
    try:
        start_frame = cmds.playbackOptions(q=True, min=True)
        end_frame = cmds.playbackOptions(q=True, max=True)
        cmds.optionVar(iv=('customFileDialogIncludeUVs', True))
        options_str = ";exportUVs=1;exportSkels=auto;exportSkin=auto;exportBlendShapes=1;exportDisplayColor=0;filterTypes=nurbsCurve;exportColorSets=0;exportComponentTags=1;defaultMeshScheme=none;animation=1;eulerFilter=0;staticSingleSample=0;startTime={};endTime={};frameStride=1;frameSample=0.0;defaultUSDFormat=usdc;parentScope=;shadingMode=useRegistry;convertMaterialsTo=[UsdPreviewSurface];exportInstances=1;exportVisibility=1;mergeTransformAndShape=1;stripNamespaces=0;worldspace=0;materialsScopeName=mtl".format(
            start_frame, end_frame)
        cmds.file(temp_path_usd, force=True, options=options_str, type="USD Export", exportSelected=True, pr=True,
                  es=True)
        try:
            tryProcess([temp_path_usd])
        except:
            pass
        shutil.copy(temp_path_usd, export_path.replace('usdz', 'usd'))
        shutil.copy(temp_path_usd + 'z', export_path)
        om.MGlobal.displayInfo(f"File exported to: {export_path}")
    except Exception as e:
        om.MGlobal.displayError(f"Failed to export USDZ file: {str(e)}")
        return

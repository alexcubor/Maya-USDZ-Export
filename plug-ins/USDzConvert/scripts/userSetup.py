import maya.cmds as cmds
import maya.mel as mel


def add_menu():
    # Create a new menu item
    gMainWindow = mel.eval('$temp1=$gMainWindow')
    menu = cmds.menu('usdzMenu', label='USDz', tearOff=True, parent=gMainWindow)
    # Add menu items to the new menu
    command = "import usdMayaExport; usdMayaExport.export_selection_to_usd()"
    cmds.menuItem(label="Export to USDZ", parent=menu, command=command)


cmds.evalDeferred("add_menu()")

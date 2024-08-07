#!/usr/bin/python
import os.path
from os import chdir
import sys
import importlib, imp
import tempfile
from shutil import rmtree
import zipfile

usdLibLoaded = True
kConvertErrorReturnValue = 2

try:
    from pxr import *
    import usdUtils
except ImportError:
    usdUtils.printError("failed to import pxr module. Please add path to USD Python bindings to your PYTHONPATH.")
    usdLibLoaded = False

__all__ = ['convert']


class USDParameters:
    version = 0.62
    materialsPath = '/Materials'

    def __init__(self, usdStage, verbose, url, copyright, assetPath):
        self.usdStage = usdStage
        self.verbose = verbose
        self.url = url
        self.copyright = copyright
        self.usdMaterials = {} # store materials by path
        self.usdMaterialsByName = {} # store materials by name
        self.defaultMaterial = None
        self.assetName = ''
        self.asset = usdUtils.Asset(assetPath, usdStage)



class ParserOut:
    def __init__(self):
        self.inFilePath = ''
        self.outFilePath = ''
        self.argumentFile = ''
        self.materials = []
        self.verbose = False
        self.copyTextures = False
        self.iOS12 = False
        self.url = ''
        self.copyright = ''
        self.metersPerUnit = 0
        self.loop = False
        self.noloop = False
        material = usdUtils.Material('')
        self.materials.append(material)



class Parser:
    def __init__(self):
        self.out = ParserOut()
        self.arguments = []
        self.argumentIndex = 0
        self.texCoordSet = 'st'


    def printConvertNameAndVersion(self):
        print('usdzconvert', USDParameters.version)



    def printUsage(self):
        self.printConvertNameAndVersion()
        print('usage: usdzconvert inputFile [outputFile]\n\
                   [-h] [-f file] [-v]\n\
                   [-url url]\n\
                   [-copyright copyright]\n\
                   [-copytextures]\n\
                   [-metersPerUnit value]\n\
                   [-loop]\n\
                   [-no-loop]\n\
                   [-iOS12]\n\
                   [-m materialName]        [-texCoordSet name]\n\
                   [-diffuseColor           r,g,b]\n\
                   [-diffuseColor           <file> fr,fg,fb]\n\
                   [-normal                 x,y,z]\n\
                   [-normal                 <file> fx,fy,fz\n\
                   [-emissiveColor          r,g,b]\n\
                   [-emissiveColor          <file> fr,fb,fg]\n\
                   [-metallic               c]\n\
                   [-metallic               ch <file> fc]\n\
                   [-roughness              c]\n\
                   [-roughness              ch <file> fc]\n\
                   [-occlusion              c]\n\
                   [-occlusion              ch <file> fc]\n\
                   [-opacity                c]\n\
                   [-opacity                ch <file> fc]\n\
                   [-clearcoat              c]\n\
                   [-clearcoat              ch <file> fc]\n\
                   [-clearcoatRoughness     c]\n\
                   [-clearcoatRoughness     ch <file> fc]')


    def printHelpAndExit(self):
        self.printUsage()
        print('\n\
Converts 3D model file to usd/usda/usdc/usdz.\n\
\npositional argument:\n\
  inputFile             Input file: OBJ/glTF(.gltf/glb)/FBX/Alembic(.abc)/USD(.usd/usda/usdc/usdz) files.\n\
\noptional arguments:\n\
  outputFile            Output .usd/usda/usdc/usdz files.\n\
  -h, --help            Show this help message and exit.\n\
  -f <file>             Read arguments from <file>\n\
  -v                    Verbose output.\n\
  -url <url>            Add URL metadata\n\
  -copyright "copyright message"\n\
                        Add copyright metadata\n\
  -copytextures         Copy texture files (for .usd/usda/usdc) workflows\n\
  -metersPerUnit value  Set metersPerUnit attribute with float value\n\
  -loop                 Set animation loop flag to 1\n\
  -no-loop              Set animation loop flag to 0\n\
  -m materialName       Subsequent material arguments apply to this material.\n\
                        If no material is present in input file, a material of\n\
                        this name will be generated.\n\
  -iOS12                Make output file compatible with iOS 12 frameworks\n\
  -texCoordSet name     The name of the texture coordinates to use for current\n\
                        material. Default texture coordinate set is "st".\n\
                        \n\
  -diffuseColor r,g,b   Set diffuseColor to constant color r,g,b with values in\n\
                        the range [0 .. 1]\n\
  -diffuseColor <file> fr,fg,fb\n\
                        Use <file> as texture for diffuseColor.\n\
                        fr,fg,fb: (optional) constant fallback color, with\n\
                                  values in the range [0..1].\n\
                        \n\
  -normal x,y,z         Set normal to constant value x,y,z in tangent space\n\
                        [(-1, -1, -1), (1, 1, 1)].\n\
  -normal <file> fx,fy,fz\n\
                        Use <file> as texture for normal.\n\
                        fx,fy,fz: (optional) constant fallback value, with\n\
                                  values in the range [-1..1].\n\
                        \n\
  -emissiveColor r,g,b  Set emissiveColor to constant color r,g,b with values in\n\
                        the range [0..1]\n\
  -emissiveColor <file> fr,fg,fb\n\
                        Use <file> as texture for emissiveColor.\n\
                        fr,fg,fb: (optional) constant fallback color, with\n\
                                  values in the range [0..1].\n\
                        \n\
  -metallic c           Set metallic to constant c, in the range [0..1]\n\
  -metallic ch <file> fc\n\
                        Use <file> as texture for metallic.\n\
                        ch: (optional) texture color channel (r, g, b or a).\n\
                        fc: (optional) fallback constant in the range [0..1]\n\
                        \n\
  -roughness c          Set roughness to constant c, in the range [0..1]\n\
  -roughness ch <file> fc\n\
                        Use <file> as texture for roughness.\n\
                        ch: (optional) texture color channel (r, g, b or a).\n\
                        fc: (optional) fallback constant in the range [0..1]\n\
                        \n\
  -occlusion c          Set occlusion to constant c, in the range [0..1]\n\
  -occlusion ch <file> fc\n\
                        Use <file> as texture for occlusion.\n\
                        ch: (optional) texture color channel (r, g, b or a).\n\
                        fc: (optional) fallback constant in the range [0..1]\n\
                        \n\
  -opacity c            Set opacity to constant c, in the range [0..1]\n\
  -opacity ch <file> fc Use <file> as texture for opacity.\n\
                        ch: (optional) texture color channel (r, g, b or a).\n\
                        fc: (optional) fallback constant in the range [0..1]\n\
  -clearcoat c          Set clearcoat to constant c, in the range [0..1]\n\
  -clearcoat ch <file> fc\n\
                        Use <file> as texture for clearcoat.\n\
                        ch: (optional) texture color channel (r, g, b or a).\n\
                        fc: (optional) fallback constant in the range [0..1]\n\
  -clearcoatRoughness c Set clearcoat roughness to constant c, in the range [0..1]\n\
  -clearcoatRoughness ch <file> fc\n\
                        Use <file> as texture for clearcoat roughness.\n\
                        ch: (optional) texture color channel (r, g, b or a).\n\
                        fc: (optional) fallback constant in the range [0..1]\n\
\n\
examples:\n\
    usdzconvert chicken.gltf\n\
\n\
    usdzconvert cube.obj -diffuseColor albedo.png\n\
\n\
    usdzconvert cube.obj -diffuseColor albedo.png -opacity a albedo.png\n\
\n\
    usdzconvert vase.obj -m bodyMaterial -diffuseColor body.png -opacity a body.png -metallic r metallicRoughness.png -roughness g metallicRoughness.png -normal normal.png -occlusion ao.png\n\
\n\
    usdzconvert subset.obj -m leftMaterial -diffuseColor left.png -m rightMaterial -diffuseColor right.png\n\
')

        raise usdUtils.ConvertExit()


    def printErrorUsageAndExit(self, message):
        self.printConvertNameAndVersion()
        usdUtils.printError(message)
        print('For more information, run "usdzconvert -h"')
        raise usdUtils.ConvertError()


    def loadArgumentsFromFile(self, filename):
        self.out.argumentFile = ''
        if os.path.isfile(filename):
            self.out.argumentFile = filename
        elif self.out.inFilePath:
            filename = os.path.dirname(self.out.inFilePath) + '/' + filename
            if os.path.isfile(filename):
                self.out.argumentFile = filename
        if self.out.argumentFile == '':
            self.printErrorUsageAndExit("failed to load argument file:" + filename)

        with open(self.out.argumentFile) as file:
            for line in file:
                line = line.strip()
                if '' == line:
                    continue

                line = line.replace('\t', ' ')
                line = line.replace(',', ' ')
                # arguments, like file names, can be with spaces in quotes
                quotes = line.split('"')
                if len(quotes) > 1:
                    for i in range(1, len(quotes), 2):
                        quotes[i] = quotes[i].replace(' ', '\t')
                    line = ''.join(quotes)

                arguments = line.split(' ')
                for argument in arguments:
                    argument = argument.replace('\t', ' ').strip()
                    if argument:
                        self.arguments.append(argument)


    def getParameters(self, count, argument):
        if self.argumentIndex + count >= len(self.arguments):
            self.printErrorUsageAndExit('argument ' + argument + ' needs more parameters')

        self.argumentIndex += count
        if count == 1:
            parameter = self.arguments[self.argumentIndex]
            if parameter[0] == '-' and not isFloat(parameter):
                self.printErrorUsageAndExit('unexpected parameter ' + parameter + ' for argument ' + argument)
            return self.arguments[self.argumentIndex]
        else:
            parameters = self.arguments[(self.argumentIndex - count + 1):(self.argumentIndex + 1)]
            for parameter in parameters:
                if parameter[0] == '-' and not isFloat(parameter):
                    self.printErrorUsageAndExit('unexpected parameter ' + parameter + ' for argument ' + argument)
            return parameters


    def isNextArgumentsAreFloats(self, count):
        if self.argumentIndex + count >= len(self.arguments):
            return False
        for i in range(count):
            argument = self.arguments[self.argumentIndex + 1 + i]
            if not isFloat(argument):
                return False
        return True


    def processInputArgument(self, argument):
        Ok = 0
        Error = 1
        inputIdx = -1
        for i in range(len(usdUtils.Input.names)):
            inputName = usdUtils.Input.names[i]
            if '-' + inputName == argument:
                inputIdx = i
                break
        if inputIdx == -1:
            return Error

        defaultChannels = usdUtils.Input.channels[inputIdx]
        channelsCount = len(defaultChannels)
        inputName = usdUtils.Input.names[inputIdx]
        if self.isNextArgumentsAreFloats(channelsCount):
            # constant or RGB value for input
            self.out.materials[-1].inputs[inputName] = self.getParameters(channelsCount, argument)
            return Ok

        # texture file
        channels = ''
        filename = ''
        parameter = self.getParameters(1, argument)
        if 'r' == parameter or 'g' == parameter or 'b' == parameter or 'a' == parameter or 'rgb' == parameter:
            channels = parameter
            filename = self.getParameters(1, argument)
        else:
            filename = parameter

        if channelsCount != 1 and channels != '' or channels == 'rgb':
            usdUtils.printWarning('invalid channel ' + channels + ' for argument ' + argument)
            channels = ''


        fallback = None
        if self.isNextArgumentsAreFloats(channelsCount):
            fallback = self.getParameters(channelsCount, argument)

        if channels == '':
            index = usdUtils.Input.names.index(inputName)
            channels = usdUtils.Input.channels[index]

        self.out.materials[-1].inputs[inputName] = usdUtils.Map(channels, filename, fallback, self.texCoordSet)
        return Ok


    def parse(self, arguments):
        self.arguments = []
        for arg in arguments:
            if arg.find(',') != -1:
                newargs = filter(None, arg.replace(',',' ').split(' '))
                for newarg in newargs:
                    self.arguments.append(newarg)
            else:
                self.arguments.append(arg)
        
        if len(arguments) == 0:
            self.printUsage()
            print('For more information, run "usdzconvert -h"')
            raise usdUtils.ConvertExit()

        while self.argumentIndex < len(self.arguments):
            argument = self.arguments[self.argumentIndex]
            if not argument:
                continue
            if '-' == argument[0]:
                # parse optional arguments
                if '-v' == argument:
                    self.out.verbose = True
                elif '-copytextures' == argument:
                    self.out.copyTextures = True
                elif '-iOS12' == argument or '-ios12' == argument:
                    self.out.iOS12 = True
                elif '-copyright' == argument:
                    self.out.copyright = self.getParameters(1, argument)
                    print(self.out.copyright)
                elif '-url' == argument:
                    self.out.url = self.getParameters(1, argument)
                    print(self.out.url)
                elif '-metersPerUnit' == argument:
                    metersPerUnit = self.getParameters(1, argument)
                    if not isFloat(metersPerUnit) or float(metersPerUnit) <= 0:
                        self.printErrorUsageAndExit('expected positive float value for argument ' + argument)
                    self.out.metersPerUnit = float(metersPerUnit)
                elif '-m' == argument:
                    name = self.getParameters(1, argument)
                    material = usdUtils.Material(name)
                    self.out.materials.append(material)
                    self.texCoordSet = 'st' # drop to default
                elif '-texCoordSet' == argument:
                    self.texCoordSet = self.getParameters(1, argument)
                elif '-loop' == argument or '--loop' == argument:
                    self.out.loop = True
                elif '-no-loop' == argument or '--no-loop' == argument:
                    self.out.noloop = True
                elif '-h' == argument or '--help' == argument:
                    self.printHelpAndExit()
                elif '-f' == argument:
                    self.loadArgumentsFromFile(self.getParameters(1, argument))
                else:
                    errorValue = self.processInputArgument(argument)
                    if errorValue:
                        self.printErrorUsageAndExit('unknown argument ' + argument)
            else:
                # parse input/output filenames
                if self.out.inFilePath == '':
                    self.out.inFilePath = argument
                elif self.out.outFilePath == '':
                    self.out.outFilePath = argument
                else:
                    print('Input file:', self.out.inFilePath)
                    print('Output file:', self.out.outFilePath)
                    self.printErrorUsageAndExit('unknown argument ' + argument)

            self.argumentIndex += 1

        if self.out.inFilePath == '':
            self.printErrorUsageAndExit('too few arguments')

        if self.out.loop and self.out.noloop:
            self.printErrorUsageAndExit("can't use -loop and -no-loop flags together")

        return self.out


def isFloat(value):
    try:
        val = float(value)
        return True
    except ValueError:
        return False


def createMaterial(params, materialName):
    matPath = params.materialsPath + '/' + materialName

    if params.verbose:
        print('  creating material at path:', matPath)
    if not Sdf.Path.IsValidIdentifier(materialName):
        usdUtils.printError("failed to create material by specified path.")
        raise usdUtils.ConvertError()

    surfaceShader = UsdShade.Shader.Define(params.usdStage, matPath + '/Shader')
    surfaceShader.CreateIdAttr('UsdPreviewSurface')
    usdMaterial = UsdShade.Material.Define(params.usdStage, matPath)
    usdMaterial.CreateOutput('surface', Sdf.ValueTypeNames.Token).ConnectToSource(surfaceShader, 'surface')

    params.usdMaterials[matPath] = usdMaterial
    params.usdMaterialsByName[materialName] = usdMaterial
    return usdMaterial


def getAllUsdMaterials(params, usdParentPrim):
    for usdPrim in usdParentPrim.GetChildren():
        if usdPrim.IsA(UsdGeom.Mesh) or usdPrim.IsA(UsdGeom.Subset):
            bindAPI = UsdShade.MaterialBindingAPI(usdPrim)
            if bindAPI != None:
                usdShadeMaterial = None
                directBinding = bindAPI.GetDirectBinding()
                matPath = str(directBinding.GetMaterialPath())

                if matPath != '':
                    usdShadeMaterial = directBinding.GetMaterial()

                if usdShadeMaterial != None and matPath not in params.usdMaterials:
                    params.usdMaterials[matPath] = usdShadeMaterial
                    materialNameSplitted = matPath.split('/')
                    materialName = materialNameSplitted[len(materialNameSplitted) - 1]
                    params.usdMaterialsByName[materialName] = usdShadeMaterial

        getAllUsdMaterials(params, usdPrim)


def addDefaultMaterialToGeometries(params, usdParentPrim):
    for usdPrim in usdParentPrim.GetChildren():
        if usdPrim.IsA(UsdGeom.Mesh) or usdPrim.IsA(UsdGeom.Subset):
            bindAPI = UsdShade.MaterialBindingAPI(usdPrim)
            if bindAPI != None:
                usdShadeMaterial = None
                directBinding = bindAPI.GetDirectBinding()
                matPath = str(directBinding.GetMaterialPath())

                if matPath != '':
                    usdShadeMaterial = directBinding.GetMaterial()

                if usdShadeMaterial == None:
                    if params.defaultMaterial == None:
                        params.defaultMaterial = createMaterial(params, 'defaultMaterial')
                    matPath = params.materialsPath + '/defaultMaterial'
                    usdShadeMaterial = params.defaultMaterial
                    bindAPI.Bind(usdShadeMaterial)

                if matPath not in params.usdMaterials:
                    params.usdMaterials[matPath] = usdShadeMaterial
                    materialNameSplitted = matPath.split('/')
                    materialName = materialNameSplitted[len(materialNameSplitted) - 1]
                    params.usdMaterialsByName[materialName] = usdShadeMaterial

        addDefaultMaterialToGeometries(params, usdPrim)


def findUsdMaterialRecursively(params, usdParentPrim, name, byPath):
    for usdPrim in usdParentPrim.GetChildren():
        if usdPrim.IsA(UsdShade.Material):
            path = usdPrim.GetPath()
            if byPath:
                if path == name:
                    return UsdShade.Material(usdPrim)
            else:
                matName = os.path.basename(str(path))
                if matName == name:
                    return UsdShade.Material(usdPrim)
        usdMaterial = findUsdMaterialRecursively(params, usdPrim, name, byPath)
        if usdMaterial is not None:
            return usdMaterial
    return None


def findUsdMaterial(params, name):
    if not name or len(name) < 1:
        return None

    # first try to find by material path
    if name in params.usdMaterials:
        return params.usdMaterials[name]

    # try to find by material name 
    materialName = usdUtils.makeValidIdentifier(name)
    if materialName in params.usdMaterialsByName:
        return params.usdMaterialsByName[materialName]

    # try other options
    testMaterialName = '/Materials/' + materialName
    if testMaterialName in params.usdMaterials:
        return params.usdMaterials[testMaterialName]

    testMaterialName = '/' + materialName
    if testMaterialName in params.usdMaterials:
        return params.usdMaterials[testMaterialName]

    byPath = '/' == name[0]
    return findUsdMaterialRecursively(params, params.usdStage.GetPseudoRoot(), name, byPath)


def copyTexturesFromStageToFolder(params, srcPath, folder):
    copiedFiles = {}
    srcFolder = os.path.dirname(srcPath)
    for path, usdMaterial in params.usdMaterials.items():
        for childShader in usdMaterial.GetPrim().GetChildren():
            idAttribute = childShader.GetAttribute('info:id')
            if idAttribute is None:
                continue
            id = idAttribute.Get()
            if id != 'UsdUVTexture':
                continue
            fileAttribute = childShader.GetAttribute('inputs:file')
            if fileAttribute is None or fileAttribute.Get() is None:
                continue
            filename = fileAttribute.Get().path
            if not filename:
                continue
            if filename in copiedFiles:
                continue
            if srcFolder and filename[0] != '/':
                filePath = srcFolder + '/' + filename
            else:
                filePath = filename
            usdUtils.copy(filePath, folder + '/' + filename, params.verbose)
            copiedFiles[filename] = filename


def copyMaterialTextures(params, material, srcPath, dstPath, folder):
    srcFolder = os.path.dirname(srcPath)
    dstFolder = os.path.dirname(dstPath)
    for inputName, input in material.inputs.iteritems():
        if not isinstance(input, usdUtils.Map):
            continue
        if not input.file:
            continue

        if srcFolder:
            if os.path.isfile(srcFolder + '/' + input.file):
                usdUtils.copy(srcFolder + '/' + input.file, folder + '/' + input.file, params.verbose)
                continue

        if dstFolder and dstFolder != srcFolder:
            if os.path.isfile(dstFolder + '/' + input.file):
                usdUtils.copy(dstFolder + '/' + input.file, folder + '/' + input.file, params.verbose)
                continue

        if os.path.isfile(input.file):
            if srcFolder and len(srcFolder) < len(input.file) and srcFolder + '/' == input.file[0:(len(srcFolder)+1)]:
                input.file = input.file[(len(srcFolder)+1):]
                usdUtils.copy(srcFolder + '/' + input.file, folder + '/' + input.file, params.verbose)
                continue

            if dstFolder and dstFolder != srcFolder and len(dstFolder) < len(input.file) and dstFolder + '/' == input.file[0:(len(dstFolder)+1)]:
                input.file = input.file[(len(dstFolder)+1):]
                usdUtils.copy(dstFolder + '/' + input.file, folder + '/' + input.file, params.verbose)
                continue

            basename = 'textures/' + os.path.basename(input.file)
            usdUtils.copy(input.file, folder + '/' + basename, params.verbose)
            input.file = basename


def createStageMetadata(params):
    params.usdStage.SetMetadataByDictKey("customLayerData", "creator", "usdzconvert preview " + str(params.version))
    if params.url != '':
        params.usdStage.SetMetadataByDictKey("customLayerData", "url", str(params.url))
    if params.copyright != '':
        params.usdStage.SetMetadataByDictKey("customLayerData", "copyright", str(params.copyright))


def unzip(filePath, outputDir):
    firstFile = ''
    with zipfile.ZipFile(filePath) as zf:
        zf.extractall(outputDir)
        namelist = zf.namelist()
        if len(namelist) > 0:
            firstFile = namelist[0]
    return firstFile


def process(argumentList):
    parser = Parser()
    parserOut = parser.parse(argumentList)

    srcPath = ''
    if os.path.isfile(parserOut.inFilePath):
        srcPath = parserOut.inFilePath
    elif os.path.dirname(parserOut.inFilePath) == '' and parserOut.argumentFile:
        # try to find input file in argument file folder which is specified by -f in command line
        argumentFileDir = os.path.dirname(parserOut.argumentFile)
        if argumentFileDir:
            os.chdir(argumentFileDir)
            if os.path.isfile(parserOut.inFilePath):
                srcPath = parserOut.inFilePath

    if srcPath == '':
        parser.printErrorUsageAndExit('input file ' + parserOut.inFilePath + ' does not exist.')

    fileAndExt = os.path.splitext(srcPath)
    if len(fileAndExt) != 2:
        parser.printErrorUsageAndExit('input file ' + parserOut.inFilePath + ' has unsupported file extension.')

    print('Input file:', srcPath)
    srcExt = fileAndExt[1].lower()

    dstIsUsdz = False
    dstPath = parserOut.outFilePath
    dstExt = ''
    if dstPath == '':
        # default destination file is .usdz file in the same folder as source file
        dstExt = '.usdz'
        dstPath = fileAndExt[0] + dstExt
        dstIsUsdz = True

    dstFileAndExt = os.path.splitext(dstPath)
    if len(dstFileAndExt) != 2:
        parser.printErrorUsageAndExit('output file ' + dstPath + ' has unsupported file extension.')

    if not dstIsUsdz:
        dstExt = dstFileAndExt[1].lower()
        if dstExt == '.usdz':
            dstIsUsdz = True
        elif dstExt != '.usd' and dstExt != '.usdc' and dstExt != '.usda':
            parser.printErrorUsageAndExit('output file ' + dstPath + ' should have .usdz, .usdc, .usda or .usd extension.')

    tmpFolder = tempfile.mkdtemp('usdzconvert')

    legacyModifier = None
    if parserOut.iOS12:
        iOS12Compatible_module = importlib.import_module("iOS12LegacyModifier")
        legacyModifier = iOS12Compatible_module.createLegacyModifier()
        legacyModifier.setMetersPerUnit(parserOut.metersPerUnit)
        print('Converting in iOS12 compatiblity mode.')

    tmpPath = dstFileAndExt[0] + '.usdc' if dstIsUsdz else dstPath
    tmpBasename = os.path.basename(tmpPath)
    tmpPath = tmpFolder + '/' + tmpBasename
    removeTmpPath = False
    if '.usd' == srcExt or '.usda' == srcExt or '.usdc' == srcExt:
        # create .usdc file in source file folder
        srcFolder =  os.path.dirname(srcPath)
        tmpPath = srcFolder + '/' +  tmpBasename
        if os.path.isfile(tmpPath):
            tmpPath = srcFolder + '/' +  next(tempfile._get_candidate_names()) + tmpBasename
        removeTmpPath = True

    if parserOut.verbose and parserOut.copyTextures and dstIsUsdz:
        usdUtils.printWarning('argument -copytextures works for .usda and .usdc output files only.')

    copyTextures = parserOut.copyTextures and not dstIsUsdz
    srcIsUsd = False;
    srcIsUsdz = False;
    usdStage = None
    if '.obj' == srcExt:
        global usdStageWithObj_module
        usdStageWithObj_module = importlib.import_module("usdStageWithObj")
        # this line can be updated with Pixar's backend loader
        usdStage = usdStageWithObj_module.usdStageWithObj(srcPath, tmpPath, legacyModifier, parserOut.verbose)
    elif '.gltf' == srcExt or '.glb' == srcExt:
        global usdStageWithGlTF_module
        usdStageWithGlTF_module = importlib.import_module("usdStageWithGlTF")
        usdStage = usdStageWithGlTF_module.usdStageWithGlTF(srcPath, tmpPath, legacyModifier, copyTextures, parserOut.verbose)
    elif '.fbx' == srcExt:
        global usdStageWithFbx_module
        usdStageWithFbx_module = importlib.import_module("usdStageWithFbx")
        usdStage = usdStageWithFbx_module.usdStageWithFbx(srcPath, tmpPath, legacyModifier, copyTextures, parserOut.verbose)
    elif '.usd' == srcExt or '.usda' == srcExt or '.usdc' == srcExt:
        usdStage = Usd.Stage.Open(srcPath)
        srcIsUsd = True;
    elif '.usdz' == srcExt:
        tmpUSDC = unzip(srcPath, tmpFolder)
        if tmpUSDC == '':
            parser.printErrorUsageAndExit("can't open input usdz file " + parserOut.inFilePath)
        usdStage = Usd.Stage.Open(tmpFolder + '/' + tmpUSDC)
        srcIsUsdz = True;
    elif '.abc' == srcExt:
        usdStage = Usd.Stage.Open(srcPath)
        # To update Alembic USD Stage, first save it to temporary .usdc and reload it
        tmpUSDC = tmpPath + '.usdc'
        usdStage.GetRootLayer().Export(tmpUSDC)
        if parserOut.verbose:
            print('Temporary USDC file:', tmpUSDC)
        usdStage = Usd.Stage.Open(tmpUSDC)
    else:
        parser.printErrorUsageAndExit('input file ' + parserOut.inFilePath + ' has unsupported file extension.')

    if usdStage == None:
        usdUtils.printError("failed to create USD stage.")
        raise usdUtils.ConvertError()

    params = USDParameters(usdStage, parserOut.verbose, parserOut.url, parserOut.copyright, tmpPath)
    createStageMetadata(params)

    if parserOut.metersPerUnit != 0 and legacyModifier is None:
        usdStage.SetMetadata("metersPerUnit", parserOut.metersPerUnit)

    if parserOut.loop and (srcIsUsd or srcIsUsdz):
        usdStage.SetMetadataByDictKey("customLayerData", "loopStartToEndTimeCode", True)

    if parserOut.noloop:
        usdStage.SetMetadataByDictKey("customLayerData", "loopStartToEndTimeCode", False)

    rootPrim = None
    if usdStage.HasDefaultPrim():
        rootPrim = usdStage.GetDefaultPrim()

    if rootPrim != None:
        params.assetName = rootPrim.GetName()
        params.materialsPath = '/' + params.assetName + '/Materials'

        if legacyModifier is not None and legacyModifier.getMetersPerUnit() != 0:
            usdMetersPerUnit = 0.01
            scale = legacyModifier.getMetersPerUnit() / usdMetersPerUnit
            if scale != 1:
                rootXform = UsdGeom.Xform(rootPrim)
                rootXform.AddScaleOp(UsdGeom.XformOp.PrecisionFloat, "metersPerUnit").Set(Gf.Vec3f(scale, scale, scale))

    getAllUsdMaterials(params, params.usdStage.GetPseudoRoot())

    if srcIsUsd and dstIsUsdz:
        # copy textures to temporary folder while creating usdz
        copyTexturesFromStageToFolder(params, srcPath, tmpFolder)

    if srcIsUsd:
        if not (len(parserOut.materials) == 1 and parserOut.materials[0].isEmpty()):
            usdUtils.printWarning('Material arguments are ignored for .usda/usdc input files.')
    else:
        # update usd materials with command line material arguments
        for material in parserOut.materials:

            if legacyModifier is not None:
                legacyModifier.opacityAndDiffuseOneTexture(material)

            if material.name == '':
                # if materials are not specified, then apply default material to all materials
                if not material.isEmpty():
                    addDefaultMaterialToGeometries(params, params.usdStage.GetPseudoRoot())

                    copyMaterialTextures(params, material, srcPath, dstPath, tmpFolder)
                    if legacyModifier is not None:
                        legacyModifier.makeORMTextures(material, tmpFolder, parserOut.verbose)

                    for path, usdMaterial in params.usdMaterials.iteritems():
                        surfaceShader = material.getUsdSurfaceShader(usdMaterial, params.usdStage)
                        material.updateUsdMaterial(usdMaterial, surfaceShader, params.usdStage)
                continue

            usdMaterial = findUsdMaterial(params, material.path if material.path else material.name)

            if usdMaterial is not None:
                # if material does exist remove it
                matPath = str(usdMaterial.GetPrim().GetPath())
                if matPath in params.usdMaterials:
                    del params.usdMaterials[matPath]
                usdStage.RemovePrim(matPath)
                usdMaterial = None

            copyMaterialTextures(params, material, srcPath, dstPath, tmpFolder)
            if legacyModifier is not None:
                legacyModifier.makeORMTextures(material, tmpFolder, parserOut.verbose)

            usdMaterial = material.makeUsdMaterial(params.asset)
            if usdMaterial is None:
                continue

            surfaceShader = material.getUsdSurfaceShader(usdMaterial, params.usdStage)
            material.updateUsdMaterial(usdMaterial, surfaceShader, params.usdStage)
            params.usdMaterials[str(usdMaterial.GetPrim().GetPath())] = usdMaterial

    usdStage.GetRootLayer().Export(tmpPath)

    # prepare destination folder
    dstFolder = os.path.dirname(dstPath)
    if dstFolder != '' and not os.path.isdir(dstFolder):
        if parserOut.verbose:
            print('Creating folder:', dstFolder)
        os.makedirs(dstFolder)

    if dstIsUsdz:
        # construct .usdz archive from the .usdc file
        UsdUtils.CreateNewARKitUsdzPackage(Sdf.AssetPath(tmpPath), dstPath)
    else:
        usdUtils.copy(tmpPath, dstPath)

    # copy textures with usda and usdc
    if copyTextures:
        copyTexturesFromStageToFolder(params, tmpPath, dstFolder)

    if removeTmpPath:
        os.remove(tmpPath)

    rmtree(tmpFolder, ignore_errors=True)
    print('Output file:', dstPath)

    arkitCheckerReturn = 0
    if dstIsUsdz:
        # ARKit checker code
        usdcheckerArgs = [dstPath]
        if parserOut.verbose:
            usdcheckerArgs.append('-v')
        scriptFolder = os.path.dirname(os.path.realpath(__file__))
        usdARKitChecker = imp.load_source('main', scriptFolder + '/usdARKitChecker')
        arkitCheckerReturn = usdARKitChecker.main(usdcheckerArgs)

    return arkitCheckerReturn

def tryProcess(argumentList):
    try:
        ret = process(argumentList)
    except usdUtils.ConvertError:
        return kConvertErrorReturnValue
    except usdUtils.ConvertExit:
        return 0
    except:
        raise
    return ret


def convert(fileList, optionDictionary):
    supportedFormats = ['.obj', '.gltf', '.glb', '.fbx', '.usd', '.usda', '.usdc', '.usdz', '.abc'];
    argumentList = []

    for file in fileList:
        fileAndExt = os.path.splitext(file)
        if len(fileAndExt) == 2:
            ext = fileAndExt[1].lower();
            if ext in supportedFormats:
                # source file to convert
                argumentList.append(file)

            name = fileAndExt[0]

            for inputName in usdUtils.Input.names:
                if inputName in optionDictionary:
                    option = optionDictionary[inputName]

                    channel = ''

                    optionAndChannel = option.split(':')
                    if len(optionAndChannel) == 2:
                        option = optionAndChannel[0]
                        channel = optionAndChannel[1]

                    if len(name) > len(option) and option==name[-len(option):]:
                        argumentList.append('-' + inputName)
                        if channel != '':
                            argumentList.append(channel)
                        argumentList.append(file)

    return tryProcess(argumentList)


def main():
    return tryProcess(sys.argv[1:])


if __name__ == '__main__':
    if usdLibLoaded:
        errorValue = main()
    else:
        errorValue = kConvertErrorReturnValue

    sys.exit(errorValue)


import json
from AGO_Manager import AGO_manager
import arcpy
import os, sys
from arcgis.gis import GIS


class Project:
    def __init__(self, projects_folder, project_folder, project_name):
        self.projects_folder = projects_folder
        self.project_folder = project_folder
        self.project_root = f"{self.projects_folder}/{self.project_folder}"
        self.project_name = project_name
        self.project_path = f"{self.project_root}/{self.project_name}.aprx"
        self.project = arcpy.mp.ArcGISProject(f"{self.projects_folder}/{self.project_folder}/{self.project_name}.aprx")
        self.project_dict = {}

        self.project_dict['modified'] = self.project.dateSaved
        self.project_dict['version'] = self.project.version
        self.project_dict['gdb'] = self.project.defaultGeodatabase
        self.project_dict['tbx'] = self.project.defaultToolbox
        self.project_dict['aprx'] = f'{self.projects_folder}/{self.project_folder}/{self.project_name}.aprx'
        maps = self.project.listMaps()
        if maps != []:
            self.project_dict['maps'] = []
            maps = self.project.listMaps()
            for i, map in enumerate(maps):
                layers = map.listLayers()
                map_dict = {}
                map_dict['name'] = map.name
                map_dict['data'] = map
                map_dict['layers'] = []
                for layer in layers:
                    layer_dict = {}
                    layer_dict['name'] = layer.longName
                    layer_dict['data'] = layer
                    map_dict['layers'].append(layer_dict)
                self.project_dict['maps'].append(map_dict)

        layouts = self.project.listLayouts()
        if layouts != []:
            self.project_dict['layouts'] = []
            for layout in layouts:
                layout_dict = {}
                layout_dict['name'] = layout.name

    def projDict(self):
        return self.project_dict


# https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/merge.htm
def Merge(inputs, output_path, field_map=None, source=None):
    arcpy.management.Merge(inputs, output_path, field_map, source)


def updateItem(proj_folder, proj_name):
    with open('secrets.json') as file:
        x = json.load(file)

    ############################ BEGIN ASSIGNING VARIABLES ############################

    # Set the path to the project
    prjFolder = proj_folder
    prjPath = f'{proj_folder}/{proj_name}.aprx'

    # Set login credentials (username is case-sensitive, fyi)
    portal = "https://www.arcgis.com/"  # or use another portal
    user = x['user']
    password = x['password']

    # Set sharing settings
    shrOrg = False
    shrEveryone = False
    shrGroups = ''

    ############################# END ASSIGNING VARIABLES #############################

    # Assign name and location for temporary staging files
    tempPath = prjFolder
    sddraft = os.path.join(tempPath, "TempFile.sddraft")
    sd = os.path.join(tempPath, "TempFile.sd")

    # Connect to ArcGIS online
    print("Connecting to {}".format(portal))
    gis = GIS(portal, user, password)
    print("Successfully logged in as: " + gis.properties.user.username + "\n")

    # Assign environment and project, and create empty dictionaries
    arcpy.env.overwriteOutput = True
    prj = arcpy.mp.ArcGISProject(prjPath)
    mapDict = {}
    servDict = {}

    # Populate map dictionary with map names and objects from earlier defined project
    for map in prj.listMaps():
        mapDict[map.name] = map
        mapLayers = map.listLayers()
        for mapLayer in mapLayers:
            if mapLayer.name == 'JSA_Merge':
                mapItem = mapLayer

    # Search for service definition files under the current user's account and populate
    # service definition dictionary with names and ID numbers
    sdItem = gis.content.search(query="owner: " + user + " AND type:Service Definition", max_items=10000)
    for serv in sdItem:
        if str(serv.name).endswith(".sd"):
            servDict[str(serv.name)[:-3]] = serv.id

    # Iterate through maps in project and, if a matching service definition is found,
    # overwrite that service definition with the data in the local map
    for sdName, sdID in servDict.items():
        if sdName == mapItem.name:
            updateItem = gis.content.get(sdID)
            arcpy.mp.CreateWebLayerSDDraft(mapItem, sddraft, sdName, 'MY_HOSTED_SERVICES', 'FEATURE_ACCESS', True, True)
            arcpy.StageService_server(sddraft, sd)
            updateItem.update(data=sd)
            print("Overwriting {}...".format(sdName))
            fs = updateItem.publish(overwrite=True)
            if shrOrg or shrEveryone or shrGroups:
                print("Setting sharing options...")
                fs.share(org=shrOrg, everyone=shrEveryone, groups=shrGroups)
            print("Successfully updated {}.\n".format(fs.title))


if __name__ == '__main__':
    projects_folder = "C:/Users/TechServPC/Documents/ArcGIS/Projects"
    project_folder = "JSA_TSG"
    project_name = "JSA_TSG"
    # p = Project(projects_folder=projects_folder,
    #             project_folder=project_folder,
    #             project_name=project_name)

    # d = p.projDict()
    # inputs = [x['data'] for x in d['maps'][0]['layers'] if '\\' in x['name']]
    # output_path = r'C:\Users\TechServPC\Documents\ArcGIS\Projects\JSA_TSG\JSA_TSG.gdb\JSA_Merge'
    # Merge(inputs, output_path)
    # print('merge complete')

    updateItem(proj_folder=f'{projects_folder}/{project_folder}', proj_name=project_name)
    print('Item updated')
    print()

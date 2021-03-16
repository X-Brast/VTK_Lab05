# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 13:41:42 2020

@author: alexandre marques

@remarque: J'ai décidé de travail dans les coordonnées RT90 2.5 gon V
"""

from pyproj import Transformer
from pyproj import CRS
import numpy as np
import os
import vtk

###
#
# fonction et class
#
###

# Interactor qui permet de réalise une coupe dans la carte à chaque mouvement 
# de la souris tant que le curseur pointe la carte
class PersoInteractor(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self,actCut, Map, text):
        self.AddObserver("MouseMoveEvent",self.mouseMoveEvent)

        # l'acteur dois déjà être ajouté au renderer
        self.PickedActorCutter = actCut
        self.Map = Map
        self.textActor = text
        
        self.plane = vtk.vtkPlane()
        self.plane.SetNormal(0,0,1)
        
        self.cutter = vtk.vtkCutter()
        self.cutter.SetCutFunction(self.plane)
        self.cutter.SetValue(0,10)
        self.cutter.SetInputData(self.Map)
        
        self.cutterMapper = vtk.vtkPolyDataMapper()
        
    def mouseMoveEvent(self,obj,event):
        # position du curseur sur la fenetre
        clickPos = self.GetInteractor().GetEventPosition()
        
        # permet de trouver l'intersection
        picker = vtk.vtkPropPicker()
        picker.Pick(clickPos[0], clickPos[1], 0, self.GetDefaultRenderer())
        
        if picker.GetActor():    
            # change l'hauteur de la coupe
            self.plane.SetOrigin(0,0,picker.GetPickPosition()[2])
            self.textActor.SetInput("Altitude: " + '{:.2f}'.format(picker.GetPickPosition()[2]) + " m")
            # mise à jour des informations
            self.cutterMapper.SetInputConnection(self.cutter.GetOutputPort())
            self.PickedActorCutter.SetMapper(self.cutterMapper)
        else:
            # enleve la coupe si hors de la carte
            self.PickedActorCutter.SetMapper(None)
            self.textActor.SetInput("")
        
        # rafraichit la fenetre
        self.GetInteractor().GetRenderWindow().Render()
        self.OnMouseMove()
        return
    
# Permet defenir la couleur du trajet du planneur 
# Si diff est inférieur, le planneur descends
# Si diff est supérieur, le planneur monte
def ChooseColor(diff):
    if(diff > 4):  
        scalarsPlaneur.InsertNextTuple1(0)
        return
    if(diff > 0):    
        scalarsPlaneur.InsertNextTuple1(1)
        return
    if(diff == 0):  
        scalarsPlaneur.InsertNextTuple1(2)
        return
    if(diff > -2):    
        scalarsPlaneur.InsertNextTuple1(3)
        return
    if(diff > -4):    
        scalarsPlaneur.InsertNextTuple1(4)
        return   
    scalarsPlaneur.InsertNextTuple1(5)

# permet de chercher la position de la texture
# code donnée par Cuisenaire 
def textureCoordinates ( gx, gy ):       
    y = ( gy - bottom ) / (top - bottom)
    x = ( gx - left ) / (right - left)
    return x,y

###
#
# première partie
#
###

# j'ai pris le RT90 2.5 gon V comme base
crs_RT90 = CRS.from_epsg(3021)
crs_GPS = CRS.from_epsg(4326)
transformer = Transformer.from_crs(crs_GPS, crs_RT90)

colonne = 6000
ligne = 6000
lat = 5
lon = 5
beginLat = 10
beginLon = 60
stepLat = lat / ligne
stepLon = lon / colonne

topleft = ( 1349340 , 7022573 ) 
topright = ( 1371573 , 7022967 )
bottomright = ( 1371835 , 7006362 )
bottomleft = ( 1349602 , 7005969 )

top = ( topleft[1] + topright[1] ) / 2.
left = ( topleft[0] + bottomleft[0] ) / 2.
right = ( bottomright[0] + topright[0] ) / 2.
bottom = ( bottomleft[1] + bottomright[1] ) / 2.

carte = vtk.vtkPolyData()
points = vtk.vtkPoints()
polys = vtk.vtkCellArray()
textureCoord = vtk.vtkFloatArray()
textureCoord.SetNumberOfComponents(2)

# lecture du fichier donnée de la carte
f = open("EarthEnv-DEM90_N60E010.bil", "rb")

data = np.fromfile(f, dtype=np.int16)

# contient les indices d'ordre d'ajout des points pour former des carrés
# c'est une matrice
tabPos = []
counter = 0

# j'ai laissé ces valeurs pour que la compilation se fasse plus vite
# for i in range(ligne)
for i in range(3700,4000):
    tabLinePos = []
    # for j in range(colonne)
    for j in range(3300,4000):
        # i et j commence en bas à droite tandis que les hauteurs commence en haut à droite
        pos = (colonne - i) * colonne + j
        zone = transformer.transform(beginLon + stepLon * i, beginLat + stepLat * j)
        indic = -1
        if(zone[1] >= left and zone[1] <= right and zone[0] <= top and zone[0] >= bottom):
            points.InsertNextPoint([zone[1], zone[0], data[pos]])
            u, v = textureCoordinates(zone[1], zone[0])
            textureCoord.InsertNextTuple2(u,v)
            indic = counter
            counter+=1
        tabLinePos.append(indic)
    tabPos.append(tabLinePos)      
    
# Création des formes géométriques
for l in range (len(tabPos)-1):
    for c in range (len(tabPos[l])-1):
        if(tabPos[l][c] >= 0 and tabPos[l][c+1] >= 0 and tabPos[l+1][c] >= 0 and tabPos[l+1][c+1] >= 0):
            polys.InsertNextCell(4, (tabPos[l][c], tabPos[l][c+1], tabPos[l+1][c+1], tabPos[l+1][c]))
                        
carte.SetPoints(points)
carte.SetPolys(polys)
carte.GetPointData().SetTCoords(textureCoord)

carteMapper = vtk.vtkPolyDataMapper()
carteMapper.SetInputData(carte)
carteMapper.Update()

# lecture du fichier image pour la texture
image = vtk.vtkJPEGReader()
image.SetFileName("glider_map.jpg")
image.Update()

texture = vtk.vtkTexture()
texture.SetInputConnection(image.GetOutputPort())
texture.InterpolateOff()
texture.RepeatOff()

carteActor = vtk.vtkActor()
carteActor.SetMapper(carteMapper)
carteActor.SetTexture(texture)

###
#
# deuxième partie
#
###

pointPlaneur = vtk.vtkPoints()
cellPlaneur = vtk.vtkCellArray()
actorPlaneur = vtk.vtkActor()
scalarsPlaneur = vtk.vtkFloatArray()

# lecture du fichier voyage planeur
file = open("vtkgps.txt", "r")
# nombre d'entrée
nbLine = int(file.readline())
cellPlaneur.InsertNextCell(nbLine)
counter = 0
lastAlt = 0
for line in file:
    info = line.split()
    pointPlaneur.InsertNextPoint([int(info[1]), int(info[2]), int(float(info[3]))])
    cellPlaneur.InsertCellPoint(counter)
    ChooseColor(int(float(info[3])) - lastAlt)
    lastAlt = int(float(info[3]))
    counter+=1
file.close()

polyPlaneur = vtk.vtkPolyData()
polyPlaneur.SetPoints(pointPlaneur)
polyPlaneur.SetLines(cellPlaneur)
polyPlaneur.GetPointData().SetScalars(scalarsPlaneur)

lookupTable = vtk.vtkLookupTable()
lookupTable.SetNumberOfColors(6)
lookupTable.Build()
lookupTable.SetTableValue(0, 1, 0, 0) # red
lookupTable.SetTableValue(1, 1, 1, 0) # yellow
lookupTable.SetTableValue(2, 0.4, 1, 0.4) # green
lookupTable.SetTableValue(3, 0.4, 1, 1) # ligth blue
lookupTable.SetTableValue(4, 0, 0.5, 1) # blue 
lookupTable.SetTableValue(5, 0, 0, 1) # dark blue

mapperPlaneur = vtk.vtkPolyDataMapper()
mapperPlaneur.SetInputData(polyPlaneur)
mapperPlaneur.SetScalarRange(0,6)
mapperPlaneur.SetLookupTable(lookupTable)
mapperPlaneur.Update()

actorPlaneur = vtk.vtkActor()
actorPlaneur.SetMapper(mapperPlaneur)

###
#
# troisième partie
#
###

# l'acteur sera toujours present avec pas forcement des données
cutterActor = vtk.vtkActor()
cutterActor.GetProperty().SetColor(1.0,0,0)
cutterActor.GetProperty().SetLineWidth(2)

textActor = vtk.vtkTextActor()
textActor.SetPosition2(50,50)
textActor.GetTextProperty().SetFontSize(24)

ren = vtk.vtkRenderer()
ren.AddActor(carteActor)
ren.AddActor(cutterActor)
ren.AddActor(actorPlaneur)
ren.AddActor(textActor)
ren.SetBackground(0.1,0.2,0.4)
ren.ResetCamera()

renWin = vtk.vtkRenderWindow()
renWin.AddRenderer(ren)
renWin.SetSize(800, 800)
renWin.Render()

iren = vtk.vtkRenderWindowInteractor()
iren.SetRenderWindow(renWin)
style = PersoInteractor(cutterActor, carte, textActor)
style.SetDefaultRenderer(ren)
iren.SetInteractorStyle(style)
iren.Initialize()
iren.Start()
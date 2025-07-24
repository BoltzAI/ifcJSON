# IFCJSON_python - ifc2json4.py
# Convert IFC SPF file to ifcJSON-4
# https://github.com/IFCJSON-Team

# MIT License

# Copyright (c) 2020 Jan Brouwer <jan@brewsky.nl>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import uuid
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.guid as guid
import ifcjson.common as common
from datetime import datetime
from ifcopenshell.entity_instance import entity_instance


class IFC2JSON4(common.IFC2JSON):
    SCHEMA_VERSION = '0.0.1'

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, False)

    def __init__(self,
                 ifcModel,
                 COMPACT=False,
                 NO_INVERSE=False,
                 EMPTY_PROPERTIES=False,
                 NO_OWNERHISTORY=False,
                 GEOMETRY=True):
        """IFC SPF to ifcJSON-4 writer

        parameters:
        ifcModel: IFC filePath or ifcopenshell model instance
        COMPACT (boolean): if True then pretty print is turned off and references are created without informative "type" property
        NO_INVERSE (boolean): if True then inverse relationships will be explicitly added to entities

        """

        self.COMPACT = COMPACT
        self.NO_INVERSE = NO_INVERSE
        self.EMPTY_PROPERTIES = EMPTY_PROPERTIES

        if isinstance(ifcModel, ifcopenshell.file):
            self.ifcModel = ifcModel
        else:
            self.ifcModel = ifcopenshell.open(ifcModel)

        # Dictionary referencing all objects with a GlobalId that are already created
        self.rootObjects = {}
        
        # Track all used GUIDs to ensure uniqueness
        self.usedGuids = set()

        # input(dir(self.ifcModel.wrapped_data.header))
        # input(self.ifcModel.wrapped_data.header)
        # print(dir(self.ifcModel.wrapped_data.header.file_description))
        # if self.ifcModel.wrapped_data.header.file_description.this:
        #     print(self.ifcModel.wrapped_data.header.file_description[0])
        # input()
        
        if NO_OWNERHISTORY:
            self.remove_ownerhistory()

        # adjust GEOMETRY type
        if GEOMETRY == 'tessellate':
            self.tessellate()
        elif GEOMETRY == False:
            self.remove_geometry()

    def generateUniqueGuid(self):
        """Generate a truly unique GUID that hasn't been used before"""
        while True:
            new_guid = str(uuid.uuid4())
            if new_guid not in self.usedGuids:
                self.usedGuids.add(new_guid)
                return new_guid

    def extractAndPreserveGuid(self, entity):
        """Extract GUID from IFC entity and ensure it's unique"""
        if hasattr(entity, 'GlobalId') and entity.GlobalId:
            # Extract the original GUID from IFC format
            try:
                # Convert IFC GUID to full UUID format
                expanded_guid = guid.expand(entity.GlobalId)
                # Extract the middle part (removing curly braces)
                original_guid = guid.split(expanded_guid)[1:-1]
                
                # Check if this GUID is already used
                if original_guid in self.usedGuids:
                    print(f"WARNING: Duplicate GUID found for entity {entity.id()}: {original_guid}")
                    print(f"Entity type: {entity.is_a()}")
                    if hasattr(entity, 'Name'):
                        print(f"Entity name: {entity.Name}")
                    # Generate a new unique GUID
                    new_guid = self.generateUniqueGuid()
                    print(f"Generated new unique GUID: {new_guid}")
                    return new_guid
                else:
                    # GUID is unique, use it
                    self.usedGuids.add(original_guid)
                    return original_guid
                    
            except Exception as e:
                print(f"ERROR: Could not extract GUID from entity {entity.id()}: {e}")
                # Generate a new unique GUID as fallback
                return self.generateUniqueGuid()
        else:
            # Entity doesn't have a GUID, generate one
            return self.generateUniqueGuid()

    def spf2Json(self):
        """
        Create json dictionary structure for all attributes of the objects in the root list
        also including inverse attributes (except for IfcGeometricRepresentationContext and IfcOwnerHistory types)
        # (?) Check every IFC object to see if it is used multiple times

        Returns:
        dict: ifcJSON-4 model structure

        """

        jsonObjects = []
        relationships = []

        print("Starting GUID extraction and preservation...")
        print(f"Processing {len(list(self.ifcModel.by_type('IfcRoot')))} IfcRoot entities...")

        # Collect all entity types that already have a GlobalId (IfcRoot descendants)
        for entity in self.ifcModel.by_type('IfcRoot'):
            preserved_guid = self.extractAndPreserveGuid(entity)
            self.rootObjects[entity.id()] = preserved_guid
            
            if entity.is_a('IfcRelationship'):
                relationships.append(entity)

        print(f"Processed IfcRoot entities. Total unique GUIDs: {len(self.usedGuids)}")

        # Generate GUIDs for entity types that need them but don't inherit from IfcRoot
        entity_types_needing_guids = [
            'IfcShapeRepresentation',
            'IfcOwnerHistory', 
            'IfcGeometricRepresentationContext'
        ]
        
        for entity_type in entity_types_needing_guids:
            entities = self.ifcModel.by_type(entity_type)
            print(f"Processing {len(entities)} {entity_type} entities...")
            
            for entity in entities:
                # Only add GUID if not already processed (some might inherit from IfcRoot)
                if entity.id() not in self.rootObjects:
                    new_guid = self.generateUniqueGuid()
                    self.rootObjects[entity.id()] = new_guid

        print(f"Final total entities with GUIDs: {len(self.rootObjects)}")
        print(f"Final total unique GUIDs: {len(self.usedGuids)}")

        # Verify no duplicate GUIDs exist
        guid_values = list(self.rootObjects.values())
        if len(guid_values) != len(set(guid_values)):
            print("ERROR: Duplicate GUIDs detected in rootObjects!")
            duplicates = []
            seen = set()
            for guid_val in guid_values:
                if guid_val in seen:
                    duplicates.append(guid_val)
                seen.add(guid_val)
            print(f"Duplicate GUIDs: {duplicates}")
        else:
            print("✅ GUID uniqueness verified - no duplicates found")

        for key in self.rootObjects:
            entity = self.ifcModel.by_id(key)
            entityAttributes = entity.__dict__
            entityType = entityAttributes['type']
            if not entityType == 'IfcOwnerHistory':
                if not self.NO_INVERSE:
                    for attr in entity.wrapped_data.get_inverse_attribute_names():
                        inverseAttribute = getattr(entity, attr)
                        attrValue = self.getAttributeValue(inverseAttribute)
                        if not attrValue and attrValue is not False:
                            continue
                        else:
                            entityAttributes[attr] = attrValue

            entityAttributes["GlobalId"] = self.rootObjects[entity.id()]
            jsonObjects.append(self.createFullObject(entityAttributes))

        return {
            'type': 'ifcJSON',
            'version': self.SCHEMA_VERSION,
            # 'schemaIdentifiers': self.ifcModel.wrapped_data.header.file_schema.schema_identifiers,
            'schemaIdentifier': self.ifcModel.wrapped_data.schema,
            'originatingSystem': 'IFC2JSON_python_fixed Version ' + self.VERSION,
            'preprocessorVersion': 'IfcOpenShell ' + ifcopenshell.version,
            'timeStamp': datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            'data': jsonObjects
        }

    def createFullObject(self, entityAttributes):
        """Returns complete ifcJSON-4 object

        Parameters:
        entityAttributes (dict): Dictionary of IFC object data

        Returns:
        dict: containing complete ifcJSON-4 object

        """
        fullObject = {}

        for attr in entityAttributes:

            # Line numbers are not part of IFC JSON
            if attr == 'id':
                continue

            attrKey = self.toLowerCamelcase(attr)

            # Replace wrappedvalue key names to value
            if attrKey == 'wrappedValue':
                attrKey = 'value'

            jsonValue = self.getAttributeValue(entityAttributes[attr])
            if jsonValue is not None:
                fullObject[attrKey] = jsonValue
        return fullObject

    def createReferenceObject(self, entityAttributes, COMPACT=False):
        """Returns object reference

        Parameters:
        entityAttributes (dict): Dictionary of IFC object data
        COMPACT (boolean): verbose or non verbose ifcJSON-4 output

        Returns:
        dict: object containing reference to another object

        """
        ref = {}
        if not COMPACT:
            ref['type'] = entityAttributes['type']
        ref['ref'] = entityAttributes['GlobalId']
        return ref

    def tessellate(self):
        """Converts all IfcProduct representations to IfcTriangulatedFaceSet
        """
        for product in self.ifcModel.by_type('IfcProduct'):
            if product.Representation:
                try:
                    representation = product.Representation
                    old_shapes = representation.Representations
                    context = old_shapes[0].ContextOfItems

                    tessellated_shape = ifcopenshell.geom.create_shape(
                        self.settings, product)

                    verts = tessellated_shape.geometry.verts
                    vertsList = [verts[i:i+3] for i in range(0, len(verts), 3)]

                    faces = tessellated_shape.geometry.faces
                    facesList = [faces[i:i+3] for i in range(0, len(faces), 3)]

                    pointlist = self.ifcModel.createIfcCartesianPointList3D(
                        vertsList)
                    shape = self.ifcModel.createIfcTriangulatedFaceSet(pointlist,
                        None, None, facesList, None)

                    body_representation = self.ifcModel.createIfcShapeRepresentation(
                        context, "Body", "Tessellation", [shape])
                    new_representation = self.ifcModel.createIfcProductDefinitionShape(
                        None, None, [body_representation])

                    representation = tuple(new_representation)

                except Exception as e:
                    print(str(e) + ': Unable to generate OBJ data for ' +
                          str(product))

    def remove_ownerhistory(self):
        for entity in self.ifcModel.by_type('IfcOwnerHistory'):
            self.ifcModel.remove(entity)

    def remove_geometry(self):
        removeTypes = ['IfcLocalPlacement', 'IfcRepresentationMap', 'IfcGeometricRepresentationContext', 'IfcGeometricRepresentationSubContext', 'IfcProductDefinitionShape',
                       'IfcMaterialDefinitionRepresentation', 'IfcShapeRepresentation', 'IfcRepresentationItem', 'IfcStyledRepresentation', 'IfcPresentationLayerAssignment', 'IfcTopologyRepresentation']
        for ifcType in removeTypes:
            # print(ifcType)
            # (lambda x: self.ifcModel.remove(x), self.ifcModel.by_type(ifcType))
            for entity in self.ifcModel.by_type(ifcType):
                self.ifcModel.remove(entity)
